# CohortFrame

**A clear brief. A finished video. A record you can inspect.**

**0.2.0 · Evaluation alpha · Python 3.11+ · Local rendering**

The current source is version 0.2.0. The latest GitHub tagged release is
[v0.1.0](https://github.com/Albertito-AI/cohortframe/releases/tag/v0.1.0), which
predates the visual composer. Use the current source for the commands and
composer described below; the old release wheel retains its original scope.

[**Open the visual composer**](https://cohortframe-studio.travelingbert.chatgpt.site) · [Get started](#quick-start) · [Release checks](docs/RELEASE_0_2.md) · [Known limits](#scope-and-limits)

CohortFrame turns structured title-card briefs into H.264 MP4 videos. Compose scenes in the browser or write JSON directly, preview the exact layouts, then render on your own machine with an optional PCM WAV soundtrack. Each render retains an inspectable job record, input snapshot and output hash.

Use it for short announcements, research explainers, project updates and repeatable agent workflows. There are no connected generation providers, provider keys or paid API calls.

## What is new in 0.2

- **Visual composer:** three starter templates; landscape, portrait and square formats; scene editing, ordering and duplication; sequence playback; undo/redo; browser-local drafts; strict JSON import and export.
- **Preflight:** `validate` checks the schema, frame-rounded duration and exact renderer layout before creating a job.
- **Exact still previews:** `preview` exports PNG scene images without requiring FFmpeg.
- **Offline interface:** `studio` exports the composer as ordinary HTML, CSS and JavaScript. Open `index.html` locally.
- **Project discovery:** `project list` retrieves saved projects and their revisions.
- **Better dependency inspection:** `doctor` checks for both required encoders, rather than reporting readiness merely because executables exist.

CLI interface version 1, project schema version 1 and the SQLite schema remain unchanged. Existing project and job commands retain their semantics. The visual composer produces ordinary v1 briefs.

## Quick start

Download the current source through this repository's **Code → Download ZIP**
control, or clone the repository. Use Python 3.11 or later and a trusted
[FFmpeg installation](https://ffmpeg.org/download.html) with `ffmpeg`, `ffprobe`,
`libx264` and AAC support. FFmpeg is installed separately.

In a POSIX shell, from the extracted project directory:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install .
cohortframe doctor
cohortframe --home ./demo-output demo
```

The demonstration produces a real 12-second MP4 with original procedural audio. It does not call a music or video generation model. Local execution and storage still consume your own resources. This release was verified on Linux with Python 3.12 and FFmpeg 7.1.5; other platforms have not been verified for this release.

To build an installable wheel from the same inspected checkout:

```sh
python -m pip wheel --no-deps . --wheel-dir dist
python -m pip install --no-deps dist/cohortframe-0.2.0-py3-none-any.whl
```

If the command is not on your PATH, use `python -m cohortframe`. The global `--home` option goes **before** the command.

## Compose, preview, render

1. Use the [visual composer](https://cohortframe-studio.travelingbert.chatgpt.site#composer), then download `cohortframe-project.json`. The browser preview is illustrative. No brief or audio is uploaded by the composer.
2. Check the exact layout locally:

```sh
cohortframe validate cohortframe-project.json
cohortframe preview cohortframe-project.json --output frames
```

Open the PNGs in `frames/`. Output directories must be new; existing work is never replaced. Preflight checks scene layouts and timing. Audio is checked when creating the project and copied when submitting a job.

3. Create a project and render it:

```sh
cohortframe project create cohortframe-project.json
cohortframe project list
cohortframe job submit PROJECT_ID --expected-revision 1 --key first-export --run
cohortframe job show JOB_ID
```

Replace the identifiers with those returned by the commands. The MP4 is at `snapshot_dir` plus `result.path` in the returned job. For example, a successful job's artifact is normally `<home>/jobs/<JOB_ID>/artifact.mp4`. A `succeeded` job includes validated media properties and a SHA-256 hash.

For audio, put your approved PCM WAV next to the JSON brief and use its filename in `audio`, or provide an approved absolute path on the rendering machine. An audio path entered in the browser does not upload or validate the file.

For an entirely offline composer:

```sh
cohortframe studio --output my-studio
```

Open `my-studio/index.html`. Browser storage can be unavailable for local files or restricted browsing; downloading the brief is the portable way to retain work. Use **Clear saved draft** on shared devices.

## Agent interface and durable jobs

Commands return one JSON document on stdout, with `ok`, `interface_version: "1"` and either `result` or a structured error. Help and version output are explicit exceptions. Exit codes: `0` success; `2` invalid request or state conflict; `3` local operation error; `4` an executed or inspected job in failed, interrupted or cancelled state. `doctor` itself can succeed while reporting `ready: false`; inspect that field before rendering.

```sh
cohortframe capabilities
cohortframe project update PROJECT_ID revised.json --expected-revision 1
cohortframe job submit PROJECT_ID --expected-revision 2 --key second-export
cohortframe job run JOB_ID
cohortframe job list
cohortframe job cancel JOB_ID
cohortframe job recover
cohortframe job retry JOB_ID --run
```

Stale edits fail. Submitted jobs retain their original inputs. Idempotency keys are project-scoped; a conflicting revision cannot silently reuse the same key. Queued work runs only on explicit invocation. Cancellation requests are observed during execution. Recovery detects abandoned POSIX workers. See [architecture](docs/ARCHITECTURE.md) before automating retries.

## Scope and limits

- 1 to 12 title-card scenes, up to 60 seconds including frame rounding.
- Even dimensions from 16 to 1920 pixels and 1 to 30 fps. Very small dimensions or dense text may fail layout validation.
- Printable ASCII text, displayed using the bundled uppercase bitmap font. No Unicode text shaping or custom fonts.
- Local PCM WAV audio, bounded to 32 MiB and 120 seconds. No footage import, transitions, timeline trimming or AI-generated media.
- Trusted local use. No OS sandbox, hosted renderer, multi-tenant service, billing, marketplace or security certification.
- Windows abandoned-worker recovery is not supported. Linux is the tested release environment.
- Browser responsive styles and interaction logic are included. Desktop/mobile visual browser QA was blocked by the execution environment for this release; it is not claimed as completed.

## Verification and contribution

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
node --test tests/test_studio.cjs
```

FFmpeg integration tests run when media tools are installed. [Release evidence](docs/RELEASE_0_2.md) records observed results, installation checks, output properties and verification gaps. Historical v0.1 evidence is retained and labelled by version.

CohortFrame is an Atlas Agent School community project under Albert Tan Sin Hon's stewardship. Future qualified cohort participation is planned, not a claim of current student operation. [Succession](docs/SUCCESSION.md) describes a separate qualification and handover process.

For adaptations or evaluation feedback, use [Albert Tan's website](https://www.alberttansinhon.com/). Public source availability is not an open-source licence. See [distribution terms and provenance](NOTICE.md), [security boundaries](docs/SECURITY.md) and [source provenance](docs/PROVENANCE.md).
