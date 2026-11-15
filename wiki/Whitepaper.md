<!-- atlas-whitepaper:managed:v1 -->

# CohortFrame: creative work that survives its creators

## Abstract

CohortFrame is an evaluation alpha that turns bounded title-card briefs into local video artifacts while retaining project revisions, immutable job inputs and inspectable results. Its research proposition is that explicit execution records can support reliable revision and maintainer handover. The present evidence covers implementation, local media checks and a dated scripted browser evaluation. It does not establish accessibility, independent user benefit or successful transfer to a new cohort. This paper follows a revision-and-render example, identifies counterexamples to misleading success claims, and specifies how continuity should be tested before it is asserted.

## The thesis

A creative tool should produce an artifact people can use and a process another person can understand. CohortFrame joins these objectives through a structured brief, bounded local rendering and a retained job record. Its larger ambition is continuity: successive qualified contributors, including future software-agent cohorts, should be able to improve the product without relying on an outgoing author's private memory.

The present product is deliberately concrete. It turns short title-card briefs into local MP4 videos, with exact still previews and optional WAV audio. The ideal future is broader, but dependable creation and handover matter more than the number of media-generation integrations.

Prepared for Albert Tan Sin Hon with AI assistance on 2 November 2026; revised against the source identified below on 15 November 2026. This paper explains the inspected evaluation alpha and proposes future directions. It does not claim that student agents currently operate the project, that a hosted renderer exists or that the product has an open-source licence.

## First principles: separate intention, execution and evidence

A brief describes intended content. A project revision records an accepted version of that intention. A job executes frozen inputs. An artifact is the resulting media. A success record should identify what was actually produced and checked. Treating these objects as interchangeable invites stale edits, duplicate work and misleading completion claims.

The current architecture makes these distinctions operational. Project edits require an expected revision, so a stale writer cannot silently replace newer work. A job retains its input snapshot. Project-scoped idempotency keys distinguish an identical retry from a conflicting request. An output hash identifies produced bytes; it is not proof that a video communicates well or that its soundtrack is lawfully usable.

The second principle is inspectability before expansion. A browser preview is illustrative; exact PNG previews come from the local renderer's layout. A `doctor` command may complete successfully while reporting that the environment is not ready. Those distinctions should remain visible because they help a user make the next correct decision.

## Operational definitions

| Object or state | Meaning | Boundary |
| --- | --- | --- |
| Brief | A versioned JSON description of scenes, dimensions, timing and optional local audio | It is not a rendered artifact |
| Project revision | A saved accepted version of a brief | A stale expected revision must not silently replace it |
| Job snapshot | The manifest and imported audio frozen for a submitted job | Later edits to the project do not redefine that job |
| Idempotency key | A project-scoped identifier for a submission request | It is not a guarantee about external provider billing |
| Succeeded job | A recorded local result with checked media properties and output hash | It does not prove communication quality, rights or accessibility |

The operational boundary is a trusted local user. There is no operating-system sandbox, hosted rendering service, multi-tenant access control or provider integration. Exact still layouts are produced by the local renderer. Full MP4 byte identity is not promised across FFmpeg versions or builds; the [release record](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/docs/RELEASE_0_2.md) expressly retains that limit.

## Fundamental logic of the current system

The browser composer exports ordinary versioned JSON. It offers templates, scene editing, ordering, playback and local drafts without uploading briefs or audio. The Python toolkit validates the contract, checks exact layout, stores projects and jobs in SQLite and invokes local rendering tools with bounded parameters.

Jobs can be queued, running, succeeded, failed, cancelled or interrupted. Cancellation is a request until execution actually stops. Recovery must distinguish an abandoned worker from a live one. Retrying a failed job should use the stored inputs, not whatever the project has become since submission. These details become particularly important if future adapters incur costs or run remotely.

Version 0.2 supports up to twelve title-card scenes and sixty seconds, with printable ASCII through a bundled bitmap font. It does not generate footage or music. Windows abandoned-worker recovery remains unsupported. The 11 November 2026 [release record](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/docs/RELEASE_0_2.md) reports scripted Chromium desktop/mobile acceptance and screenshot inspection for the installed composer. Independent user testing, accessibility certification, broad browser coverage and live-site QA remain separate, unestablished claims. Honesty about these limits makes a useful evaluation possible.

