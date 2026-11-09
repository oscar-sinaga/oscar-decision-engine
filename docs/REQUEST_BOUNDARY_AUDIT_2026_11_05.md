# Request-boundary and persistence audit — 5 November 2026 (Asia/Jakarta)

Review baseline: `4a7df58ff97c0096bc5d3eb26d10eb74bcf23e7a` on PR #1.
These findings extend the previous deep audit; they do not imply all possible defects are absent.
Only synthetic test data and ephemeral CI databases are used. No deployment or main-branch merge.

## Confirmed failures and corrections

| Area | Failure found | Correction / regression evidence |
| --- | --- | --- |
| Strategy configuration | `required_fields=null`, object/list elements, and `calculations=null` reached service loops and raised `TypeError` instead of a validation response | Validate list shape in both graph and legacy step requests; invalid writes return 422 and create no version |
| Storage limits | Legacy step names/references, owner team, and canvas positions could exceed their destination columns | Enforce the same limits at both request boundaries; bound graph collections before service processing |
| Catalog PATCH | Explicit null for required feature/model/category fields could cause constraint failures or persist invalid JSON metadata and break subsequent reads | Shared PATCH validation distinguishes omitted, nullable and non-nullable fields; invalid updates leave catalog rows unchanged |
| Nullable edits | `customer_message=null` on a reason code was silently ignored | Use `exclude_unset=True`; clearing a nullable message and setting `active=false` now persist with correct before/after audit values |
| Audit capacity | Valid 200-character feature paths, 201-character model/version identifiers and long strategy version labels overflowed audit columns | Migration `d7a4c192e605` widens both audit identifiers to 256 characters without truncating evidence |
| Concurrent catalog writes | Two identical creates could both pass the precheck and leave the loser with an internal database error | Map only PostgreSQL unique violations (23505) to 409 after rollback; keep other failures visible. Lock mutable catalog rows before reading audit before-state |
| Invalid JSON strings | NUL or unpaired-surrogate strings/keys passed application schema but cannot be persisted in PostgreSQL | Reject at request validation without echoing the supplied value; legitimate Unicode and dotted catalog metadata keys remain supported |

## Test design and evidence

The initial isolated boundary suite reproduced **41 failures / 3 passes** on the review baseline.
After adding three further semantic/concurrency-helper tests, the isolated unit suite contains
**190 passing tests** (143 existing plus 47 new) in the review container. That local run uses
`--noconftest` and is not a substitute for PostgreSQL integration acceptance.

The API regression file additionally exercises invalid PATCH atomicity, nullable clears,
malformed flow requests, maximum-length identifiers, long-code decision execution, three
barrier-synchronized duplicate-create races and rollback protection for existing audit records.
The full test collection contains **368 cases** at this revision. A collection count is not
an assertion that those tests passed. The GitHub Actions result for the exact PR commit is
the authoritative full-stack acceptance record.

Static review also found and corrected one pre-existing Ruff line-length failure in the rule
validator. No formatter is allowed to edit source as a way of making CI pass.

## Migration and rollback safety

`d7a4c192e605` follows `c1e5f09a64d2`. The upgrade preserves audit values and append-only triggers.
Downgrade takes an exclusive table lock and refuses to narrow columns while existing evidence
would exceed the former sizes. It never truncates or deletes evidence to force a rollback.

CI recreates **only the explicitly guarded `oscar_test` database** before the reversible
schema rehearsal, then runs the full test suite again. This is an ephemeral clean-schema
rehearsal, not proof of a successful production/preserved-volume restore. A separate integration
test verifies that downgrade refuses to truncate long immutable evidence.

For an existing deployment: take a recoverable backup, rehearse the upgrade against a protected
copy, and review rollback compatibility before applying it. Do not delete the persistent volume.

## Remaining release gates

PR #1 stays Draft. Main branch protection, production database least privilege, retained-volume
migration/restore rehearsal, policy-owner UAT and real integration/security testing remain
separate gates. Passing CI demonstrates the tested behaviors, not a universal zero-bug guarantee.
