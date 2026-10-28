"""Durable, local project and render-job coordination.

SQLite owns project revisions and job state. A submission durably copies its
inputs before committing a queued job. Renderers are trusted Python callables;
this module is not an OS sandbox or a live-provider billing system.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import stat
import uuid
import wave
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from .models import (
    MAX_AUDIO_BYTES, MAX_AUDIO_SECONDS, MAX_JSON_BYTES, SNAPSHOT_VERSION,
    CohortFrameError, ConflictError, IdempotencyConflictError, JobCancelled,
    NotFoundError, RevisionConflictError, StateError, ValidationError,
    canonical_json, parse_json, validate_id, validate_manifest, validate_revision,
)

Renderer = Callable[[dict[str, Any], Path, Callable[[], bool]], dict[str, Any]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _file_digest(path: Path, *, maximum: int | None = None) -> tuple[str, int]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            size += len(chunk)
            if maximum is not None and size > maximum:
                raise ValidationError("File exceeds the supported byte limit.")
            digest.update(chunk)
    return digest.hexdigest(), size


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, value: Any) -> bytes:
    raw = (canonical_json(value) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            os.chmod(temporary, 0o600)
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return raw


def _process_identity(pid: int) -> str | None:
    """Linux start ticks distinguish a reused PID; other platforms use PID liveness."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] == "Z":
            return "zombie"
        return fields[19]
    except (OSError, IndexError):
        return None


def _alive(pid: int | None, identity: str | None) -> bool:
    if not pid or pid < 1:
        return False
    # os.kill(pid, 0) is not a safe Windows probe. Until a native liveness
    # implementation is verified there, never reclaim a recorded worker.
    if os.name != "posix":
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    current = _process_identity(pid)
    if current == "zombie":
        return False
    return not (identity is not None and current is not None and identity != current)


def _validate_wave(path: Path) -> None:
    try:
        if path.stat().st_size > MAX_AUDIO_BYTES:
            raise ValidationError("Audio exceeds the 32 MiB v0.1 limit.")
        with wave.open(str(path), "rb") as audio:
            if audio.getcomptype() != "NONE" or audio.getnchannels() not in (1, 2):
                raise ValidationError("Audio must be uncompressed mono or stereo PCM WAV.")
            if audio.getsampwidth() not in (1, 2, 3, 4) or not 8000 <= audio.getframerate() <= 96000:
                raise ValidationError("PCM WAV requires 1..4-byte samples at 8..96 kHz.")
            if not 0 < audio.getnframes() / audio.getframerate() <= MAX_AUDIO_SECONDS:
                raise ValidationError("Source WAV must contain more than zero and at most 120 seconds.")
            expected = audio.getnframes() * audio.getnchannels() * audio.getsampwidth()
            consumed = 0
            while True:
                chunk = audio.readframes(65536)
                if not chunk:
                    break
                consumed += len(chunk)
            if consumed != expected:
                raise ValidationError("WAV sample data is truncated.")
    except (wave.Error, EOFError, OSError) as exc:
        raise ValidationError(f"Cannot read a supported PCM WAV: {exc}") from exc


