"""Bounded local title-card renderer using only Python and installed FFmpeg.

This is a trusted-local alpha, not an OS sandbox. It never interprets project
text as code or a filter, and FFmpeg receives only generated frames and an
optional checked PCM WAV snapshot. Resource limits bound this renderer's work;
they do not protect against a compromised host, executable, or native decoder.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import textwrap
import time
import wave
from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction

from .font import paint_text, printable, text_width
from .models import CohortFrameError, JobCancelled, ValidationError, scene_frames as quantize_scene_frames


RENDER_TIMEOUT_SECONDS = 180.0
MAX_AUDIO_BYTES = 32 * 1024 * 1024
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
MAX_LOG_BYTES = 64 * 1024
MAX_PROBE_BYTES = 256 * 1024
_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")


class RenderError(CohortFrameError):
    code = "render_failed"


class RenderTimeout(RenderError):
    code = "render_timeout"


class RenderDependencyError(RenderError):
    code = "dependency_unavailable"


def _check_cancel(cancelled: Callable[[], bool], deadline: float | None = None) -> None:
    if cancelled():
        raise JobCancelled("Rendering was cancelled; no artifact was committed.")
    if deadline is not None and time.monotonic() >= deadline:
        raise RenderTimeout("The local renderer exceeded its wall-time allowance.")


def _stop(process: subprocess.Popen) -> None:
    """Reap a child on cancellation, timeout, or another failure."""
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
        process.wait(timeout=2.0)


def _run(
    command: list[str],
    directory: Path,
    cancelled: Callable[[], bool],
    deadline: float,
    *,
    output: Path | None = None,
) -> bytes:
    """Run without a shell, cap captured output, and keep cancellation responsive."""
    _check_cancel(cancelled, deadline)
    with tempfile.TemporaryFile(dir=directory) as stdout, tempfile.TemporaryFile(dir=directory) as stderr:
        try:
            process = subprocess.Popen(
                command,
                cwd=directory,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                shell=False,
                start_new_session=os.name == "posix",
            )
        except OSError as error:
            raise RenderDependencyError("The local media executable could not be started.") from error
        try:
            while process.poll() is None:
                _check_cancel(cancelled, deadline)
                if os.fstat(stderr.fileno()).st_size > MAX_LOG_BYTES or os.fstat(stdout.fileno()).st_size > MAX_PROBE_BYTES:
                    raise RenderError("The media process exceeded its diagnostic-output allowance.")
                if output is not None and output.exists() and output.stat().st_size > MAX_OUTPUT_BYTES:
                    raise RenderError("The rendered artifact exceeded its file-size allowance.")
                time.sleep(0.04)
            _check_cancel(cancelled, deadline)
            if os.fstat(stderr.fileno()).st_size > MAX_LOG_BYTES or os.fstat(stdout.fileno()).st_size > MAX_PROBE_BYTES:
                raise RenderError("The media process exceeded its diagnostic-output allowance.")
            if process.returncode:
                stderr.seek(max(0, os.fstat(stderr.fileno()).st_size - 1200))
                detail = stderr.read(1200).decode("utf-8", errors="replace").strip()
                detail = detail.replace(str(directory), "<job>")
                raise RenderError(f"The media process exited with status {process.returncode}: {detail}")
            stdout.seek(0)
            return stdout.read(MAX_PROBE_BYTES + 1)
        finally:
            _stop(process)


def _safe_child(directory: Path, relative: str, *, existing: bool = False) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValidationError("A renderer path must be a relative job path.")
    path = Path(relative)
    if path.is_absolute() or any(part in (".", "..") for part in path.parts):
        raise ValidationError("A renderer path must stay inside the job directory.")
    candidate = directory / path
    if candidate.is_symlink():
        raise ValidationError("Renderer inputs and outputs cannot be symbolic links.")
    try:
        resolved = candidate.resolve(strict=existing)
        resolved.relative_to(directory)
    except (OSError, ValueError) as error:
        raise ValidationError("A renderer path does not resolve inside the job directory.") from error
    return resolved


def _digest(path: Path, cancelled: Callable[[], bool], deadline: float) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            _check_cancel(cancelled, deadline)
            digest.update(chunk)
    return digest.hexdigest()


def _audio(snapshot: dict, directory: Path, cancelled: Callable[[], bool], deadline: float) -> str | None:
    record = snapshot.get("audio")
    if record is None:
        return None
    if not isinstance(record, dict) or record.get("path") != "audio.wav":
        raise ValidationError("The renderer accepts only the job's audio.wav snapshot.")
    path = _safe_child(directory, "audio.wav", existing=True)
    if not path.is_file():
        raise ValidationError("The audio snapshot is not a regular file.")
    size = path.stat().st_size
    if not 0 < size <= MAX_AUDIO_BYTES or type(record.get("bytes")) is not int or size != record["bytes"]:
        raise ValidationError("The audio snapshot size changed or exceeds 32 MiB.")
    if not isinstance(record.get("sha256"), str) or not _HASH.fullmatch(record["sha256"]):
        raise ValidationError("The audio snapshot has no valid SHA-256 digest.")
    if _digest(path, cancelled, deadline) != record["sha256"]:
        raise ValidationError("The audio snapshot no longer matches its recorded SHA-256 digest.")
    try:
        with wave.open(str(path), "rb") as source:
            channels, sample_width, rate, count = source.getparams()[:4]
            if source.getcomptype() != "NONE" or channels not in (1, 2) or sample_width not in (1, 2, 3, 4):
                raise ValidationError("Audio must be uncompressed mono or stereo PCM WAV.")
            if not 8000 <= rate <= 96000 or not 0 < count / rate <= 120:
                raise ValidationError("Audio must use 8–96 kHz sampling and last at most 120 seconds.")
            expected = count * channels * sample_width
            consumed = 0
            while data := source.readframes(8192):
                _check_cancel(cancelled, deadline)
                consumed += len(data)
            if consumed != expected:
                raise ValidationError("The audio snapshot contains truncated PCM data.")
    except (wave.Error, EOFError, OSError) as error:
        raise ValidationError("The audio snapshot is not a readable PCM WAV file.") from error
    return "audio.wav"


def _settings(snapshot: dict) -> tuple[dict, int, int, int, list[int]]:
    if not isinstance(snapshot, dict) or type(snapshot.get("snapshot_version")) is not int or snapshot["snapshot_version"] != 1:
        raise ValidationError("The renderer requires a version 1 job snapshot.")
    manifest = snapshot.get("manifest")
    if not isinstance(manifest, dict) or type(manifest.get("version")) is not int or manifest["version"] != 1:
        raise ValidationError("The snapshot has no version 1 project manifest.")
    width, height, fps = (manifest.get(key) for key in ("width", "height", "fps"))
    if any(type(value) is not int or not 16 <= value <= 1920 or value % 2 for value in (width, height)):
        raise ValidationError("Video dimensions must be even integers between 16 and 1920.")
    if type(fps) is not int or not 1 <= fps <= 30:
        raise ValidationError("Video frame rate must be an integer between 1 and 30.")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 12:
        raise ValidationError("A render requires between 1 and 12 scenes.")
    frames = []
    requested = Decimal("0")
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValidationError("Every scene must be an object.")
        title, subtitle = scene.get("title"), scene.get("subtitle", "")
        if not isinstance(title, str) or not title.strip() or len(title) > 160:
            raise ValidationError("A scene needs a title of 1–160 characters.")
        if not isinstance(subtitle, str) or len(subtitle) > 280:
            raise ValidationError("Scene subtitles must contain at most 280 characters.")
        if not printable(title) or not printable(subtitle):
            raise ValidationError("The v0.1 bitmap renderer supports printable ASCII and newlines only.")
        if not isinstance(scene.get("color", "#183153"), str) or not _COLOR.fullmatch(scene.get("color", "#183153")):
            raise ValidationError("Scene color must have the form #RRGGBB.")
        duration = scene.get("duration")
        if type(duration) not in (int, float) or duration <= 0 or duration > 60 or not math.isfinite(duration) or duration * fps < 1 - 1e-9:
            raise ValidationError("Each scene must last at least one frame and at most 60 seconds.")
        requested += Decimal(str(duration))
        frames.append(quantize_scene_frames(duration, fps))
    if requested > 60 or sum(frames) / fps > 60:
        raise ValidationError("Requested and frame-quantized video duration must not exceed 60 seconds.")
    return manifest, width, height, fps, frames


def _lines(text: str, width: int, scale: int) -> list[str]:
    columns = (width + scale) // (6 * scale)
    if columns < 1:
        return []
    wrapper = textwrap.TextWrapper(width=columns, break_long_words=True, break_on_hyphens=False)
    result = []
    for paragraph in text.strip().split("\n"):
        result.extend(wrapper.wrap(paragraph) or [""])
    return result


def _card(
    scene: dict,
    width: int,
    height: int,
    index: int,
    total: int,
    cancelled: Callable[[], bool],
    deadline: float,
) -> bytes:
    """Render a deterministic PPM card with no hidden font or system dependency."""
    color = scene.get("color", "#183153")
    tint = tuple(int(color[offset : offset + 2], 16) for offset in (1, 3, 5))
    accent = tuple(min(255, int(channel * 0.45 + 140)) for channel in tint)
    pixels = bytearray(width * height * 3)
    for y in range(height):
        if y % 64 == 0:
            _check_cancel(cancelled, deadline)
        amount = 0.12 + 0.13 * y / max(1, height - 1)
        row_color = bytes(min(255, int(channel * amount + 9)) for channel in tint)
        pixels[y * width * 3 : (y + 1) * width * 3] = row_color * width

    def rectangle(x: int, y: int, w: int, h: int, rgb: tuple[int, int, int]) -> None:
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(width, x + w), min(height, y + h)
        if x0 >= x1 or y0 >= y1:
            return
        row = bytes(rgb) * (x1 - x0)
        for yy in range(y0, y1):
            start = (yy * width + x0) * 3
            pixels[start : start + len(row)] = row

    margin = max(8, round(min(width, height) * 0.085))
    available_width = width - 2 * margin
    small_scale = max(1, min(width, height) // 220)
    header_left, header_right = f"{index + 1:02d} / {total:02d}", "COHORTFRAME"
    if text_width(header_left + "  " + header_right, small_scale) > available_width:
        raise ValidationError("The selected dimensions are too small for the title-card layout.")

    # Understated right-hand geometry leaves the high-contrast reading area clear.
    faint = tuple(min(255, int(channel * 0.32 + 12)) for channel in tint)
    unit = max(5, min(width, height) // 28)
    for step in range(4):
        rectangle(width - margin - unit * (step + 1), margin + unit * (step + 2), unit - 2, unit - 2, faint)
    paint_text(rectangle, header_left, margin, margin, small_scale, accent)
    paint_text(rectangle, header_right, width - margin - text_width(header_right, small_scale), margin, small_scale, (175, 184, 196))
    rectangle(margin, margin + 11 * small_scale, available_width, 1, faint)

    main_top = max(margin + 18 * small_scale, round(height * (0.24 if width >= height else 0.27)))
    main_bottom = height - margin - 20 * small_scale
    available_height = main_bottom - main_top
    preferred = max(1, int(min(width * 0.072, height * 0.105) / 7))
    selected = None
    for title_scale in range(preferred, 0, -1):
        subtitle_scale = max(1, min(max(1, min(width, height) // 180), (title_scale + 1) // 2))
        title_lines = _lines(scene["title"], available_width, title_scale)
        subtitle_lines = _lines(scene.get("subtitle", ""), available_width, subtitle_scale) if scene.get("subtitle", "").strip() else []
        title_height = (len(title_lines) * 9 - 2) * title_scale
        subtitle_height = (len(subtitle_lines) * 9 - 2) * subtitle_scale if subtitle_lines else 0
        gap = max(10, title_scale * 3) if subtitle_lines else 0
        if title_lines and title_height + gap + subtitle_height <= available_height:
            selected = (title_scale, subtitle_scale, title_lines, subtitle_lines, title_height + gap + subtitle_height, gap)
            break
    if selected is None:
        raise ValidationError("The scene text does not fit the selected dimensions; shorten it or enlarge the frame.")
    title_scale, subtitle_scale, title_lines, subtitle_lines, block_height, gap = selected
    y = main_top + (available_height - block_height) // 2
    rectangle(margin, y - max(10, title_scale * 3), max(24, title_scale * 8), max(2, small_scale), accent)
    for line in title_lines:
        paint_text(rectangle, line, margin, y, title_scale, (246, 247, 249))
        y += title_scale * 9
    y -= 2 * title_scale
    y += gap
    for line in subtitle_lines:
        paint_text(rectangle, line, margin, y, subtitle_scale, (185, 196, 210))
        y += subtitle_scale * 9

    footer_y = height - margin - 7 * small_scale
    label = "LOCAL / SNAPSHOT"
    if text_width(label, small_scale) <= available_width:
        paint_text(rectangle, label, margin, footer_y, small_scale, (145, 157, 174))
    track_y = height - max(4, margin // 3)
    rectangle(margin, track_y, available_width, max(2, small_scale), faint)
    rectangle(margin, track_y, max(1, available_width * (index + 1) // total), max(2, small_scale), accent)
    return f"P6\n{width} {height}\n255\n".encode("ascii") + pixels


def _probe(
    ffprobe: str,
    path: Path,
    directory: Path,
    width: int,
    height: int,
    fps: int,
    frames: int,
    has_audio: bool,
    cancelled: Callable[[], bool],
    deadline: float,
) -> dict:
    result = _run(
        [
            ffprobe, "-v", "error", "-protocol_whitelist", "file", "-show_entries",
            "stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate,nb_frames,duration,channels,sample_rate:format=duration,size,format_name",
            "-of", "json", path.relative_to(directory).as_posix(),
        ],
        directory, cancelled, deadline,
    )
    try:
        data = json.loads(result)
        videos = [stream for stream in data["streams"] if stream.get("codec_type") == "video"]
        audios = [stream for stream in data["streams"] if stream.get("codec_type") == "audio"]
        video = videos[0]
        duration = float(data["format"]["duration"])
        valid = (
            len(videos) == 1 and len(data["streams"]) == 1 + int(has_audio)
            and video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p"
            and (video["width"], video["height"]) == (width, height)
            and Fraction(video["avg_frame_rate"]) == fps and int(video["nb_frames"]) == frames
            and math.isfinite(duration) and abs(duration - frames / fps) <= 1 / fps + 0.05
            and "mp4" in data["format"]["format_name"]
            and len(audios) == int(has_audio)
        )
        if has_audio:
            valid = valid and audios[0]["codec_name"] == "aac" and int(audios[0]["sample_rate"]) == 48000 and audios[0]["channels"] == 2
        if not valid:
            raise ValueError("media properties do not match the submitted job")
    except (KeyError, TypeError, IndexError, ValueError, ZeroDivisionError, json.JSONDecodeError) as error:
        raise RenderError("The produced file failed MP4, codec, dimensions, frame-count, duration or audio validation.") from error
    return {"duration": round(duration, 6), "video_codec": "h264", "audio_codec": "aac" if has_audio else None}


def render(snapshot: dict, job_dir: Path, cancelled: Callable[[], bool]) -> dict:
    """Render a submitted snapshot and return only a verified artifact receipt.

    Paths in the receipt are relative to ``job_dir``. This function never reads
    the manifest's original audio path. Snapshot audio must be ``audio.wav`` and
    match the digest and byte count fixed at submission. Scene durations round
    to the nearest frame (half up), and each scene contains at least one frame.
    """
    deadline = time.monotonic() + RENDER_TIMEOUT_SECONDS
    _check_cancel(cancelled, deadline)
    directory = Path(job_dir).resolve(strict=True)
    if not directory.is_dir():
        raise ValidationError("The render job directory is unavailable.")
    manifest, width, height, fps, scene_frames = _settings(snapshot)
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RenderDependencyError("Rendering requires installed ffmpeg and ffprobe executables.")
    audio_path = _audio(snapshot, directory, cancelled, deadline)
    frames = sum(scene_frames)
    duration = frames / fps
    destination = _safe_child(directory, "artifact.mp4")

    with tempfile.TemporaryDirectory(prefix=".render-", dir=directory) as working_name:
        working = Path(working_name)
        timeline = ["ffconcat version 1.0"]
        for index, (scene, count) in enumerate(zip(manifest["scenes"], scene_frames, strict=True)):
            _check_cancel(cancelled, deadline)
            filename = f"scene-{index:03d}.ppm"
            (working / filename).write_bytes(_card(scene, width, height, index, len(scene_frames), cancelled, deadline))
            timeline.extend([f"file '{filename}'", f"option framerate {fps}", f"duration {count / fps:.12f}"])
        # The final repeated image establishes the end timestamp for the concat
        # demuxer; -frames:v is the exact output bound and excludes this sentinel.
        timeline.append(f"file 'scene-{len(scene_frames) - 1:03d}.ppm'")
        timeline.append(f"option framerate {fps}")
        playlist = working / "frames.ffconcat"
        playlist.write_text("\n".join(timeline) + "\n", encoding="ascii")
        temporary_output = working / "video.mp4"
        command = [
            ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-filter_threads", "1", "-filter_complex_threads", "1", "-threads", "1",
            # Concat's safe=1 forbids its per-file framerate option. This list is
            # generated here, contains only fixed local scene-NNN.ppm names, and
            # is never supplied by the caller. Protocols remain file-only.
            "-protocol_whitelist", "file", "-f", "concat", "-safe", "0",
            "-i", playlist.relative_to(directory).as_posix(),
        ]
        if audio_path:
            command.extend(["-protocol_whitelist", "file", "-f", "wav", "-i", audio_path])
        command.extend([
            "-map", "0:v:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-threads", "2", "-pix_fmt", "yuv420p", "-vf", f"fps={fps}", "-r", str(fps), "-fps_mode", "cfr",
            "-frames:v", str(frames),
        ])
        if audio_path:
            fade = min(0.35, duration / 4)
            audio_filter = (
                f"atrim=duration={duration:.12f},apad=whole_dur={duration:.12f},"
                f"afade=t=in:st=0:d={fade:.12f},afade=t=out:st={duration - fade:.12f}:d={fade:.12f}"
            )
            command.extend(["-map", "1:a:0", "-af", audio_filter, "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"])
        else:
            command.append("-an")
        command.extend([
            "-t", f"{duration:.12f}", "-map_metadata", "-1", "-metadata", "comment=CohortFrame local snapshot render",
            "-movflags", "+faststart", "-fs", str(MAX_OUTPUT_BYTES), "-f", "mp4",
            temporary_output.relative_to(directory).as_posix(),
        ])
        _run(command, directory, cancelled, deadline, output=temporary_output)
        if not temporary_output.is_file() or not 0 < temporary_output.stat().st_size <= MAX_OUTPUT_BYTES:
            raise RenderError("The renderer did not produce an artifact within its file-size allowance.")
        metadata = _probe(ffprobe, temporary_output, directory, width, height, fps, frames, audio_path is not None, cancelled, deadline)
        digest = _digest(temporary_output, cancelled, deadline)
        size = temporary_output.stat().st_size
        _check_cancel(cancelled, deadline)
        # FFmpeg has closed its output. Sync those bytes before publishing the
        # name, then sync the directory as core does for its atomic records.
        # This does not establish a tested power-loss recovery guarantee.
        with temporary_output.open("r+b") as completed:
            completed.flush()
            os.fsync(completed.fileno())
        _check_cancel(cancelled, deadline)
        os.replace(temporary_output, destination)
        if os.name != "nt":
            descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return {
            "path": "artifact.mp4", "sha256": digest, "bytes": size, "format": "mp4",
            "width": width, "height": height, "fps": fps, "frame_count": frames,
            "requested_duration": round(sum(scene["duration"] for scene in manifest["scenes"]), 6),
            "scene_count": len(scene_frames), "renderer": "cohortframe-bitmap-v1",
            "validation": "ffprobe: codec, dimensions, frame count, frame rate, duration and audio",
            **metadata,
        }
