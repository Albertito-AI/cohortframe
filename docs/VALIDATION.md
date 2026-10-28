# CohortFrame 0.1.0 validation record

**Observed on 28 October 2026 (Asia/Singapore). Status: working local alpha.**

This is the original incubation-build record, retained with its original wheel and artifact hashes. The dedicated repository's release is verified separately in [standalone launch validation](LAUNCH_VALIDATION.md); use that record for the released wheel's digest and fresh-install results.

The release was built as a Python wheel, installed in a separate virtual environment, and exercised with `PYTHONPATH` removed and the working directory outside the source tree. Imported application code came from the installed wheel. The same installed package produced both demonstration videos.

## Environment and results

| Item | Observed result |
| --- | --- |
| Python | 3.12.14 |
| Platform | Linux x86_64, kernel 6.18.55, glibc 2.39 |
| Media tools | FFmpeg and ffprobe 6.1.1; libx264 video and AAC audio |
| Automated suite | 37 passed, 0 failed, 0 skipped |
| Landscape demonstration | 1280 x 720, 24 fps, 288 frames, 12 seconds, H.264/AAC MP4 |
| Portrait demonstration | 720 x 1280, 24 fps, 288 frames, 12 seconds, H.264/AAC MP4 |
| Duplicate submission after success | Same job identifier, one attempt, unchanged output file for each demonstration |
| Visual inspection | Selected landscape and portrait frames inspected for legibility, layout and clipping |

Machine-readable environment details, wheel digest and output receipts are in [validation.json](validation.json). A digest records bytes; it is not a publisher signature. The original procedural chord fixture is the demonstration soundtrack. No music-generation service was involved.

## Behaviour covered

The suite contains six CLI checks, 21 schema/core checks and ten renderer checks. It exercises structured errors, persistence across CLI processes, duplicate JSON keys, input bounds, huge integer durations, frame quantisation, optimistic revisions, idempotent submissions and conflicts, immutable input copying, tamper detection, single-worker claims, cancellation and abandoned-worker recovery.

Renderer checks invoke real FFmpeg and ffprobe for short audio and silent videos, portrait output, actual frame counts and duration, audio fades, and text containing punctuation that must remain raster data. Other checks force missing dependencies, process failure, timeouts, changed audio and cancellation. Core tests use stub artifacts where the subject is job coordination; those stubs are not evidence of valid media.

Tests and targeted review identified and corrected frame-timing mismatch, unsafe assumptions about enormous numeric inputs, non-POSIX process liveness, unbounded reads from special files, corrupt database error handling, and unintended retry paths. Completed artifacts are synchronised before success is recorded, with the job directory synchronised on supported POSIX systems. Power-loss behaviour has not been simulated.

## Reproduce

Install Python and a trusted FFmpeg/ffprobe build, then follow the README installation steps. In the project directory, using the installed package:

```sh
python -m unittest discover -s tests -v
python -m cohortframe capabilities
python -m cohortframe doctor
python -m cohortframe --home ./check-landscape demo
python -m cohortframe --home ./check-portrait demo --width 720 --height 1280
```

Inspect the returned artifact and receipt. Submit a demonstration's same project/revision/idempotency key again with `--run`; the response should identify the successful existing job without another attempt. Encoded byte hashes may differ with different FFmpeg builds, so compare the media contract as well as locally recorded hashes.

## Limits of this evidence

Only the environment above has been exercised locally. The declared Python minimum is not evidence that every supported interpreter or operating system has been tested. Automatic abandoned-worker recovery is not implemented for Windows. There is no operating-system sandbox, multi-tenant authorization service, native dependency audit, fuzzing campaign or security certification.

This record establishes local software behaviour. It does not establish commercial demand, revenue, live provider compatibility, school enrolment, learner competence or a completed transfer of maintenance. The separate market and succession documents define the next evidence to collect.