class Store:
    """A private local workspace. Each operation uses its own SQLite connection."""

    def __init__(self, home: str | Path):
        self.home = Path(home).expanduser().resolve()
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.jobs_dir = self.home / "jobs"
        if self.jobs_dir.is_symlink():
            raise ValidationError("The jobs directory must not be a symbolic link.")
        self.jobs_dir.mkdir(exist_ok=True, mode=0o700)
        self.db_path = self.home / "cohortframe.sqlite3"
        if self.db_path.is_symlink():
            raise ValidationError("The state database must not be a symbolic link.")
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    @contextmanager
    def _read(self) -> Iterator[sqlite3.Connection]:
        connection = None
        try:
            connection = self._connect()
            yield connection
        except sqlite3.Error as exc:
            raise StateError("The local state database could not complete this operation.") from exc
        finally:
            if connection is not None:
                connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._read() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def _initialise(self) -> None:
        with self._read() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise StateError(f"Unsupported local database version: {version}.")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, revision INTEGER NOT NULL CHECK(revision>0),
                    manifest_json TEXT NOT NULL, base_dir TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    project_revision INTEGER NOT NULL, idempotency_key TEXT NOT NULL,
                    request_digest TEXT NOT NULL, snapshot_digest TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('queued','running','succeeded','failed','cancel_requested','cancelled','interrupted')),
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    started_at TEXT, finished_at TEXT, attempts INTEGER NOT NULL DEFAULT 0,
                    worker_pid INTEGER, worker_identity TEXT, worker_token TEXT,
                    result_json TEXT, error_json TEXT,
                    UNIQUE(project_id,idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS jobs_state ON jobs(state);
                PRAGMA user_version=1;
            """)
        os.chmod(self.db_path, 0o600)

    @staticmethod
    def _project(row: sqlite3.Row) -> dict[str, Any]:
        return {key: row[key] for key in ("id", "revision", "created_at", "updated_at", "base_dir")} | {"manifest": json.loads(row["manifest_json"])}

    def _project_row(self, connection: sqlite3.Connection, identifier: str) -> sqlite3.Row:
        validate_id(identifier, "Project identifier")
        row = connection.execute("SELECT * FROM projects WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise NotFoundError("Project does not exist.")
        return row

    def _job_row(self, connection: sqlite3.Connection, identifier: str) -> sqlite3.Row:
        validate_id(identifier, "Job identifier")
        row = connection.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise NotFoundError("Job does not exist.")
        return row

    def _prepare_manifest(self, manifest: dict[str, Any], base_dir: str | Path | None) -> tuple[dict[str, Any], Path]:
        validated = validate_manifest(manifest)
        try:
            base = Path(base_dir or Path.cwd()).expanduser().resolve(strict=True)
        except OSError as exc:
            raise ValidationError("base_dir must be an existing local directory.") from exc
        if not base.is_dir():
            raise ValidationError("base_dir must be an existing local directory.")
        if "audio" in validated:
            supplied = Path(validated["audio"]).expanduser()
            if ".." in supplied.parts:
                raise ValidationError("Audio paths must not contain parent traversal (..).")
            relative = not supplied.is_absolute()
            chosen = base / supplied if relative else supplied
            if chosen.is_symlink():
                raise ValidationError("The selected audio file must not be a symbolic link.")
            try:
                actual = chosen.resolve(strict=True)
            except OSError as exc:
                raise ValidationError("The selected audio file does not exist.") from exc
            if relative and not actual.is_relative_to(base):
                raise ValidationError("A relative audio path must remain inside base_dir after resolving links.")
            if not actual.is_file():
                raise ValidationError("The selected audio must be a regular local file.")
            _validate_wave(actual)
            validated["audio"] = str(actual)
        return validated, base

    def create_project(self, manifest: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
        validated, base = self._prepare_manifest(manifest, base_dir)
        identifier, now = uuid.uuid4().hex, _now()
        with self._transaction() as connection:
            connection.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)", (identifier, 1, canonical_json(validated), str(base), now, now))
            return self._project(self._project_row(connection, identifier))

    def get_project(self, identifier: str) -> dict[str, Any]:
        with self._read() as connection:
            return self._project(self._project_row(connection, identifier))

    def update_project(self, identifier: str, manifest: dict[str, Any], expected_revision: int, *, base_dir: str | Path | None = None) -> dict[str, Any]:
        validate_revision(expected_revision)
        with self._transaction() as connection:
            current = self._project_row(connection, identifier)
            if current["revision"] != expected_revision:
                raise RevisionConflictError("Project changed; inspect it and submit a new expected_revision.", details={"expected_revision": expected_revision, "current_revision": current["revision"]})
            validated, base = self._prepare_manifest(manifest, base_dir or current["base_dir"])
            connection.execute("UPDATE projects SET revision=revision+1,manifest_json=?,base_dir=?,updated_at=? WHERE id=?", (canonical_json(validated), str(base), _now(), identifier))
            return self._project(self._project_row(connection, identifier))

    def _copy_audio(self, source: Path, destination: Path) -> dict[str, Any]:
        if source.resolve(strict=True) != source:
            raise ValidationError("Audio path changed through a symbolic link before snapshotting.")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(source, flags)
        digest, size = hashlib.sha256(), 0
        try:
            with os.fdopen(descriptor, "rb", closefd=False) as incoming, destination.open("xb") as outgoing:
                before = os.fstat(descriptor)
                if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_AUDIO_BYTES:
                    raise ValidationError("Audio must be a regular file no larger than 32 MiB.")
                for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                    size += len(chunk)
                    if size > MAX_AUDIO_BYTES:
                        raise ValidationError("Audio grew beyond the 32 MiB limit while snapshotting.")
                    digest.update(chunk)
                    outgoing.write(chunk)
                outgoing.flush()
                os.fsync(outgoing.fileno())
                after = os.fstat(descriptor)
                if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                    raise ConflictError("Audio changed while snapshotting; submit again with stable input.")
        finally:
            os.close(descriptor)
        _validate_wave(destination)
        os.chmod(destination, 0o400)
        return {"path": "audio.wav", "sha256": digest.hexdigest(), "bytes": size}

    def submit_job(self, identifier: str, expected_revision: int, idempotency_key: str) -> dict[str, Any]:
        validate_id(identifier, "Project identifier")
        validate_revision(expected_revision)
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128 or any(not 33 <= ord(char) <= 126 for char in idempotency_key):
            raise ValidationError("idempotency_key must contain 1..128 non-space printable ASCII characters.")
        request_digest = _digest({"operation": "render", "version": 1, "project_id": identifier, "expected_revision": expected_revision})
        staging = final = None
        committed = False
        try:
            with self._transaction() as connection:
                existing = connection.execute("SELECT * FROM jobs WHERE project_id=? AND idempotency_key=?", (identifier, idempotency_key)).fetchone()
                if existing is not None:
                    if not hmac.compare_digest(existing["request_digest"], request_digest):
                        raise IdempotencyConflictError("This project already used that idempotency key for a different request.")
                    return self._job(existing)
                project = self._project_row(connection, identifier)
                if project["revision"] != expected_revision:
                    raise RevisionConflictError("Project changed before submission.", details={"expected_revision": expected_revision, "current_revision": project["revision"]})
                manifest = json.loads(project["manifest_json"])
                job_id, now = uuid.uuid4().hex, _now()
                staging = self.jobs_dir / f".{job_id}.staging"
                final = self.jobs_dir / job_id
                staging.mkdir(mode=0o700)
                audio = None
                if "audio" in manifest:
                    audio = self._copy_audio(Path(manifest["audio"]), staging / "audio.wav")
                    manifest["audio"] = "audio.wav"
                snapshot = {"snapshot_version": SNAPSHOT_VERSION, "project_id": identifier, "project_revision": expected_revision, "manifest": manifest, "audio": audio, "manifest_sha256": _digest(manifest)}
                raw = _atomic_json(staging / "snapshot.json", snapshot)
                os.chmod(staging / "snapshot.json", 0o400)
                os.replace(staging, final)
                _sync_directory(self.jobs_dir)
                connection.execute("""INSERT INTO jobs
                    (id,project_id,project_revision,idempotency_key,request_digest,snapshot_digest,state,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,'queued',?,?)""", (job_id, identifier, expected_revision, idempotency_key, request_digest, hashlib.sha256(raw).hexdigest(), now, now))
                result = self._job(self._job_row(connection, job_id))
            committed = True
            return result
        except (OSError, wave.Error) as exc:
            raise ValidationError(f"Could not snapshot local inputs: {exc}") from exc
        finally:
            if not committed:
                for folder in (staging, final):
                    if folder is not None and folder.exists():
                        shutil.rmtree(folder)

    def _job(self, row: sqlite3.Row) -> dict[str, Any]:
        folder = self.jobs_dir / validate_id(row["id"])
        fields = ("id", "project_id", "project_revision", "state", "created_at", "updated_at", "started_at", "finished_at", "attempts", "worker_pid", "idempotency_key", "request_digest", "snapshot_digest")
        result = {key: row[key] for key in fields}
        result.update({"snapshot_dir": str(folder), "snapshot_path": str(folder / "snapshot.json"), "result": json.loads(row["result_json"]) if row["result_json"] else None, "error": json.loads(row["error_json"]) if row["error_json"] else None})
        try:
            with (folder / "snapshot.json").open("rb") as incoming:
                result["snapshot"] = parse_json(incoming.read(MAX_JSON_BYTES + 1))
        except (OSError, ValidationError):
            result["snapshot"] = None
        return result

    def get_job(self, identifier: str) -> dict[str, Any]:
        with self._read() as connection:
            return self._job(self._job_row(connection, identifier))

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._read() as connection:
            return [self._job(row) for row in connection.execute("SELECT * FROM jobs ORDER BY created_at,id").fetchall()]

    def cancel_job(self, identifier: str) -> dict[str, Any]:
        with self._transaction() as connection:
            row = self._job_row(connection, identifier)
            now = _now()
            if row["state"] in ("queued", "interrupted"):
                connection.execute("UPDATE jobs SET state='cancelled',updated_at=?,finished_at=?,worker_pid=NULL,worker_identity=NULL,worker_token=NULL WHERE id=?", (now, now, identifier))
            elif row["state"] == "running":
                connection.execute("UPDATE jobs SET state='cancel_requested',updated_at=? WHERE id=?", (now, identifier))
            return self._job(self._job_row(connection, identifier))

    def recover_jobs(self) -> list[dict[str, Any]]:
        recovered = []
        with self._transaction() as connection:
            for row in connection.execute("SELECT * FROM jobs WHERE state IN ('running','cancel_requested')").fetchall():
                if _alive(row["worker_pid"], row["worker_identity"]):
                    continue
                now = _now()
                state = "cancelled" if row["state"] == "cancel_requested" else "interrupted"
                error = {"code": "worker_interrupted", "message": "The recorded worker is no longer alive. The immutable inputs remain available."}
                connection.execute("UPDATE jobs SET state=?,updated_at=?,finished_at=?,worker_pid=NULL,worker_identity=NULL,worker_token=NULL,error_json=? WHERE id=?", (state, now, now, canonical_json(error), row["id"]))
                recovered.append(self._job(self._job_row(connection, row["id"])))
        return recovered

    def retry_job(self, identifier: str) -> dict[str, Any]:
        with self._transaction() as connection:
            row = self._job_row(connection, identifier)
            if row["state"] not in ("failed", "interrupted"):
                raise StateError("Only failed or interrupted jobs can be queued for retry.")
            connection.execute("UPDATE jobs SET state='queued',updated_at=?,started_at=NULL,finished_at=NULL,result_json=NULL,error_json=NULL,worker_pid=NULL,worker_identity=NULL,worker_token=NULL WHERE id=?", (_now(), identifier))
            return self._job(self._job_row(connection, identifier))

    def _verified_snapshot(self, row: sqlite3.Row) -> tuple[dict[str, Any], Path]:
        folder = self.jobs_dir / validate_id(row["id"])
        if folder.is_symlink() or not folder.resolve().is_relative_to(self.jobs_dir.resolve()):
            raise ValidationError("Job input directory is outside the workspace.")
        file = folder / "snapshot.json"
        if file.is_symlink():
            raise ValidationError("Snapshot must not be a symbolic link.")
        with file.open("rb") as incoming:
            raw = incoming.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            raise ValidationError("Snapshot exceeds the JSON size limit.")
        if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), row["snapshot_digest"]):
            raise ValidationError("Immutable snapshot was modified; refusing to render it.")
        snapshot = parse_json(raw)
        manifest = validate_manifest(snapshot["manifest"])
        if snapshot.get("snapshot_version") != SNAPSHOT_VERSION or snapshot.get("project_id") != row["project_id"] or snapshot.get("project_revision") != row["project_revision"] or _digest(manifest) != snapshot.get("manifest_sha256"):
            raise ValidationError("Snapshot identity or manifest integrity does not match its job.")
        audio = snapshot.get("audio")
        if audio is not None:
            path = folder / "audio.wav"
            if audio.get("path") != "audio.wav" or manifest.get("audio") != "audio.wav" or path.is_symlink():
                raise ValidationError("Snapshot audio must be its own audio.wav.")
            digest, size = _file_digest(path, maximum=MAX_AUDIO_BYTES)
            if digest != audio.get("sha256") or size != audio.get("bytes"):
                raise ValidationError("Immutable audio snapshot was modified.")
        elif "audio" in manifest:
            raise ValidationError("Snapshot audio is missing.")
        return snapshot, folder

    @staticmethod
    def _verified_result(result: Any, folder: Path) -> dict[str, Any]:
        if not isinstance(result, dict) or not isinstance(result.get("path"), str):
            raise ValidationError("Renderer must return an artifact with a relative path.")
        relative = Path(result["path"])
        if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".mp4" or "\\" in str(relative) or ":" in str(relative):
            raise ValidationError("Rendered artifact must be a relative MP4 inside its job directory.")
        path = folder / relative
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(folder.resolve()):
            raise ValidationError("Rendered artifact escapes its job directory.")
        digest, size = _file_digest(path, maximum=256 * 1024 * 1024)
        if size == 0 or result.get("sha256") != digest or result.get("bytes") != size:
            raise ValidationError("Renderer artifact hash or byte count is inconsistent.")
        canonical_json(result)
        return result

    def run_job(self, identifier: str, runner: Renderer) -> dict[str, Any]:
        validate_id(identifier, "Job identifier")
        if not callable(runner):
            raise ValidationError("runner must be a trusted renderer callable.")
        self.recover_jobs()
        token, pid, now = uuid.uuid4().hex, os.getpid(), _now()
        with self._transaction() as connection:
            row = self._job_row(connection, identifier)
            if row["state"] != "queued":
                raise StateError(f"Cannot run a job in state {row['state']}.")
            connection.execute("UPDATE jobs SET state='running',updated_at=?,started_at=?,finished_at=NULL,attempts=attempts+1,worker_pid=?,worker_identity=?,worker_token=?,result_json=NULL,error_json=NULL WHERE id=?", (now, now, pid, _process_identity(pid), token, identifier))
            claimed = self._job_row(connection, identifier)

        def cancelled() -> bool:
            with self._read() as connection:
                current = self._job_row(connection, identifier)
                return current["worker_token"] != token or current["state"] != "running"

        state, result, error = "failed", None, None
        pending_interrupt: BaseException | None = None
        try:
            snapshot, folder = self._verified_snapshot(claimed)
            if cancelled():
                raise JobCancelled("Cancellation requested before rendering.")
            result = self._verified_result(runner(snapshot, folder, cancelled), folder)
            state = "succeeded"
        except JobCancelled as exc:
            state, error = "cancelled", {"code": exc.code, "message": str(exc)}
        except (KeyboardInterrupt, SystemExit) as exc:
            state, error, pending_interrupt = "interrupted", {"code": "worker_interrupted", "message": "Worker was interrupted."}, exc
        except Exception as exc:
            error = ({"code": exc.code, "message": str(exc)[:1000]} if isinstance(exc, CohortFrameError)
                     else {"code": "render_failed", "message": "A local render operation failed; no successful artifact was published.", "exception_type": type(exc).__name__})
        with self._transaction() as connection:
            current = self._job_row(connection, identifier)
            if current["worker_token"] != token:
                raise StateError("Worker ownership changed before completion.")
            if current["state"] == "cancel_requested":
                state, result, error = "cancelled", None, {"code": "cancelled", "message": "Cancellation requested; no completed artifact is published by this job."}
            if state != "succeeded":
                result = None
            now = _now()
            connection.execute("UPDATE jobs SET state=?,updated_at=?,finished_at=?,worker_pid=NULL,worker_identity=NULL,worker_token=NULL,result_json=?,error_json=? WHERE id=?", (state, now, now, canonical_json(result) if result is not None else None, canonical_json(error) if error is not None else None, identifier))
            finished = self._job(self._job_row(connection, identifier))
        if pending_interrupt is not None:
            raise pending_interrupt
        return finished
