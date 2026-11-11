# CohortFrame 0.2.0 release checks

## Source and tagged-release distinction, 11 November 2026

The current source identifies itself as 0.2.0, while the most recent GitHub tag
and release is v0.1.0. The historical checks below describe the 0.2.0 source and
locally prepared package; they do not establish a tagged 0.2.0 GitHub release.
The README now installs from the current repository and gives a local wheel-build
command, avoiding an assumption that the older release includes the composer.

The 11 November recheck ran all 45 Python and seven JavaScript contract tests
successfully on Linux with Python 3.12.14 and Node 24.22.1, including real FFmpeg
rendering, cancellation and recovery. Local Chromium failed before page load
because the environment prohibited a required socket operation. It was not
counted as a visual pass. The existing CI now exports the installed composer and
runs `tests/browser_acceptance.cjs` against it with pinned Playwright 1.64.1.
That test exercises desktop/mobile editing, import/export, draft persistence,
playback and layout bounds, and retains screenshots and machine-readable evidence.
No release is created by this workflow.

### Observed browser acceptance

[Run 42971883717](https://github.com/Albertito-AI/cohortframe/actions/runs/42971883717)
passed for pull-request head `83cda056c290a1a2d3216198daa54c620ac2def9`.
The checked-out integration revision recorded by the test was
`0f763b514894d04a733578c1c30bd488fd5ad9bb`. Chromium 156.0.8078.4
completed both 1440 × 1000 desktop and 390 × 844 mobile acceptance. Both
browser-downloaded briefs also passed the installed Python validator. The
artifact ZIP SHA-256 was
`34f02eaf50659819e4ba123b52c89aae28693d381e7216d16aa7ff03d1d5a440`;
desktop and mobile screenshots were downloaded, hash checked and visually
inspected. The final mobile scene strip stays within the workspace, and its
timeline controls no longer overlap the preview note.

The initial [diagnostic run 42971082631](https://github.com/Albertito-AI/cohortframe/actions/runs/42971082631)
failed because a 616 px scene panel expanded a 390 px page. Its retained layout
JSON and screenshot established the defect before the CSS correction. A later
screenshot review found the timeline overlap and added a separate regression
assertion. This is real scripted browser evidence for the installed package,
not independent user testing, accessibility certification or live-site QA.

## Original 0.2.0 preparation record

Date: 1 November 2026. Scope: local evaluation alpha and browser-based brief composer.

## Compatibility

The CLI envelope remains interface version 1. Project manifests and job snapshots remain version 1. There is no database migration. All 37 prior regression tests were retained. New commands are additive: `validate`, `preview`, `studio`, and `project list`. `doctor.ready` now requires detected libx264 and AAC encoders; callers that formerly relied on a false-positive readiness result will receive `false`.

The composer is a static client. It has no rendering server, upload endpoint, authentication flow or paid-provider integration. Its preview is illustrative; the Python renderer creates exact still previews and final video.

## Reproducible checks

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
node --test tests/test_studio.cjs
python -m pip wheel --no-deps --no-build-isolation . -w dist
cohortframe doctor
cohortframe validate examples/intro.json
cohortframe preview examples/intro.json --output frames
cohortframe --home demo-output demo
```

Observed: 45 Python tests pass, including real FFmpeg tests, state recovery, immutable snapshots, cancellation, revision conflicts, malformed inputs and the new workflow operations. Seven JavaScript contract tests pass, covering templates, import ambiguity, unsupported values, rounding limits, reordering, defaults and bounded input size. The test run contains no skipped Python tests in the release environment.

Exact 1280 × 720 PNG previews were generated and visually inspected. A 12-second 1280 × 720 MP4 was rendered: H.264, 24 fps, 288 frames, AAC audio, 254,512 bytes. SHA-256: `f7a5af32a6ef0f80b96bc78391745a65f841ebe8ba9c653fdcc7c27226ff960a`. This is the procedural `demo` fixture, not a customer result or generated footage.

Environment: Linux, Python 3.12.14, FFmpeg/ffprobe 7.1.5, Node 24.22.1. Other operating systems and dependency builds are not verified here. Media hashes can differ across encoder versions.

## Verification boundaries

The available browser runtime failed to start with an environment filesystem error before loading a page. Desktop/mobile visual QA and real browser end-to-end interaction testing are therefore unverified. Responsive CSS, semantic controls, focus styles, labels, reduced-motion handling and a text alternative for the canvas were implemented; this is not an accessibility certification.

No independent incoming-cohort succession exercise was performed. Existing succession requirements remain in force before maintenance responsibility is transferred. No customer pilot, conversion measurement, security audit or paid market validation is claimed.

Publication status must be read from the live deployment and repository visibility, separately from these functional checks. A public product page does not itself make the GitHub repository public.

## Fresh installation and portrait output

The built wheel was installed in a new virtual environment using `pip install --no-index --no-deps`. The installed `studio` command exported all five offline interface assets. The installed `demo --width 720 --height 1280` produced a second successful 12-second, 288-frame H.264/AAC MP4 (254,149 bytes), SHA-256 `f8df03488673492d3248573f1a83aa10e4819fd4644946900f7bf3d97de9b638`. All three browser starter templates were exported to examples and passed Python schema, frame-duration and exact-layout preflight.
