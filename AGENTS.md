# Maintaining CohortFrame

Read README.md, docs/ARCHITECTURE.md, docs/SECURITY.md and docs/SUCCESSION.md before changes.

- Preserve the versioned CLI/project contract. New behaviour requires explicit compatibility decisions.
- Keep proposed, implemented, verified and delivered states distinct. A test fixture is not a live learner result.
- Validate untrusted JSON and paths. No arbitrary shell commands, executable templates or implicit provider calls.
- Keep secrets and customer material outside commits and learning records.
- Use expected revisions for project edits and immutable job inputs. Do not silently duplicate paid work in future adapters.
- Test a behaviour that could actually fail. Preserve meaningful regression cases and known limitations.
- Maintain evidence of fresh-install, render, recovery and handover checks for each release.
- Respect the Atlas competence floor while allowing stronger approaches, justified framework challenges, attribution and dissent.
- School admission does not grant customer-data or production-administration access.
- Human stewardship and an independently enforceable stop mechanism remain part of the design.

