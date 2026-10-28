# README video demonstration

Recorded on **28 October 2026** from the actual private `v0.1.0` release. The README animation is a reduced-frame-rate preview of the landscape MP4, not a simulated interface or a generated product mock-up.

## Source and result

- Product commit: `5d60e220a6add97ba290197ffbbd3bbdf519ab41`.
- Source video: [`cohortframe-0.1.0-demo-landscape.mp4`](https://github.com/Albertito-AI/cohortframe/releases/download/v0.1.0/cohortframe-0.1.0-demo-landscape.mp4).
- Source SHA-256: `c1f3f3b1213be9df91ec6442e08f2405228f3674c2029eb02919a4307b5f9ba5`.
- Original output: 1280 × 720, 12 seconds, 24 fps, 288 H.264 frames and AAC stereo audio at 48 kHz.
- README preview: 720 × 405, 48 frames at 4 fps, a silent GIF loop.
- The portrait release example is 720 × 1280 with the same duration, frame rate and audio format.

The three title-card scenes and original procedural audio exercise the existing local composition and artifact-validation workflow. They do not demonstrate a generative music model, a graphical editor or a hosted service. See [launch validation](LAUNCH_VALIDATION.md) for the installed-wheel, job-reuse and artifact checks.

## Reproduce the output

Follow the repository's [installation guide](../README.md#quick-start), including FFmpeg, then run:

```sh
cohortframe --home ./readme-demo demo
```

The returned JSON names the project, completed job and output artifact. Use a fresh `--home` directory to make a separate fixture run. No provider account or API key is required.

## Reproduce the preview

Download the source MP4 from the private release to a directory in which you have permission to write, then run:

```sh
ffmpeg -i cohortframe-0.1.0-demo-landscape.mp4 \
  -vf 'fps=4,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3' \
  -loop 0 cohortframe-demo.gif
```

The documentation update does not change the `v0.1.0` source tag, wheel, MP4 assets or runtime. Repository access is still required to view this private project and its release assets.
