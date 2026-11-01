# Historical v0.1 market plan

This document records the original private-alpha plan. Current implemented capabilities and release limits are in [README](../README.md) and [0.2 release checks](RELEASE_0_2.md). No pilot outcomes are implied by the public evaluation launch.

# CohortFrame: market readiness

## Position and scope

**CohortFrame is a local video-rendering tool for authorised agent workflows.** Agents operate the CLI; the people or organisations authorising them decide what may run and pay any associated costs.

Suggested alpha copy, usable after the corresponding acceptance checks pass:

> Turn structured title-card projects into MP4s, with job records you can inspect. Run locally, supply your own WAV soundtrack, and keep project revisions and render snapshots.

The v0.1 scope is Python 3.11+, the standard library, an external FFmpeg executable, JSON CLI responses, strict title-card scenes, optional local WAV audio, project revisions, and SQLite-backed jobs with idempotency, snapshots, cancellation, and recovery. Each capability must have implementation evidence before it becomes a release claim.

No generation-provider account is required for the local rendering path. Local execution, storage, and any separately chosen agent service still have costs. Users must have permission to use supplied text and audio; accepting a file does not establish commercial rights.

Cloud music generation, marketplace, billing, desktop GUI, hosted operation, and security certification are outside this release. This is original implementation work inspired by the problem space, not an OpenFilm fork. Future Atlas student contributions are planned; no operational student workforce is claimed.

## First customer hypothesis

Start with developers and small teams already operating agents who need repeatable announcement, status, or explainer clips from approved text and audio. Test whether structured projects and inspectable jobs reduce their effort enough to justify continued use. Do not position title cards as a complete filmmaking suite.

## Evidence before invitations

1. **Functional version:** produce and inspect a real MP4 from the documented example. Save its input, output, job record, tested environment, and observed limitations.
2. **Tested alpha:** verify revisions, immutable render inputs, idempotency conflicts, invalid inputs, cancellation, and interrupted-job recovery. Inspect output duration, dimensions, text legibility, and audio behaviour. Publish only the platforms and dependency versions actually tested.
3. **Pilot package:** provide installation instructions, one working project, the CLI contract, known limitations, recovery instructions, and a feedback form. Identify the operator responsible for support. The canonical application now has its own [private product repository](https://github.com/Albertito-AI/cohortframe). Public distribution and pilot invitations remain separate decisions from this private alpha release.

Security reviews must state their actual scope and date. Neither passing tests nor local execution establishes that arbitrary inputs or dependencies are safe.

## First market experiment

**Planned, not executed:** invite five consenting agent operators to a private alpha after readiness checks pass and outreach is authorised. Have each render the supplied example, create one useful project of their own, and complete a controlled recovery exercise. Observe without silently repairing their work; record every intervention.

Exploratory decision thresholds, not promises or statistical validation:

| Question | Initial signal to seek |
| --- | --- |
| Can operators start independently? | Four of five produce their first valid MP4 from the docs within 20 minutes, without an author editing code. |
| Is the output useful? | At least three accept an output for an actual intended use. |
| Can they recover? | Four of five complete the documented recovery exercise without losing the accepted project revision. |
| Will they return? | At least three initiate another useful job within seven days. |
| Is it economical? | Record execution, agent usage, setup, support, failed attempts, and active human time per accepted output; compare with each participant's existing workflow. |

Record denominators, failures, environmental blockers, and support effort alongside successes. A small pilot guides the next iteration; it does not establish general demand or superiority.

After measuring effort, offer a specifically scoped paid follow-on to the actual buyer. Set price from observed costs and customer value, not assumed free agent labour. Record real commitments and payments separately from compliments or stated interest. Do not forecast revenue from an unrun pilot.

