"""Versioned data contracts for CohortFrame's trusted-local prototype.

These checks reject ambiguous or unsupported inputs. They are not an operating
system sandbox and do not make an untrusted Python renderer safe to execute.
"""

from __future__ import annotations

import json
import math
import re
from decimal import Decimal
from typing import Any

MAX_JSON_BYTES = 128 * 1024
MAX_AUDIO_BYTES = 32 * 1024 * 1024
MAX_AUDIO_SECONDS = 120
PROJECT_VERSION = 1
SNAPSHOT_VERSION = 1
JOB_STATES = frozenset(
    {"queued", "running", "succeeded", "failed", "cancel_requested", "cancelled", "interrupted"}
)


class CohortFrameError(Exception):
    """An expected failure with a stable machine-readable category."""

    code = "cohortframe_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


class ValidationError(CohortFrameError):
    code = "validation_error"


class NotFoundError(CohortFrameError):
    code = "not_found"


class ConflictError(CohortFrameError):
    code = "conflict"


class RevisionConflictError(ConflictError):
    code = "revision_conflict"


class IdempotencyConflictError(ConflictError):
    code = "idempotency_conflict"


class StateError(ConflictError):
    code = "state_conflict"


class JobCancelled(CohortFrameError):
    code = "cancelled"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Duplicate JSON property: {key}")
        result[key] = value
    return result


def _no_constant(value: str) -> None:
    raise ValidationError(f"Non-finite JSON number is not permitted: {value}")


def parse_json(text: str | bytes) -> dict[str, Any]:
    """Read one bounded JSON object, rejecting duplicate keys and NaN/Infinity."""
    if not isinstance(text, (str, bytes)):
        raise ValidationError("JSON input must be text or UTF-8 bytes.")
    try:
        size = len(text if isinstance(text, bytes) else text.encode("utf-8"))
        if size > MAX_JSON_BYTES:
            raise ValidationError(f"JSON input exceeds {MAX_JSON_BYTES} bytes.")
        decoded = text.decode("utf-8") if isinstance(text, bytes) else text
        result = json.loads(decoded, object_pairs_hook=_unique_object, parse_constant=_no_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValidationError(f"Invalid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise ValidationError("JSON input must be an object.")
    return result


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValidationError("Value is not finite, serializable JSON.") from exc


def validate_id(value: Any, label: str = "Identifier") -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{32}", value) is None:
        raise ValidationError(f"{label} must be a lowercase 32-character UUID hex identifier.")
    return value


def validate_revision(value: Any) -> int:
    if type(value) is not int or value < 1:
        raise ValidationError("expected_revision must be an integer greater than zero.")
    return value


def scene_frames(duration: float, fps: int) -> int:
    """Nearest frame with ties rounded up, matching the renderer contract."""
    return max(1, math.floor(duration * fps + 0.5))


def _fields(value: dict[str, Any], required: set[str], allowed: set[str], label: str) -> None:
    if any(not isinstance(key, str) for key in value):
        raise ValidationError(f"{label} property names must be strings.")
    missing, unknown = required - value.keys(), value.keys() - allowed
    if missing:
        raise ValidationError(f"{label} is missing: {', '.join(sorted(missing))}.")
    if unknown:
        raise ValidationError(f"{label} has unsupported properties: {', '.join(sorted(unknown))}.")


def _text(value: Any, label: str, maximum: int, *, empty: bool = False, newline: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip()):
        raise ValidationError(f"{label} must be {'0' if empty else '1'}..{maximum} characters.")
    if any(not (32 <= ord(char) <= 126 or (newline and char == "\n")) for char in value):
        raise ValidationError(f"{label} supports printable ASCII{' and newline' if newline else ''} in v0.1.")
    return value


def validate_manifest(data: Any) -> dict[str, Any]:
    """Validate the supported v1 manifest and return an independent normalized copy."""
    if not isinstance(data, dict):
        raise ValidationError("Project manifest must be an object.")
    required = {"version", "name", "width", "height", "fps", "scenes"}
    _fields(data, required, required | {"audio"}, "Manifest")
    if type(data["version"]) is not int or data["version"] != PROJECT_VERSION:
        raise ValidationError("Only project version 1 is supported.")
    name = _text(data["name"], "name", 120)
    for dimension in ("width", "height"):
        value = data[dimension]
        if type(value) is not int or not 16 <= value <= 1920 or value % 2:
            raise ValidationError(f"{dimension} must be an even integer from 16 to 1920.")
    fps = data["fps"]
    if type(fps) is not int or not 1 <= fps <= 30:
        raise ValidationError("fps must be an integer from 1 to 30.")
    source_scenes = data["scenes"]
    if not isinstance(source_scenes, list) or not 1 <= len(source_scenes) <= 12:
        raise ValidationError("scenes must contain 1..12 scenes.")
    scenes, identifiers = [], set()
    total = Decimal("0")
    for index, source in enumerate(source_scenes):
        label = f"scenes[{index}]"
        if not isinstance(source, dict):
            raise ValidationError(f"{label} must be an object.")
        _fields(source, {"id", "title", "duration"}, {"id", "title", "subtitle", "duration", "color"}, label)
        identifier = source["id"]
        if not isinstance(identifier, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", identifier) is None:
            raise ValidationError(f"{label}.id must start with a letter and contain at most 64 ASCII letters, digits, underscores or hyphens.")
        if identifier in identifiers:
            raise ValidationError(f"Scene identifiers must be unique: {identifier}.")
        identifiers.add(identifier)
        duration = source["duration"]
        if type(duration) not in (int, float) or duration <= 0 or duration > 60 or not math.isfinite(duration):
            raise ValidationError(f"{label}.duration must be a finite positive number no greater than 60.")
        if duration * fps < 1 - 1e-9:
            raise ValidationError(f"{label}.duration must be at least one frame at the chosen fps.")
        total += Decimal(str(duration))
        color = source.get("color", "#183153")
        if not isinstance(color, str) or re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None:
            raise ValidationError(f"{label}.color must be #RRGGBB.")
        scenes.append({
            "id": identifier,
            "title": _text(source["title"], f"{label}.title", 160, newline=True),
            "subtitle": _text(source.get("subtitle", ""), f"{label}.subtitle", 280, empty=True, newline=True),
            "duration": float(duration),
            "color": color.upper(),
        })
    if total > Decimal("60") or sum(scene_frames(scene["duration"], fps) for scene in scenes) > 60 * fps:
        raise ValidationError("Total scene duration, including frame rounding, cannot exceed 60 seconds.")
    manifest = {"version": 1, "name": name, "width": data["width"], "height": data["height"], "fps": fps, "scenes": scenes}
    if "audio" in data:
        audio = data["audio"]
        if not isinstance(audio, str) or not audio or len(audio) > 4096 or any(ord(char) < 32 for char in audio):
            raise ValidationError("audio must name a local PCM WAV file.")
        if "://" in audio or audio.startswith(("//", "\\\\")) or not audio.lower().endswith(".wav"):
            raise ValidationError("audio supports local .wav paths only, not URLs or network shares.")
        manifest["audio"] = audio
    if len(canonical_json(manifest).encode("utf-8")) > MAX_JSON_BYTES:
        raise ValidationError("Normalized project manifest is too large.")
    return manifest