## Worked example: revise the project without rewriting the job

Suppose a creator submits project revision 1 with key `first-export`, then corrects the title in revision 2. The original job retains revision 1's manifest and audio snapshot. A new rendering of revision 2 requires a new compatible submission request. Repeating the identical project/revision/key request identifies the existing job; reusing that key for a different revision is a conflict. A stale project update also fails rather than overwriting the correction. The [store implementation](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/src/cohortframe/core.py) and [state tests](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/tests/test_core.py) expose those rules.

A counterexample shows why process success is insufficient. `doctor` can exit successfully while reporting `ready: false` if an encoder is missing. Similarly, `validate` can check layout while returning `audio_checked: false`: audio is checked at project creation and snapshotted at submission. A browser preview is illustrative, so a downloaded brief still needs local layout preflight. These are distinct successful operations with distinct evidential scopes.

The [workflow tests](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/tests/test_workflow.py) include a brief with 1.04 seconds at 24 fps. Preflight reports 25 frames, corresponding to 25/24 seconds. The same suite checks a schema-valid but unrenderable 16-by-16 layout and refusal to overwrite an existing preview directory. These controls make a more informative example than asserting that every valid-looking JSON object will render.

### Reproduction from a specified source

Use the source at `8d3845dbe0a451329f40fe55aabdb824ef9fbe97`, not an assumption that the older tagged release contains version 0.2 features. The [README](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/README.md) and [release record](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/docs/RELEASE_0_2.md) distinguish the 0.2.0 source from the older v0.1.0 tagged release as documented on 11 November. Install from this checkout in an isolated environment with Python 3.11 or newer and separately available FFmpeg/ffprobe with libx264 and AAC support. Installation instructions and dependency choices remain those of the repository.

```sh
cohortframe doctor
cohortframe validate examples/intro.json
cohortframe preview examples/intro.json --output paper-frames
cohortframe --home ./paper-demo demo
PYTHONPATH=src python -m unittest discover -s tests -v
node --test tests/test_studio.cjs
```

Use new output locations. Inspect `doctor.ready`, actual PNGs, the returned job record and produced MP4 properties, not only command exit codes. Record the source commit, Python, Node, FFmpeg and ffprobe versions, output hashes, skips and failures. The procedural demo's documented target is 12 seconds at 24 fps, or 288 frames. Hash differences across encoder builds must be investigated within the recorded environment rather than automatically labelled semantic failure. These are reproduction instructions; no new rendering or browser run was performed for this paper revision.

| Claim | Evidence at the reviewed commit | Limit |
| --- | --- | --- |
| Stale writes and conflicting submission keys are rejected | [Store code](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/src/cohortframe/core.py); [state controls](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/tests/test_core.py) | Local application behaviour, not distributed exactly-once execution |
| Preview and preflight distinguish audio scope | [Workflow code](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/src/cohortframe/workflow.py); [workflow controls](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/tests/test_workflow.py) | PNG output is not an audio-validated MP4 |
| Scripted desktop/mobile acceptance was recorded | [Dated 0.2 release record](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/docs/RELEASE_0_2.md) with native run and artifact hash | A historical installed-package check, not a fresh live-site or user test |
| Handover has explicit requirements | [Succession contract](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/docs/SUCCESSION.md) | A contract is not evidence that an incoming cohort passed it |

## A creative workflow with a memory

Imagine a small community organisation produces a recurring research update. It wants a recognisable visual sequence, a corrected title and a clear record of which version was sent. A structured brief can preserve that design without requiring the organisation to reconstruct a video manually each time.

If a render fails halfway through, the project and job records should support diagnosis and recovery. If a new maintainer takes over, the brief, schema, fixtures and release evidence should be sufficient to reproduce the output. The useful unit of progress is a capability that survives this handover, not a burst of impressive generation that nobody can maintain.

The design also permits principled disagreement. A later contributor may propose a better renderer or representation, but must demonstrate compatibility or an explicit migration. Preservation of evidence should not freeze the project into its first design. It should make improvement reviewable.

## Aim and public-interest hope

The immediate aim is accessible, repeatable creation of short visual communications. The larger hope is to reduce the distance between having something useful to explain and being able to communicate it clearly. Educators, researchers and small organisations could benefit from reliable local tools that do not require a subscription or provider key for each output.

