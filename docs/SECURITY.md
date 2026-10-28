# Security and current limits

## Current boundary

CohortFrame 0.1 is a local development alpha for trusted operators and approved assets. It does not enforce operating-system isolation or defend against a caller who controls its process, database, job directories or FFmpeg executable. The initial agent permissions are those of the caller's local process. This is not yet suitable for unattended untrusted agents or public multi-tenant hosting.

The application does not need provider credentials, expose an HTTP listener, run submitted scripts, execute HTML templates or call paid AI services. External rendering tools process local snapshots. Strict input validation and subprocess argument lists reduce particular classes of mistakes; they do not establish that a native decoder or the operating environment is invulnerable.

## Properties to verify

- Reject malformed and duplicate-key JSON, unsupported manifest versions, invalid dimensions, excessive durations, and unsupported local audio.
- Reject stale changes and conflicting idempotency keys.
- Keep submitted job inputs independent from subsequent project or source-file changes.
- Require valid identifiers and constrain application-owned job paths.
- Bound render runtime and preserve explicit cancellation/failure state.
- Verify output media before reporting a successful artifact.
- Avoid shell interpolation of user text or arbitrary FFmpeg filters.

See the test suite and validation record for observed evidence and its limits.

## Before a broader release

Verify process and filesystem isolation on each supported platform; separate rendering, provider credentials, policy enforcement and release privileges. Add input fuzzing and native dependency review appropriate to the accepted media formats. Review authenticated distribution and updates before marketing protected installations. A provider's commercial integration terms and output rights need verification before it is offered through the product.

Production safeguards must be enforced outside the model. School admission, a maintainer title, or an API key does not grant general authority to access customer data, change policy, publish releases or spend money.

Sensitive findings should go to the founder or the project's established private channel. Preserve a minimal reproduction using synthetic data. Do not place secrets or private customer material in issues, logs, examples or school learning records.

