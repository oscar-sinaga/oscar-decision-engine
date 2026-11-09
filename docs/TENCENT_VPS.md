# Tencent operator-authorized deployment

The operator authorized installation on their existing Tencent VPS on 2026-11-09.
This is an explicit exception to the repository's default no-deployment rule;
the subsequent operator instruction on 2026-11-09 explicitly authorizes
committing and pushing all application/VPS changes to the existing GitHub
repositories. This scoped authorization overrides the default local-only rule
for this synchronization; no force push or credential publication is authorized.

- Public workbench: `https://150.109.17.147/workspaces/decision-engine/`.
  ACC administrator authentication gates all frontend and backend routes.
  Decision Engine also requires its own JWT login and enforces backend RBAC.
- Web build arguments: `OSCAR_BASE_PATH=/workspaces/decision-engine` and
  `VITE_API_BASE_URL=/workspaces/decision-engine/backend`. Navigation and API
  requests stay under that prefix. Empty base and absolute API origins keep
  development behavior unchanged.
- The API uses `--root-path /workspaces/decision-engine/backend`, one worker,
  locked FastAPI 0.139.0 and the existing PostgreSQL 17 container. The dedicated
  database is `oscar_decision_engine`, role `decision_app`, pool 3 + overflow 1.
  Existing `server_internal` data is preserved.
- API cap: 192 MiB / 0.10 CPU; web cap: 96 MiB / 0.05 CPU. Non-root containers,
  read-only roots, bounded temporary files/logs, no host ports. Only Nginx HTTPS
  443 is public; SSH remains on 22. Both services are protected always-on apps.
- Credentials are generated only on the VPS in the root-only `.private`
  directory beneath `/srv/oscar/oscar-decision-engine`. The initial account is
  `admin`; its random password is in `initial-access.txt`. Production seeding
  overrides the public development password using a separate one-off seed env.
  Other seeded accounts have synthetic role identities; rotate before sharing.
- Nginx verifies ACC owner access, forwards the JWT to the API and strips ACC
  cookies from upstream requests. Application data and credentials are never
  exposed by the public workspace navigation index.
- The existing daily backup timer includes all three app databases and role
  definitions without passwords. Restores require the separately retained VPS
  secrets. Existing volumes, PostgreSQL, panel and ingress are not replaced.

Backend quality gates passed with 213 tests. Frontend lint, strict checks,
41 Vitest tests and production build passed. `devalue` was patched to 5.9.4;
production dependency audit reports zero known findings at validation time.
Browser, live HTTPS, restore and exact-revision evidence belong to the shared
operator deployment report; these build results alone do not assert deployment.

## Final local Docker acceptance (2026-11-09)

All 11 Decision browser scenarios passed after fixing Nginx upstream ordering, preload header buffers and the static-asset rate-limit bucket. The audit UI test now creates its own synthetic business event, so a fresh seed works. Login production builds no longer prefill or advertise the development password. Under the target caps, API peak was 96 MiB and web peak 28 MiB, with no OOM/restarts. Job AI separately passed six desktop/mobile scenarios including PDF export. Live deployment and restore results are recorded in the operator report.
