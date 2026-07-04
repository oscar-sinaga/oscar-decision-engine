# Implementation Decisions

> Record material architectural, security, product-scope, and data-contract decisions. Do not record trivial coding choices.

## Decision Template

### ADR-XXX — Title

- **Date:** YYYY-MM-DD
- **Status:** Proposed / Accepted / Superseded
- **Context:**
- **Options considered:**
- **Decision:**
- **Reasoning:**
- **Consequences:**
- **Related documents/files:**

---

### ADR-001 — Backend toolchain: uv + Python 3.13

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** Spec requires Python `>=3.12,<3.15`; the system Python is 3.11. `docs/16` allows `uv` (preferred) or pip/venv.
- **Options considered:** (a) pip/venv with a manually installed 3.12+, (b) `uv` managing interpreter + lockfile.
- **Decision:** `uv` with CPython 3.13.12 pinned via `.python-version`; dependencies locked in `uv.lock`.
- **Reasoning:** `uv` provides the required interpreter without touching the system Python and produces a committed lockfile, satisfying the reproducibility policy.
- **Consequences:** All backend commands run through `uv run`; Docker image uses the same lockfile via `uv sync --frozen`.
- **Related documents/files:** `backend/pyproject.toml`, `backend/uv.lock`, `backend/Dockerfile`, `docs/16_dependency_version_policy.md`.

### ADR-002 — Auth/crypto dependencies: PyJWT + bcrypt instead of python-jose + passlib

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** `docs/15` lists `python-jose[cryptography]` and `passlib[bcrypt]` as *optional* suggestions for later. JWT + password hashing are needed for RBAC.
- **Options considered:** (a) python-jose + passlib as suggested, (b) PyJWT + bcrypt directly.
- **Decision:** `pyjwt>=2,<3` and `bcrypt>=4,<6`. Also added `pydantic-settings>=2,<3` for typed env configuration (the pydantic-v2 companion package).
- **Reasoning:** passlib is unmaintained and incompatible with modern bcrypt releases; python-jose has a history of CVEs and slow maintenance. PyJWT and bcrypt are the actively maintained, minimal equivalents. The docs marked their suggestions optional, so this is an allowed deliberate choice, documented per the dependency policy.
- **Consequences:** Token encode/decode uses PyJWT API; password hashing uses `bcrypt` directly.
- **Related documents/files:** `backend/pyproject.toml`, `docs/15_tech_stack.md`, `docs/16_dependency_version_policy.md`.

### ADR-003 — Compose PostgreSQL exposed on host port 5455

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** Host port 5432 is already occupied by a pre-existing local PostgreSQL service on the development machine.
- **Decision:** The project's PostgreSQL 16 container maps `5455:5432`; all local defaults (`settings.py`, `alembic.ini`, `.env.example`) use 5455. Inside the compose network the backend still uses 5432.
- **Reasoning:** Avoids colliding with (or accidentally using) an unrelated local database — decisive for the "never touch non-project data" rule.
- **Consequences:** Developers connecting with external tools must use port 5455.
- **Related documents/files:** `docker-compose.yml`, `backend/app/shared/config/settings.py`, `backend/alembic.ini`.

### ADR-004 — Observability implementation: stdlib JSON logging + pure-ASGI correlation middleware

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** `docs/18` requires structured sanitized logs, request/correlation IDs on every response, and safe error envelopes. `docs/15`/`docs/16` prefer the standard library over new observability dependencies.
- **Options considered:** (a) `structlog`, (b) stdlib `logging` with a JSON formatter and `contextvars`.
- **Decision:** Stdlib logging with a custom `JsonLogFormatter` that redacts sensitive keys, plus a pure-ASGI `CorrelationMiddleware` that generates/propagates IDs, times requests, emits one structured log per request, and converts unhandled exceptions into the documented error envelope (exception *type* only — never stack traces or messages) before they can leak.
- **Reasoning:** Meets every docs/18 requirement with zero added dependencies; pure ASGI avoids `BaseHTTPMiddleware` streaming pitfalls; redaction at the formatter guarantees no code path can log prohibited values unredacted.
- **Consequences:** All structured log fields pass through `app/shared/utils/masking.redact`; masking is deny-list based on key names and intentionally over-redacts (e.g. a `documents` key is masked entirely).
- **Related documents/files:** `backend/app/shared/logging/`, `backend/app/shared/utils/masking.py`, `docs/18_observability_and_audit_logging.md`.