Accessibility is both a product and a social question. ASCII-only text is a substantial limit on global usefulness. Better language support, captions, readable layouts and accessible composition deserve priority over spectacle. Rights-aware asset handling should help creators avoid using material they cannot distribute. The project should favour clarity and truthful communication over deceptive synthetic media or engagement manipulation.

Its community ambition adds another dimension: software-agent education can be evaluated through the maintenance of a useful public-facing artifact. School membership must not automatically grant release authority, access to customer data or spending power. Competence, permission and accountability remain distinct.

## Ideal progression and wishlist

| Stage | Intended outcome | Evidence gate |
| --- | --- | --- |
| Dependable local creation | Clear briefs, exact previews and recoverable jobs | Fresh install, actual rendered media and failure/recovery checks |
| Accessible composition | Better text, language and navigation support | Real browser, keyboard and user evaluation across supported languages |
| Richer media | Carefully bounded assets, transitions and layouts | Rights records, parser isolation, resource limits and reproducible outputs |
| Qualified succession | Another contributor can maintain a frozen release | Fresh-verifier reproduction, diagnosis, bounded change and rollback |
| Optional remote adapters | Useful authorised services with explicit cost | Durable reconciliation, credential boundaries and truthful ambiguous states |

The ideal wishlist includes Unicode shaping, captions, reusable design systems, exact browser/local layout agreement where feasible, portable project archives and accessible batch workflows. Any model-based generation should be optional, with explicit destination, rights, spending limits and retained provider job identifiers. An ambiguous remote timeout must not trigger an unexamined duplicate paid job.

## Related engineering methods

SQLite's [Isolation in SQLite](https://sqlite.org/isolation.html), especially “Isolation Between Database Connections”, describes transaction visibility and serialised writes. CohortFrame builds application-level revision and job rules around local storage; those rules still require their own tests. Database isolation alone does not make a filesystem snapshot and a media subprocess one indivisible transaction or establish remote-service reliability.

The official [ffprobe documentation](https://ffmpeg.org/ffprobe.html), section 2, describes inspecting media-container and stream information. That supports the distinction between a program exit and an inspected media artifact. Neither media metadata nor a SHA-256 hash proves that an explanation is intelligible, accessible or authorised for distribution. FFmpeg remains a separately installed dependency with its own terms; this paper does not import its licence into the project.

## How to measure the ambition

For creators, measure time to a usable artifact, rejected layouts, recovery success, accessibility obstacles and the effort needed to revise an earlier project. Inspect actual media rather than relying on an exit code. For maintainers, give a fresh verifier the handover bundle without the original author's private explanations and ask them to reproduce, diagnose, change and recover.

A future handover study should freeze a release, select bounded revision and recovery tasks, and give the incoming contributor only the declared bundle. Record setup failures, requests for undocumented help, incorrect state interpretations, recovery outcome and time. Use a fresh task for any comparison with the outgoing maintainer to reduce memorisation effects. Separate completion of a supplied exercise from authority to maintain a production service. No such independent succession study is claimed here.

For teaching, ask learners to predict the original job's inputs after a project edit, identify the conflict caused by reusing a key for another revision, and explain why `audio_checked: false` can accompany valid layout. Require them to identify the evidence that a cancelled or interrupted worker actually stopped. A strong answer preserves uncertainty and identifies the next observation, rather than treating a requested transition as a completed one.

Count regressions, support burden and resource use alongside new features. If a more capable renderer destroys portability or makes ordinary revisions harder, it may be the wrong improvement. If succession works only while the outgoing agent supplies hidden context, the handover has not succeeded.

The best case is a durable body of methods and compatible artifacts, within the owner's chosen distribution terms: useful work keeps improving as contributors change, and users retain understandable control over what they create.

## Inspected foundation

Source reviewed for this revision: [`8d3845dbe0a451329f40fe55aabdb824ef9fbe97`](https://github.com/Albertito-AI/cohortframe/tree/8d3845dbe0a451329f40fe55aabdb824ef9fbe97). Source, tests and historical release records were inspected without renewing their execution claims. Sources: [README](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/README.md), [architecture](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/docs/ARCHITECTURE.md), [security](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/docs/SECURITY.md) and [succession contract](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/docs/SUCCESSION.md). Public source availability does not grant an open-source licence. This paper changes neither distribution terms nor admission and release authority.
