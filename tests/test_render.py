"""Actual short media renders plus cancellation and corrupted-input boundaries."""

from __future__ import annotations

import hashlib
import importlib
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import wave

from cohortframe.models import JobCancelled, ValidationError

renderer = importlib.import_module("cohortframe.render")
MEDIA_AVAILABLE = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def snapshot(width=320, height=180, *, title="Built by agents", duration=0.4):
    return {
        "snapshot_version": 1,
        "project_id": "a" * 32,
        "project_revision": 1,
        "manifest_sha256": "0" * 64,
        "manifest": {
            "version": 1, "name": "Renderer evidence", "width": width,
            "height": height, "fps": 10,
            "scenes": [{"id": "intro", "title": title, "subtitle": "Local and inspectable", "duration": duration, "color": "#136A68"}],
        },
        "audio": None,
    }


def add_audio(data: dict, directory: Path, seconds=1.0):
    path = directory / "audio.wav"
    rate = 16000
    samples = [int(10000 * math.sin(2 * math.pi * 440 * n / rate)) for n in range(int(seconds * rate))]
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    data["audio"] = {"path": "audio.wav", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
    data["manifest"]["audio"] = "audio.wav"


@unittest.skipUnless(MEDIA_AVAILABLE, "Installed ffmpeg and ffprobe are required for integration tests")
class ActualRenderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cohortframe-render-test-")
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_mp4_audio_fade_and_quantized_scene_duration(self):
        data = snapshot(duration=0.35)
        data["manifest"]["scenes"].append({"id": "next", "title": "For the next cohort", "duration": 0.45, "color": "#6F3288"})
        add_audio(data, self.directory)
        artifact = renderer.render(data, self.directory, lambda: False)
        output = self.directory / artifact["path"]
        self.assertEqual(artifact["video_codec"], "h264")
        self.assertEqual(artifact["audio_codec"], "aac")
        self.assertEqual((artifact["width"], artifact["height"]), (320, 180))
        self.assertEqual(artifact["frame_count"], 9)
        self.assertAlmostEqual(artifact["requested_duration"], 0.8)
        self.assertAlmostEqual(artifact["duration"], 0.9, delta=0.05)
        self.assertEqual(artifact["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual(artifact["bytes"], output.stat().st_size)
        decoded = subprocess.run(
            [shutil.which("ffmpeg"), "-v", "error", "-protocol_whitelist", "file,pipe", "-i", str(output), "-vn", "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"],
            check=True, capture_output=True, timeout=10,
        ).stdout
        samples = struct.unpack(f"<{len(decoded) // 2}h", decoded)
        rms = lambda values: math.sqrt(sum(value * value for value in values) / len(values))
        middle = rms(samples[5000:6500])
        self.assertGreater(middle, 1000)
        self.assertLess(rms(samples[:800]), middle * 0.5)
        self.assertLess(rms(samples[-800:]), middle * 0.5)
        self.assertFalse(list(self.directory.glob(".render-*")))

    def test_portrait_punctuation_is_raster_data_not_executable_text(self):
        data = snapshot(180, 320, title="A: [x]; %{pts} $(touch OWNED) ' \" \\")
        artifact = renderer.render(data, self.directory, lambda: False)
        self.assertEqual((artifact["width"], artifact["height"]), (180, 320))
        self.assertIsNone(artifact["audio_codec"])
        self.assertFalse((self.directory / "OWNED").exists())
        self.assertTrue((self.directory / artifact["path"]).is_file())

    def test_cancelling_live_encoder_reaps_process_and_commits_no_artifact(self):
        started = []
        original = subprocess.Popen

        def launch(*args, **kwargs):
            process = original(*args, **kwargs)
            started.append(process)
            return process

        with patch.object(renderer.subprocess, "Popen", side_effect=launch):
            with self.assertRaises(JobCancelled):
                renderer.render(snapshot(), self.directory, lambda: bool(started))
        self.assertEqual(len(started), 1)
        self.assertIsNotNone(started[0].poll())
        self.assertFalse((self.directory / "artifact.mp4").exists())
        self.assertFalse(list(self.directory.glob(".render-*")))

    def test_changed_audio_snapshot_is_rejected(self):
        data = snapshot()
        add_audio(data, self.directory)
        audio = self.directory / "audio.wav"
        content = bytearray(audio.read_bytes())
        content[-1] ^= 1
        audio.write_bytes(content)
        with self.assertRaisesRegex(ValidationError, "SHA-256"):
            renderer.render(data, self.directory, lambda: False)
        self.assertFalse((self.directory / "artifact.mp4").exists())


class RendererBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cohortframe-render-boundary-")
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_cancelled_before_start_never_runs_an_executable(self):
        with patch.object(renderer.subprocess, "Popen") as process:
            with self.assertRaises(JobCancelled):
                renderer.render(snapshot(), self.directory, lambda: True)
            process.assert_not_called()

    def test_missing_dependency_is_an_explicit_failure(self):
        with patch.object(renderer.shutil, "which", return_value=None):
            with self.assertRaises(renderer.RenderDependencyError) as failure:
                renderer.render(snapshot(), self.directory, lambda: False)
        self.assertEqual(failure.exception.code, "dependency_unavailable")
        self.assertFalse((self.directory / "artifact.mp4").exists())

    def test_unsupported_text_and_audio_path_are_rejected(self):
        with self.assertRaisesRegex(ValidationError, "ASCII"):
            renderer.render(snapshot(title="Hello \u2603"), self.directory, lambda: False)
        data = snapshot()
        data["audio"] = {"path": "../outside.wav", "sha256": "0" * 64, "bytes": 1}
        with self.assertRaisesRegex(ValidationError, "audio.wav"):
            renderer._audio(data, self.directory, lambda: False, time.monotonic() + 2)

    def test_enormous_integer_duration_is_a_validation_error_not_overflow(self):
        with self.assertRaises(ValidationError):
            renderer.render(snapshot(duration=10 ** 500), self.directory, lambda: False)

    def test_nonzero_process_exit_is_not_reported_as_success(self):
        with self.assertRaisesRegex(renderer.RenderError, "status 7"):
            renderer._run(
                [sys.executable, "-c", "import sys; sys.stderr.write('synthetic failure'); sys.exit(7)"],
                self.directory, lambda: False, time.monotonic() + 5,
            )

    def test_wall_time_limit_stops_and_reaps_worker(self):
        started = []
        original = subprocess.Popen

        def launch(*args, **kwargs):
            process = original(*args, **kwargs)
            started.append(process)
            return process

        with patch.object(renderer.subprocess, "Popen", side_effect=launch):
            with self.assertRaises(renderer.RenderTimeout):
                renderer._run(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    self.directory, lambda: False, time.monotonic() + 0.2,
                )
        self.assertEqual(len(started), 1)
        self.assertIsNotNone(started[0].poll())


if __name__ == "__main__":
    unittest.main()
