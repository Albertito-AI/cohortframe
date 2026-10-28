"""Behavioural core tests. Stub artifacts exercise coordination, not media validity."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from cohortframe.core import Store, _alive
from cohortframe.models import (
    IdempotencyConflictError, JobCancelled, NotFoundError, RevisionConflictError,
    StateError, ValidationError, parse_json, scene_frames, validate_manifest,
)


def manifest() -> dict:
    return {"version": 1, "name": "Core fixture", "width": 640, "height": 360, "fps": 10,
            "scenes": [{"id": "intro", "title": "HELLO", "subtitle": "A LOCAL TEST", "duration": 1, "color": "#183153"}]}


def write_wave(path: Path, value: int = 0) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(22050)
        output.writeframes(value.to_bytes(2, "little", signed=True) * 2205)


def stub_artifact(snapshot: dict, folder: Path, cancelled) -> dict:
    if cancelled():
        raise JobCancelled("Stopped by the test caller.")
    # This intentionally is not a video: actual media verification belongs to
    # render.py and its FFmpeg integration tests.
    content = ("CORE STUB:" + snapshot["manifest"]["scenes"][0]["title"]).encode()
    (folder / "stub.mp4").write_bytes(content)
    return {"path": "stub.mp4", "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


class SchemaTests(unittest.TestCase):
    def test_json_rejects_duplicate_keys_nonfinite_numbers_and_nonobjects(self):
        for source in ('{"name":"first","name":"second"}', '{"x":NaN}', '{"x":Infinity}', '[]', 'null'):
            with self.subTest(source=source), self.assertRaises(ValidationError):
                parse_json(source)

    def test_json_rejects_oversize_and_invalid_utf8(self):
        for source in (b'\xff', '{"x":"' + 'x' * (128 * 1024) + '"}'):
            with self.assertRaises(ValidationError):
                parse_json(source)

    def test_bounds_and_unsupported_features_rejected(self):
        changes = [
            {"version": 2}, {"version": True}, {"width": 641}, {"height": 1922},
            {"fps": True}, {"fps": 31}, {"filter": "arbitrary ffmpeg text"},
            {"audio": "https://example.test/a.wav"}, {"audio": "//server/share/a.wav"},
            {"audio": "local.mp3"}, {"scenes": []},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                validate_manifest(manifest() | change)

    def test_duration_handles_huge_integer_without_overflow(self):
        for duration in (10 ** 500, float("nan"), float("inf"), 0, -1, True, 0.01):
            data = manifest()
            data["scenes"][0]["duration"] = duration
            with self.subTest(kind=type(duration).__name__), self.assertRaises(ValidationError):
                validate_manifest(data)

    def test_frame_rounding_is_half_up_and_cannot_push_total_over_limit(self):
        self.assertEqual(scene_frames(.25, 10), 3)
        data = manifest()
        data["scenes"] = [{"id": "one", "title": "ONE", "duration": 59.75},
                          {"id": "two", "title": "TWO", "duration": .25}]
        with self.assertRaises(ValidationError):
            validate_manifest(data)

    def test_scene_identifiers_and_visible_text_are_supported(self):
        data = manifest()
        data["scenes"].append(copy.deepcopy(data["scenes"][0]))
        with self.assertRaises(ValidationError):
            validate_manifest(data)
        for title in ("Héllo", "bad\x00text", "bad\ttext"):
            data = manifest()
            data["scenes"][0]["title"] = title
            with self.assertRaises(ValidationError):
                validate_manifest(data)
        data["scenes"][0]["title"] = "TWO\nLINES"
        self.assertEqual(validate_manifest(data)["scenes"][0]["title"], "TWO\nLINES")

    def test_nonposix_liveness_never_calls_os_kill(self):
        with patch("cohortframe.core.os.name", "nt"), patch("cohortframe.core.os.kill") as kill:
            self.assertTrue(_alive(12345, None))
            kill.assert_not_called()


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cohortframe-core-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / "assets"
        self.assets.mkdir()
        self.store = Store(self.root / "state")
        self.project = self.store.create_project(manifest(), base_dir=self.assets)

    def submit(self, key="first"):
        return self.store.submit_job(self.project["id"], self.project["revision"], key)

    def test_stale_edit_cannot_overwrite_a_newer_change(self):
        first, second = manifest(), manifest()
        first["scenes"][0]["title"] = "FIRST ACTOR"
        second["scenes"][0]["title"] = "SECOND ACTOR"
        updated = self.store.update_project(self.project["id"], first, 1)
        self.assertEqual(updated["revision"], 2)
        with self.assertRaises(RevisionConflictError) as error:
            self.store.update_project(self.project["id"], second, 1)
        self.assertEqual(error.exception.details["current_revision"], 2)
        self.assertEqual(self.store.get_project(self.project["id"])["manifest"]["scenes"][0]["title"], "FIRST ACTOR")

    def test_corrupt_state_has_a_structured_error(self):
        broken = self.root / "broken-state"
        broken.mkdir()
        (broken / "cohortframe.sqlite3").write_bytes(b"not a sqlite database")
        with self.assertRaises(StateError) as error:
            Store(broken)
        self.assertNotIn(str(broken), str(error.exception))

    def test_identical_retries_survive_later_project_changes(self):
        original = self.submit()
        changed = manifest()
        changed["scenes"][0]["title"] = "NEW REVISION"
        self.store.update_project(self.project["id"], changed, 1)
        repeated = self.store.submit_job(self.project["id"], 1, "first")
        self.assertEqual(repeated["id"], original["id"])
        self.assertEqual(repeated["snapshot"]["manifest"]["scenes"][0]["title"], "HELLO")
        with self.assertRaises(IdempotencyConflictError):
            self.store.submit_job(self.project["id"], 2, "first")
        with self.assertRaises(RevisionConflictError):
            self.store.submit_job(self.project["id"], 1, "new-key")

    def test_idempotency_keys_are_project_scoped(self):
        other = self.store.create_project(manifest(), base_dir=self.assets)
        first = self.submit("shared-key")
        second = self.store.submit_job(other["id"], 1, "shared-key")
        self.assertNotEqual(first["id"], second["id"])

    def test_concurrent_duplicate_submissions_create_one_job(self):
        def submit(_):
            return Store(self.store.home).submit_job(self.project["id"], 1, "concurrent")["id"]
        with ThreadPoolExecutor(max_workers=8) as pool:
            identifiers = list(pool.map(submit, range(16)))
        self.assertEqual(len(set(identifiers)), 1)
        self.assertEqual(len(self.store.list_jobs()), 1)
        self.assertEqual(len(list(self.store.jobs_dir.iterdir())), 1)

    def test_audio_and_manifest_are_snapshotted_before_execution(self):
        source = self.assets / "voice.wav"
        write_wave(source, 100)
        before = source.read_bytes()
        data = manifest() | {"audio": "voice.wav"}
        project = self.store.create_project(data, base_dir=self.assets)
        job = self.store.submit_job(project["id"], 1, "audio")
        write_wave(source, -100)
        changed = copy.deepcopy(data)
        changed["scenes"][0]["title"] = "CHANGED"
        self.store.update_project(project["id"], changed, 1, base_dir=self.assets)
        snapshot_audio = Path(job["snapshot_dir"]) / job["snapshot"]["audio"]["path"]
        self.assertEqual(snapshot_audio.read_bytes(), before)
        self.assertNotEqual(snapshot_audio.read_bytes(), source.read_bytes())
        self.assertEqual(job["snapshot"]["manifest"]["audio"], "audio.wav")
        observed = []
        def runner(snapshot, folder, cancelled):
            observed.append(snapshot["manifest"]["scenes"][0]["title"])
            return stub_artifact(snapshot, folder, cancelled)
        self.assertEqual(self.store.run_job(job["id"], runner)["state"], "succeeded")
        self.assertEqual(observed, ["HELLO"])

    def test_queued_cancellation_does_not_execute(self):
        job = self.submit()
        cancelled = self.store.cancel_job(job["id"])
        self.assertEqual(cancelled["state"], "cancelled")
        self.assertEqual(cancelled["attempts"], 0)
        with self.assertRaises(StateError):
            self.store.run_job(job["id"], stub_artifact)

    def test_live_worker_not_recovered_or_executed_twice_and_can_cancel(self):
        job = self.submit()
        started, continue_work = threading.Event(), threading.Event()
        observed = []
        def runner(snapshot, folder, cancelled):
            started.set()
            if not continue_work.wait(5):
                raise RuntimeError("Test synchronisation timed out")
            self.assertTrue(cancelled())
            raise JobCancelled("Cancelled by another caller.")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.store.run_job, job["id"], runner)
            try:
                self.assertTrue(started.wait(5))
                self.assertEqual(self.store.recover_jobs(), [])
                with self.assertRaises(StateError):
                    self.store.run_job(job["id"], stub_artifact)
                requested = self.store.cancel_job(job["id"])
                self.assertEqual(requested["state"], "cancel_requested")
                self.assertEqual(self.store.recover_jobs(), [])
            finally:
                continue_work.set()
            observed.append(future.result(timeout=5))
        self.assertEqual(observed[0]["state"], "cancelled")
        self.assertIsNone(observed[0]["result"])

    def test_cancel_request_wins_over_late_success(self):
        job = self.submit()
        def runner(snapshot, folder, cancelled):
            result = stub_artifact(snapshot, folder, cancelled)
            self.store.cancel_job(job["id"])
            return result
        result = self.store.run_job(job["id"], runner)
        self.assertEqual(result["state"], "cancelled")
        self.assertIsNone(result["result"])

    def test_failure_is_structured_private_exception_not_persisted_and_retry_works(self):
        job = self.submit()
        def broken(snapshot, folder, cancelled):
            raise RuntimeError("secret-token-123 /home/private/customer.wav")
        failed = self.store.run_job(job["id"], broken)
        self.assertEqual(failed["state"], "failed")
        self.assertEqual(failed["error"]["code"], "render_failed")
        self.assertNotIn("secret-token", json.dumps(failed))
        self.assertNotIn("/home/private", json.dumps(failed))
        self.assertEqual(self.store.retry_job(job["id"])["state"], "queued")
        succeeded = self.store.run_job(job["id"], stub_artifact)
        self.assertEqual(succeeded["state"], "succeeded")
        self.assertEqual(succeeded["attempts"], 2)
        with self.assertRaises(StateError):
            self.store.run_job(job["id"], stub_artifact)
        with self.assertRaises(StateError):
            self.store.retry_job(job["id"])
        self.assertEqual(self.store.cancel_job(job["id"])["state"], "succeeded")

    def test_snapshot_tampering_is_detected_before_runner(self):
        job = self.submit()
        file = Path(job["snapshot_path"])
        file.chmod(0o600)
        changed = job["snapshot"]
        changed["manifest"]["scenes"][0]["title"] = "TAMPERED"
        file.write_text(json.dumps(changed))
        with patch(__name__ + ".stub_artifact") as runner:
            failed = self.store.run_job(job["id"], runner)
            runner.assert_not_called()
        self.assertEqual(failed["state"], "failed")
        self.assertEqual(failed["error"]["code"], "validation_error")

    def test_bad_identifiers_and_artifact_paths_are_not_trusted(self):
        for identifier in ("../escape", "x" * 32, "/tmp/outside", "A" * 32):
            for method in (self.store.get_project, self.store.get_job, self.store.cancel_job):
                with self.subTest(identifier=identifier), self.assertRaises(ValidationError):
                    method(identifier)
        with self.assertRaises(NotFoundError):
            self.store.get_job("0" * 32)
        job = self.submit()
        result = self.store.run_job(job["id"], lambda *_: {"path": "../outside.mp4", "bytes": 1, "sha256": "0" * 64})
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["error"]["code"], "validation_error")

    @unittest.skipUnless(os.name == "posix", "Symlink behavior exercised on POSIX")
    def test_relative_audio_cannot_escape_through_parent_or_symlink(self):
        outside = self.root / "outside"
        outside.mkdir()
        source = outside / "voice.wav"
        write_wave(source)
        (self.assets / "escape").symlink_to(outside, target_is_directory=True)
        (self.assets / "linked.wav").symlink_to(source)
        for name in ("../outside/voice.wav", "escape/voice.wav", "linked.wav"):
            with self.subTest(path=name), self.assertRaises(ValidationError):
                self.store.create_project(manifest() | {"audio": name}, base_dir=self.assets)

    @unittest.skipUnless(os.name == "posix", "Killed-worker recovery is verified on POSIX")
    def test_killed_worker_recovered_and_original_snapshot_retried(self):
        job = self.submit()
        ready = Path(job["snapshot_dir"]) / "worker-ready"
        script = (
            "import sys,time\nfrom pathlib import Path\nfrom cohortframe.core import Store\n"
            "def hold(snapshot,folder,cancelled):\n"
            "    (folder/'worker-ready').write_text('ready')\n"
            "    while True: time.sleep(.1)\n"
            "Store(sys.argv[1]).run_job(sys.argv[2],hold)\n"
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        process = subprocess.Popen([sys.executable, "-c", script, str(self.store.home), job["id"]],
                                   env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 8
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(ready.exists(), "Child worker did not enter the renderer")
            self.assertEqual(self.store.get_job(job["id"])["state"], "running")
            self.assertEqual(self.store.recover_jobs(), [])
            process.kill()
            process.wait(timeout=5)
            recovered = Store(self.store.home).recover_jobs()
            self.assertEqual([entry["id"] for entry in recovered], [job["id"]])
            self.assertEqual(recovered[0]["state"], "interrupted")
            self.assertEqual(recovered[0]["snapshot_digest"], job["snapshot_digest"])
            with self.assertRaises(StateError):
                self.store.run_job(job["id"], stub_artifact)
            self.store.retry_job(job["id"])
            completed = self.store.run_job(job["id"], stub_artifact)
            self.assertEqual(completed["state"], "succeeded")
            self.assertEqual(completed["attempts"], 2)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if process.stderr is not None:
                process.stderr.close()


if __name__ == "__main__":
    unittest.main()
