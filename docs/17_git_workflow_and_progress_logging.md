# 17 — Git Workflow & Implementation Progress Logging

## 1. Purpose

Git and progress documents are safety and review mechanisms for autonomous implementation. They are not substitutes for product audit trails.

## 2. Branch and Remote Rules

- Work in an isolated feature branch or worktree.
- Create local commits only.
- Never push, merge, force-push, rebase shared branches, tag a release, or deploy without explicit human approval.
- Preserve unrelated pre-existing changes.
- Never rewrite human commits.

## 3. Commit Boundary

Create a commit after a coherent vertical slice or completed phase, for example:

- project foundation,
- decision runtime,
- rule management,
- strategy execution,
- decision trace,
- simulation,
- manual review,
- governance,
- monitoring,
- end-to-end hardening.

Do not commit every file edit. Do not bundle unrelated features into one commit.

## 4. Pre-Commit Quality Gate

Before committing, run all checks relevant to the change:

- formatter,
- linter,
- backend type checking,
- backend unit/integration tests,
- frontend strict TypeScript check,
- frontend tests and production build,
- Alembic migration on a clean database,
- OpenAPI generation,
- secret and PII review.

Do not disable or weaken tests to obtain a green result.

## 5. Commit Message Convention

Use conventional commit style:

```text
<type>(optional-scope): concise imperative summary
```

Recommended types:

- `chore`
- `feat`
- `fix`
- `refactor`
- `test`
- `docs`
- `perf`
- `security`

## 6. Files That Must Never Be Committed

- `.env` and credentials,
- production access tokens or API keys,
- real customer data or documents,
- full NIK/phone/address in fixtures,
- raw bureau/eKYC/fraud responses,
- dependency caches,
- build artifacts,
- temporary debug dumps,
- raw agent conversations or excessive terminal output.

Use `.env.example` and synthetic fixtures.

## 7. Progress Documents

### `docs/IMPLEMENTATION_STATUS.md`

Update before every phase commit with:

- overall status,
- completed/current/next phases,
- acceptance-criteria status,
- quality-gate results,
- known limitations,
- current blockers,
- latest local commit.

### `docs/IMPLEMENTATION_DECISIONS.md`

Record material decisions using an ADR-style format:

- context,
- options considered,
- decision,
- reasoning,
- consequences,
- related documents/files.

Do not record trivial syntax or formatting choices.

### `docs/BLOCKERS.md`

Use only for genuine blockers. Routine implementation uncertainty is not a blocker.

### `docs/FINAL_IMPLEMENTATION_REPORT.md`

Complete after all MVP quality gates pass.

## 8. Documentation Synchronization Rule

Any behavior change must update every affected source of truth in the same commit:

- PRD and scope,
- architecture,
- data model and migration notes,
- API contract and OpenAPI,
- backlog/acceptance criteria,
- screen specification,
- security/audit/logging documentation,
- tests,
- README or run instructions.

A phase is not complete when code and documentation disagree.
