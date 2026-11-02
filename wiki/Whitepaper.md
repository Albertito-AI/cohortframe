<!-- atlas-whitepaper:managed:v1 -->

# CohortFrame: creative work that survives its creators

## The thesis

A creative tool should produce an artifact people can use and a process another person can understand. CohortFrame joins these objectives through a structured brief, deterministic local rendering and a retained job record. Its larger ambition is continuity: successive qualified contributors, including future software-agent cohorts, should be able to improve the product without relying on an outgoing author's private memory.

The present product is deliberately concrete. It turns short title-card briefs into local MP4 videos, with exact still previews and optional WAV audio. The ideal future is broader, but dependable creation and handover matter more than the number of media-generation integrations.

Prepared for Albert Tan Sin Hon with AI assistance, 2 November 2026. This paper explains the inspected evaluation alpha and proposes future directions. It does not claim that student agents currently operate the project, that a hosted renderer exists or that the product has an open-source licence.

## First principles: separate intention, execution and evidence

A brief describes intended content. A project revision records an accepted version of that intention. A job executes frozen inputs. An artifact is the resulting media. A success record should identify what was actually produced and checked. Treating these objects as interchangeable invites stale edits, duplicate work and misleading completion claims.

The current architecture makes these distinctions operational. Project edits require an expected revision, so a stale writer cannot silently replace newer work. A job retains its input snapshot. Project-scoped idempotency keys distinguish an identical retry from a conflicting request. An output hash identifies produced bytes; it is not proof that a video communicates well or that its soundtrack is lawfully usable.

The second principle is inspectability before expansion. A browser preview is illustrative; exact PNG previews come from the local renderer's layout. A `doctor` command may complete successfully while reporting that the environment is not ready. Those distinctions should remain visible because they help a user make the next correct decision.

## Fundamental logic of the current system

The browser composer exports ordinary versioned JSON. It offers templates, scene editing, ordering, playback and local drafts without uploading briefs or audio. The Python toolkit validates the contract, checks exact layout, stores projects and jobs in SQLite and invokes local rendering tools with bounded parameters.

Jobs can be queued, running, succeeded, failed, cancelled or interrupted. Cancellation is a request until execution actually stops. Recovery must distinguish an abandoned worker from a live one. Retrying a failed job should use the stored inputs, not whatever the project has become since submission. These details become particularly important if future adapters incur costs or run remotely.

Version 0.2 supports up to twelve title-card scenes and sixty seconds, with printable ASCII through a bundled bitmap font. It does not generate footage or music. Windows abandoned-worker recovery and broad browser visual acceptance remain outside the recorded release verification. Honesty about these limits makes a useful evaluation possible.

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

## How to measure the ambition

For creators, measure time to a usable artifact, rejected layouts, recovery success, accessibility obstacles and the effort needed to revise an earlier project. Inspect actual media rather than relying on an exit code. For maintainers, give a fresh verifier the handover bundle without the original author's private explanations and ask them to reproduce, diagnose, change and recover.

Count regressions, support burden and resource use alongside new features. If a more capable renderer destroys portability or makes ordinary revisions harder, it may be the wrong improvement. If succession works only while the outgoing agent supplies hidden context, the handover has not succeeded.

The best case is a durable creative commons of methods and compatible artifacts, within the owner's chosen distribution terms: useful work keeps improving as contributors change, and users retain understandable control over what they create.

## Inspected foundation

Baseline: [`ef179a2faf2658c30b763509c7cf2e9fafcb1dad`](https://github.com/Albertito-AI/cohortframe/tree/ef179a2faf2658c30b763509c7cf2e9fafcb1dad). Sources: [README](https://github.com/Albertito-AI/cohortframe/blob/ef179a2faf2658c30b763509c7cf2e9fafcb1dad/README.md), [architecture](https://github.com/Albertito-AI/cohortframe/blob/ef179a2faf2658c30b763509c7cf2e9fafcb1dad/docs/ARCHITECTURE.md), [security](https://github.com/Albertito-AI/cohortframe/blob/ef179a2faf2658c30b763509c7cf2e9fafcb1dad/docs/SECURITY.md) and [succession contract](https://github.com/Albertito-AI/cohortframe/blob/ef179a2faf2658c30b763509c7cf2e9fafcb1dad/docs/SUCCESSION.md). Public source availability does not grant an open-source licence. This paper changes neither distribution terms nor admission and release authority.
