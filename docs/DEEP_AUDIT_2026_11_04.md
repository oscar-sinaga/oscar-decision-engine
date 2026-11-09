# Follow-up audit — 4 November 2026

Scope: proposed hardening PR #1, not a production deployment. Baseline source:
`303162b0b26bbbd75159c0784d2f6c925f34d9ce` (previous application head `05d0055c`).

## Reproduction evidence

The existing pure engine unit suite passed 108 tests. Fourteen additional cases
failed on the baseline: bool/number equality and membership, large-integer
ordering, ISO date ordering, omitted membership operands, non-finite scores,
non-finite JSON payloads, ambiguous dotted payload keys, and DATE overlap analysis.
The same unit suite plus regressions passed 122 tests after the local corrections.
A second set exposed 19 invalid or oversized financial-output cases. With those
corrections and two deterministic property tests, the local unit suite passed 143.
Full PostgreSQL/browser/type validation must be checked separately in GitHub Actions.

## Corrections

| Area | Defect and correction |
| --- | --- |
| Runtime catalog | Newly registered PAYLOAD features were accepted by authoring but dropped by the static runtime map. Resolved plans now carry governed paths/types, including references of existing approved versions. |
| Input/comparison types | Booleans are distinct from numbers, large-integer ordering keeps precision, ISO date ordering is supported, membership operands are validated, and non-finite/ambiguous JSON values are rejected. |
| Decision tables | DATE overlap checking no longer raises an uncaught TypeError. Overlap checking remains conservative rather than a complete symbolic proof. |
| Financial outputs | Strict finite terms and PostgreSQL representability bounds prevent invalid limits, tenors, prices and scores from reaching persistence. Oversized calculated limits take the configured error/fallback path. These are technical bounds, not new lending-policy thresholds. |
| Maker-checker | Initial creators, recorded editors and submitters cannot approve their own configuration change, across rules, tables, scorecards and strategies. |
| Concurrent policy changes | Transaction-scoped shared reader/exclusive writer advisory locks protect plan resolution and lifecycle checks; stale ORM state is refreshed after locking. |
| Simulation evidence | A fingerprint binds evidence to the resolved graph, referenced configurations and catalog. Edited graph/dependencies invalidate stale evidence even when the strategy version ID is unchanged. Old evidence without fingerprints must be rerun. |
| Published rule sets | Membership used by pending, active or retired strategy versions cannot be edited in place. Create a new set and governed draft instead. |
| Batch simulation | An absent active comparison policy is handled deliberately; corrupted active configuration is not silently ignored. |
| Manual review | Fraud investigation remains open/escalated, and subsequent approval requires override permission. Concurrent stale decisions are serialized per case. |
| Assignment/documents | Unknown assignee filters return no rows, invalid assignees are rejected, and document resolution requires an open case/requested document. Approval terms are forbidden on non-approval outcomes, including in the UI. |
| JWT | Signed tokens require expiration, issuance, subject and actor claims; known published development/CI secrets are rejected for hosted environments. |
| Test isolation | The destructive integration fixture refuses any database name except oscar_test before importing application code or opening a connection. |

## Validation integrity correction

The temporary first repair runner had a pipeline exit-status defect: commands
piped into tee did not propagate failure under the implicit shell. Its detailed
logs contained 263 pytest passes / 2 failures and one mypy error despite a green
job. That result is NOT a passing backend acceptance. No main merge or deployment
occurred. The temporary publisher and its payload files were removed.

The final corrections are committed as directly reviewable source. Canonical CI
now uses explicit Bash and set -euo pipefail, checks pipeline failure propagation,
runs two full PostgreSQL suites around a synthetic migration down/up rehearsal,
and repeats the 11 browser scenarios twice. It has read-only repository permissions
and does not edit or publish source code. Any failing gate leaves the job failed.

The two regressions preserve original assertions: catalog operator violations
retain field-specific errors, and expression fixtures use an isolated rule set
without changing seeded rule-usage counts. finite_number now returns a TypeGuard,
retaining runtime checks while making static type narrowing correct.

Two deterministic property tests check 10,000 typed equality and 2,000 overlap
cases. These are sampled checks, not proof over every possible input.

## Dependency evidence

The initial npm audit reported 28 affected packages including 6 high severity.
Compatible updates reduced the recorded full-tree report to 22 (9 low and 13
moderate; no high/critical findings), with 0 in npm's omit-dev runtime tree.
The recorded Python runtime pip-audit reported 0 vulnerabilities after updates.
These are scanner observations, not proof of absent vulnerabilities.

Remaining SvelteKit/tooling findings need a separately reviewed major-version
upgrade. No forced downgrade, audit suppression or blanket claim of safety was
used. Development dependency classification alone does not prove non-exposure:
build-time tooling can affect shipped output.

## Compatibility and release limitations

Decision readers remain concurrent; the conservative policy advisory lock can
make long batch simulations delay configuration writers. Measure contention and
throughput under the intended workload. No production benchmark is claimed.
Existing traces/audits are not rewritten; stale simulations need rerunning.
Keep PR #1 in review. Branch protection, production backup/restore rehearsal,
privacy classification, realistic load tests and independent security/UAT remain
separate requirements. Successful CI cannot establish absolute absence of bugs.
