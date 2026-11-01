"""Stable JSON CLI. No HTTP listener, live provider, or hidden external calls."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import struct
import subprocess
import sys
import uuid
import wave

from . import __version__
from .core import Store
from .models import CohortFrameError, MAX_JSON_BYTES, ValidationError, parse_json
from .workflow import preflight, preview, export_studio
from .render import render


class ArgumentError(Exception):
    code = "invalid_arguments"


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentError(message)


def capabilities():
    return {
        "product": "CohortFrame", "version": __version__, "stage": "alpha",
        "interface_version": "1", "project_schema_version": 1,
        "operations": ["project.create", "project.show", "project.update", "job.submit",
                       "job.run", "job.show", "job.list", "job.cancel", "job.retry",
                       "job.recover", "project.list", "validate", "preview", "studio", "demo", "doctor"],
        "render": {"format": "mp4", "video_codec": "h264", "audio_codec": "aac",
                   "scene_type": "title_card", "audio_input": "local_pcm_wav",
                   "max_duration_seconds": 60, "max_scenes": 12,
                   "text": "Printable ASCII; bitmap font; uppercase display"},
        "providers": [], "network_service": False, "paid_generation": False,
        "security": {"os_sandbox": False, "audience": "trusted local operators and assets",
                     "secrets_required": False, "code_templates": False},
        "durability": {"storage": "SQLite and local job snapshots",
                       "idempotency": "project-scoped request key",
                       "concurrent_edits": "expected_revision required"},
        "execution": {"worker": "explicit job run", "background_service": False},
    }


def doctor():
    tools = {}
    for name in ("ffmpeg", "ffprobe"):
        executable = shutil.which(name)
        item = {"available": bool(executable), "path": executable}
        if executable:
            try:
                process = subprocess.run([executable, "-version"], capture_output=True,
                                         text=True, timeout=10, check=False)
                item["available"] = process.returncode == 0
                item["version"] = process.stdout.splitlines()[0] if process.stdout else None
            except (OSError, subprocess.SubprocessError) as exc:
                item["available"] = False
                item["error"] = type(exc).__name__
        tools[name] = item
    encoders = {"libx264": False, "aac": False}
    if tools["ffmpeg"]["available"]:
        try:
            output = subprocess.run([tools["ffmpeg"]["path"], "-hide_banner", "-encoders"],
                                    capture_output=True, text=True, timeout=10, check=False)
            names = {line.split()[1] for line in output.stdout.splitlines() if len(line.split()) >= 2}
            encoders = {name: output.returncode == 0 and name in names for name in encoders}
        except (OSError, subprocess.SubprocessError):
            pass
    return {"ready": all(item["available"] for item in tools.values()) and all(encoders.values()),
            "encoders": encoders,
            "python": sys.version.split()[0], "tools": tools,
            "note": "Rendering requires a trusted FFmpeg build with libx264 and AAC support."}


def read_manifest(filename: str):
    path = Path(filename).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValidationError("Project JSON must be a regular local file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValidationError("Project JSON must be a regular local file")
        raw = source.read(MAX_JSON_BYTES + 1)
    return parse_json(raw), path.parent


def demo_audio(path: Path, seconds=12):
    """Original procedural test audio, not a model-generated music claim."""
    rate = 22050
    chords = [(261.6256, 329.6276, 391.9954), (220.0, 261.6256, 329.6276),
              (174.6141, 220.0, 261.6256), (195.9977, 246.9417, 293.6648)]
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        for start in range(0, rate * seconds, rate):
            samples = bytearray()
            for index in range(start, min(start + rate, rate * seconds)):
                t = index / rate
                chord = chords[min(3, int(t / 3))]
                local = t % 3
                envelope = min(1.0, t / .25, (seconds - t) / .6)
                envelope *= .6 + .4 * math.exp(-local * 1.5)
                value = sum(math.sin(2 * math.pi * freq * t) for freq in chord) / 3
                samples.extend(struct.pack("<h", int(value * envelope * 6500)))
            audio.writeframes(samples)


def parser():
    p = Parser(prog="cohortframe", description="Agent-operated local video. Commands return JSON.")
    p.add_argument("--home", default=os.environ.get("COHORTFRAME_HOME", str(Path.home() / ".cohortframe")),
                   help="Local state directory. Put this option before the command.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    sub.add_parser("doctor")
    sub.add_parser("validate", help="Check schema and exact title-card layout without creating a job").add_argument("file")
    preview_cmd = sub.add_parser("preview", help="Write exact PNG scene previews without FFmpeg")
    preview_cmd.add_argument("file")
    preview_cmd.add_argument("--output", required=True, help="New output directory; existing directories are never replaced")
    studio = sub.add_parser("studio", help="Export the offline visual scene composer")
    studio.add_argument("--output", required=True, help="New directory for the offline composer")
    demo = sub.add_parser("demo", help="Render an original 12-second local demonstration")
    demo.add_argument("--width", type=int, default=1280)
    demo.add_argument("--height", type=int, default=720)
    project = sub.add_parser("project").add_subparsers(dest="action", required=True)
    project.add_parser("list")
    project.add_parser("create").add_argument("file")
    project.add_parser("show").add_argument("id")
    update = project.add_parser("update")
    update.add_argument("id")
    update.add_argument("file")
    update.add_argument("--expected-revision", required=True, type=int)
    job = sub.add_parser("job").add_subparsers(dest="action", required=True)
    submit = job.add_parser("submit")
    submit.add_argument("project_id")
    submit.add_argument("--expected-revision", required=True, type=int)
    submit.add_argument("--key", required=True)
    submit.add_argument("--run", action="store_true")
    for action in ("show", "run", "cancel", "retry"):
        command = job.add_parser(action)
        command.add_argument("id")
        if action == "retry":
            command.add_argument("--run", action="store_true")
    job.add_parser("list")
    job.add_parser("recover")
    return p


def dispatch(args):
    if args.command == "capabilities":
        return capabilities()
    if args.command == "doctor":
        return doctor()
    if args.command in ("validate", "preview"):
        manifest, base = read_manifest(args.file)
        return preflight(manifest) if args.command == "validate" else preview(manifest, Path(args.output).expanduser())
    if args.command == "studio":
        return export_studio(Path(args.output).expanduser())
    store = Store(Path(args.home).expanduser())
    if args.command == "project":
        if args.action == "list":
            return store.list_projects()
        if args.action == "show":
            return store.get_project(args.id)
        manifest, base = read_manifest(args.file)
        if args.action == "create":
            return store.create_project(manifest, base_dir=base)
        return store.update_project(args.id, manifest, args.expected_revision, base_dir=base)
    if args.command == "demo":
        location = Path(args.home).expanduser().resolve() / "demo_assets"
        location.mkdir(parents=True, exist_ok=True)
        audio = location / (uuid.uuid4().hex + ".wav")
        demo_audio(audio)
        project = store.create_project({
            "version": 1, "name": "CohortFrame 0.2 demonstration",
            "width": args.width, "height": args.height, "fps": 24,
            "audio": str(audio),
            "scenes": [
                {"id": "create", "title": "COHORTFRAME", "subtitle": "BUILT BY AGENTS. FOR AGENTS.", "duration": 4, "color": "#10253F"},
                {"id": "verify", "title": "CREATE. VERIFY. EVOLVE.", "subtitle": "LOCAL VIDEO. VISIBLE RESULTS.", "duration": 4, "color": "#123E3B"},
                {"id": "continue", "title": "THE NEXT GENERATION", "subtitle": "INHERIT THE WORK. IMPROVE THE FUTURE.", "duration": 4, "color": "#392E52"},
            ],
        }, base_dir=location)
        job = store.submit_job(project["id"], project["revision"], "demo-" + uuid.uuid4().hex)
        result = store.run_job(job["id"], render)
        return {"project": project, "job": result,
                "audio_provenance": "Original procedural chord fixture; no cloud generation."}
    if args.action == "submit":
        job = store.submit_job(args.project_id, args.expected_revision, args.key)
        return store.run_job(job["id"], render) if args.run and job["state"] == "queued" else job
    if args.action == "show":
        return store.get_job(args.id)
    if args.action == "list":
        return store.list_jobs()
    if args.action == "run":
        job = store.get_job(args.id)
        return job if job["state"] == "succeeded" else store.run_job(args.id, render)
    if args.action == "cancel":
        return store.cancel_job(args.id)
    if args.action == "recover":
        return store.recover_jobs()
    job = store.retry_job(args.id)
    return store.run_job(args.id, render) if args.run else job


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        result = dispatch(args)
        job = result.get("job", result) if isinstance(result, dict) else None
        if isinstance(job, dict) and job.get("state") in ("failed", "interrupted", "cancelled"):
            print(json.dumps({"ok": False, "interface_version": "1", "result": result,
                              "error": {"code": "job_" + job["state"], "message": "Job did not produce a successful artifact"}}, ensure_ascii=True))
            return 4
        print(json.dumps({"ok": True, "interface_version": "1", "result": result}, ensure_ascii=True))
        return 0
    except (CohortFrameError, ArgumentError) as exc:
        print(json.dumps({"ok": False, "interface_version": "1", "error": {
            "code": getattr(exc, "code", "validation_error"), "message": str(exc),
            "details": getattr(exc, "details", {})}}))
        return 2
    except sqlite3.Error as exc:
        print(json.dumps({"ok": False, "interface_version": "1", "error": {
            "code": "state_store_unavailable", "message": "Local state database is unavailable or invalid",
            "details": {"exception_type": type(exc).__name__}}}))
        return 3
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "interface_version": "1", "error": {
            "code": "local_operation_failed", "message": str(exc)}}))
        return 3


