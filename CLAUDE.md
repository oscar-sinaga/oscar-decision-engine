# OSCAR Decision Engine — Claude Code Instructions

@AGENTS.md

- Treat `AGENTS.md` and the documents under `docs/` as authoritative.
- Read `AUTONOMOUS_IMPLEMENTATION_PROMPT.md` when asked to execute the full MVP autonomously.
- Implement sequentially in small, testable vertical slices.
- Do not stop for routine approval between phases when autonomous execution was requested.
- Stop only for a genuine blocker that changes credit-decision meaning, risks destructive data loss, requires production access, or cannot be safely isolated with a mock/adapter.
- Create local commits only; never push or deploy.
- Keep `docs/IMPLEMENTATION_STATUS.md` and `docs/IMPLEMENTATION_DECISIONS.md` current.
- Keep product docs, API contracts, data model, tests, and implementation behavior synchronized.
- Never use real customer data, production credentials, or production systems.
