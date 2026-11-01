"""Read-only preflight and explicit, non-overwriting local interface exports."""
from __future__ import annotations
import binascii
from importlib.resources import files
import json
from pathlib import Path
import shutil
import struct
import zlib
import time

from .models import ValidationError, validate_manifest, scene_frames
from .render import _card


def _cards(manifest):
    deadline = time.monotonic() + 180
    for index, scene in enumerate(manifest['scenes']):
        yield _card(scene, manifest['width'], manifest['height'], index, len(manifest['scenes']), lambda: False, deadline)


def preflight(source):
    manifest = validate_manifest(source)
    for _ in _cards(manifest):
        pass
    frames = sum(scene_frames(s['duration'], manifest['fps']) for s in manifest['scenes'])
    return {'valid': True, 'manifest': manifest, 'frames': frames,
            'duration_seconds': frames / manifest['fps'], 'layout_checked': True,
            'audio_checked': False, 'warnings': ['Audio is checked at project creation and snapshotted at job submission.'] if 'audio' in manifest else []}


def _png(ppm, width, height):
    pixels = ppm.split(b'\n', 3)[3]
    def chunk(kind, content):
        return struct.pack('!I', len(content)) + kind + content + struct.pack('!I', binascii.crc32(kind + content) & 0xffffffff)
    scanlines = b''.join(b'\0' + pixels[i:i + width*3] for i in range(0, len(pixels), width*3))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(scanlines)) + chunk(b'IEND', b''))


def preview(source, output: Path):
    manifest = validate_manifest(source)
    # Validate all layouts before creating an output directory.
    preflight(manifest)
    if output.exists() or output.is_symlink():
        raise ValidationError('Preview output must be a new directory.')
    output.mkdir(parents=True)
    try:
        images = []
        for index, ppm in enumerate(_cards(manifest)):
            path = output / f'scene-{index+1:02d}.png'
            path.write_bytes(_png(ppm, manifest['width'], manifest['height']))
            images.append(str(path.resolve()))
        (output / 'project.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    except Exception:
        shutil.rmtree(output)
        raise
    return {'directory': str(output.resolve()), 'images': images, 'note': 'Exact still layouts; no audio or MP4 produced.'}


def export_studio(output: Path):
    if output.exists() or output.is_symlink():
        raise ValidationError('Studio output must be a new directory.')
    output.mkdir(parents=True)
    try:
        for asset in files('cohortframe').joinpath('studio').iterdir():
            if asset.name.endswith(('.html', '.css', '.js', '.svg')):
                (output / asset.name).write_bytes(asset.read_bytes())
    except Exception:
        shutil.rmtree(output)
        raise
    return {'index': str((output / 'index.html').resolve()),
            'note': 'Open index.html in your browser. Export a JSON brief, then render with the CLI. No HTTP listener.'}
