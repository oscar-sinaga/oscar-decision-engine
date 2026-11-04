# Follow-up audit — 4 November 2026

Scope: the proposed hardening PR, not a production deployment. Baseline source:
`303162b0b26bbbd75159c0784d2f6c925f34d9ce` (previous application head `05d0055c`).

## Reproduction evidence

The existing pure engine unit suite passed 108 tests. Fourteen additional cases
**failed on the baseline**: bool/number equality and membership, large-integer
ordering, ISO date ordering, omitted membership operands, non-finite scores,
non-finite JSON payloads, ambiguous dotted payload keys, and DATE overlap analysis.
The same unit suite plus regressions passed 122 tests after the local corrections.
Full database/browser validation is performed by the accompanying CI run; local
unit results do not stand in for that validation.

## Corrections under test

| Area | Defect and correction |
| --- | --- |
| Runtime catalog | Newly registered PAYLOAD features were accepted by rule authoring but dropped by the executor's static map. Resolved plans now carry the governed payload paths/types. Retiring a catalog entry does not erase inputs of already-approved versions. |
| Input types | Numbers, booleans, strings and dates are no longer implicitly interchangeable. NaN/Infinity and ambiguous dotted keys are rejected. Required-field policy remains configurable. |
| Rule comparisons | Boolean equality is distinct from 0/1, integer ordering keeps precision, and canonical ISO dates compare consistently with authoring validation. Membership operands must be supplied and shaped correctly. |
| Decision-table warnings | DATE range overlap checking no longer raises an uncaught TypeError. Overlap remains conservative, and discrete candidate values use the same runtime comparisons. |
| Model scores | Non-finite scores are treated as unavailable rather than receiving a valid risk grade. |
| Maker-checker | The initial creator, recorded editors, and submitter cannot approve their own change, across rules, tables, scorecards and strategies. |
| Concurrent configuration | Transaction-scoped shared/read and exclusive/write policy locks protect resolved plans and lifecycle checks. Writers refresh previously loaded ORM objects after acquiring the lock. |
| Simulation evidence | Evidence is bound to a fingerprint of the resolved graph, referenced configurations and catalog. Graph/dependency changes invalidate old evidence; activation rechecks it. Old simulations without fingerprints must be rerun. |
| Published rule sets | Membership used by pending, active or retired strategy versions cannot be edited in place. Create a new rule set and governed draft instead. The existing expression integration test now follows this workflow without weakening outcome/trace assertions. |
| Batch simulation | Absence of an active comparison policy is handled deliberately. An invalid stored active policy is still an error, not silently skipped. |
| Manual review | FRAUD_INVESTIGATION stays open/escalated with the application pending, not approved/closed. A subsequent fraud approval still requires override permission. Concurrent stale decisions are serialized per case. |
| Assignment/documents | Unknown assignee filters return no rows, invalid assignees are rejected, and document resolution requires an open case and a requested document. Approval financial terms are forbidden on non-approval outcomes; the UI clears them accordingly. |
| JWT | Signed tokens must contain expiration, issuance, subject and actor claims. Known published development JWT values are rejected for non-local environments. |
| Test isolation | The destructive integration fixture refuses any database name except `oscar_test` before loading application code or opening a connection. |

## Compatibility and operational notes

The advisory-lock namespace is intentionally conservative for an internal policy
workbench. Decision readers remain concurrent; long batch simulations may delay
policy changes until their transactions finish. Measure contention under the
intended workload before production. A future immutable policy snapshot format
may reduce that contention; this patch does not claim such a redesign.

Rule-set membership edits and stale simulation attachment now fail explicitly.
Existing traces and audit rows are not rewritten. Credit-policy thresholds are
unchanged. No production database, secret, main-branch ref or deployment is touched.

## Dependency review

The initial lockfile scan reported npm advisories for 28 packages (6 high), and
Python advisories involving anyio, certifi, dnspython, PyJWT and urllib3. These are
scanner observations, not proof that all reported exploit preconditions exist in
this application. Compatible lockfile updates are tested with the application;
no forced major-version downgrade or audit suppression is used.

The initial PyJWT report included a no-fixed-version advisory about reusing a
mutable options mapping after disabling signature verification. OSCAR uses a new
options mapping per decode and does not disable signature verification. Record
any remaining scanner finding explicitly; do not call the dependency tree clean
merely because functional CI is green.

## Release status

Keep PR #1 in review. Passing this regression suite is not proof of an absolute
absence of bugs. Production database restore/migration rehearsal, protected
branch rules, privacy classification, load testing, and independent security/UAT
remain distinct release requirements.
