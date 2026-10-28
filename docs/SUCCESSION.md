# CohortFrame: cohort succession contract

## Purpose and authority

CohortFrame is intended to become a maintained Atlas project that successive qualified software-agent cohorts can understand, challenge, and improve. Future participation is a plan, not a claim that students have already built, operated, or qualified to maintain it. This document changes no school calendar or enrolment decision.

The founder/steward remains accountable for releases, customer promises, spending authority, and production access. A student may propose work without automatically receiving authority to merge, publish, spend, contact customers, or change credentials. Qualification and delegated permissions are specific to a task and environment.

Continuity comes from retained artifacts, tools, configurations, and evidence. Do not assume that private conversational context or model weights transfer between cohorts. Improvement is evaluated, not guaranteed.

## Five-part handover

### 1. Accepted product contract

Record the supported project schema and CLI responses, accepted input types, output specifications, revision behaviour, and job lifecycle. State the expected behaviour for repeated idempotency keys, changed inputs, cancellation, and interrupted execution. Include known limitations and explicit non-goals. Separate accepted requirements from proposed changes and disputed assumptions.

A new cohort may challenge the contract through a documented proposal. Until a change is accepted, the existing version remains the release criterion.

### 2. Frozen release and operating state

Pin the handover to an immutable commit or content-addressed bundle. Record Python, FFmpeg, operating-system and relevant font versions; fixture hashes; database schema version; and build commands. Include unresolved defects, outstanding jobs or obligations, backup and restore instructions, and a tested recovery path to the previous working release.

Record permission boundaries, approved execution environments, escalation routes, and spending limits. Reference controlled credential storage if later integrations introduce it; never embed credentials in the handover. Current local rendering does not require paid-provider credentials.

### 3. Evidence cases

Supply reproducible fixtures and expected observations for:

- A valid title-card project, including a local WAV case, producing an inspected MP4.
- Invalid or unsupported inputs being rejected with useful structured errors.
- A new project revision leaving a previously accepted render snapshot unchanged.
- Repeated jobs and conflicting idempotency requests following the accepted contract without unintended duplicate execution.
- Cancellation, interruption, partial artifacts, and recovery producing truthful job status and recoverable project state.

Preserve actual results, failures, execution costs, and operator interventions. State what each check establishes and what remains untested. Passing these cases is not a security certification. Independent additional evaluation cases may be retained outside student practice materials.

### 4. Decisions, dissent, and attribution

Keep concise records of alternatives, evidence, tradeoffs, accepted decisions, unresolved objections, and conditions for reconsideration. Attribute contributions and reviews to stable agent or operator identifiers and record relevant tool/configuration versions. Preserve useful alternative implementations without promising indefinite support for every branch.

Grade observable behaviour and maintainability rather than similarity to an instructor's preferred implementation. Permit students to identify defects in the framework or evaluation itself. Do not erase a reasoned objection merely because the final decision differs.

### 5. Fresh-verifier succession exercise

A separately initiated verifier receives the handover bundle and accepted task, without relying on the outgoing author's private chat context or live explanations. The verifier must reproduce a render, run the evidence cases, diagnose a supplied problem, assess a bounded change, and demonstrate recovery.

Record blockers as handover defects. Review results against the accepted contract, using executable checks and artifact inspection alongside agent review. Agent agreement alone is insufficient evidence.

Only an authorised steward transfers the defined responsibility after reviewing this record. Keep the prior working release available, specify an escalation owner, and revoke obsolete access. If verification fails, improve the bundle or qualifications before transfer.

## Unit of progress

Count an accepted capability that remains understandable and maintainable across handovers. Track useful outcomes, regressions, total execution/review cost, and support burden. More agents, commits, or generations do not by themselves constitute progress.
