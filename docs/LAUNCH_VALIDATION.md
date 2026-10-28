# Standalone release validation: CohortFrame 0.1.0

**Observed:** 28 October 2026, Asia/Singapore. **Release scope:** private local alpha.

This record verifies the extracted product and the wheel supplied by the dedicated
CohortFrame release. [launch-validation.json](launch-validation.json) contains
the environment, runtime identities, media properties and artifact digests.
The earlier [incubation validation](VALIDATION.md) remains a separate historical
record with its original hashes.

## Source and package

All 24 product files were extracted from Atlas Agent School PR #15 at
`ea4631b9d2a8eaff19e5557b9c65449f06ddbd95`. Each Git blob identifier and byte size
matched. Only product files were copied. The independent extraction review found
no school runtime dependency or private learner record in the package.

The extracted baseline was built offline into a wheel, installed into a fresh
virtual environment and tested from a copied test directory outside the source
tree, with `PYTHONPATH` removed from the launched environment. All **37 tests
passed**, with zero errors, failures or skips.

Launch documentation changed the embedded README metadata. The final wheel was
rebuilt and installed into another fresh environment; capability discovery and
dependency checks passed. All seven runtime modules are byte-identical across
the upstream source, tested baseline wheel/install and final wheel/install.
The full suite was not repeated for the documentation-only metadata change.

Final wheel: `cohortframe-0.1.0-py3-none-any.whl`, **28,674 bytes**.

```text
SHA-256 8ad5471ce14708a84c3b1c623b722671b3903bbb85e9b4e45d9d859bb0127278
```

The final wheel contains the updated README. The release's `SHA256SUMS` covers
that wheel and both demonstration videos. Checksums identify bytes; they are not
publisher signatures.

## Observed media and job behaviour

The tested environment was Python **3.12.14**, Linux x86_64 and
FFmpeg/ffprobe **6.1.1**. The installed baseline runtime produced both demos:

| Property | Landscape | Portrait |
| --- | --- | --- |
| Dimensions | 1280 x 720 | 720 x 1280 |
| Video | H.264, 24 fps | H.264, 24 fps |
| Frames | 288 | 288 |
| Duration | 12.000 seconds | 12.000 seconds |
| Audio | AAC, stereo, 48 kHz | AAC, stereo, 48 kHz |
| Successful-job repeat | Same single attempt and artifact | Same single attempt and artifact |

Independent ffprobe reads confirmed these properties. Repeating each completed
submission preserved the artifact hash and modification time. Selected frames
at 1, 5 and 9 seconds were inspected for legibility and clipping; titles and
subtitles fitted both layouts. The soundtrack is the included original
procedural fixture. No generation provider was called.

## Reproduce and interpret

Install the release wheel with a trusted FFmpeg/ffprobe build, then run
`cohortframe capabilities`, `cohortframe doctor` and
`cohortframe --home ./demo-output demo`. The source archive contains the tests
and the custom-brief example. The [README](../README.md) gives installation and
job commands; [SECURITY.md](SECURITY.md) describes the current local boundary.

GitHub checks attached to the release commit establish their own hosted result.
This document records the local verification above. Only Linux was exercised;
other platforms and interpreters remain unverified. This release does not
establish a hosted service, OS sandbox, security certification, customer demand,
school admission or student maintenance transfer.
