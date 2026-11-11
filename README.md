# OSCAR Decision Engine — Implementation Pack v1.1 Synchronized

<!-- DOCKER-INSTALL-START -->

## Panduan instalasi Docker

Pilih [tanpa Nginx](#instalasi-docker-tanpa-nginx) atau
[dengan Nginx](#instalasi-docker-dengan-nginx). Panduan ini untuk instalasi baru
yang mandiri; tidak memerlukan Tencent atau ACC.
Prasyarat host Linux/Ubuntu 24.04 atau WSL: Git, Docker Engine, plugin Docker
Compose **2.30+**, Python **3.10+**, dan OpenSSL. Python host hanya menjalankan
helper; aplikasi dan PostgreSQL berjalan di container. Autentikasi GitHub diperlukan
untuk clone repo private. Docker Engine tidak dipasang/diubah otomatis oleh helper.
Di Windows, jalankan perintah Bash dari Ubuntu WSL dan clone di filesystem Linux
(misalnya `~/projects`), agar permission privat 0700/0600 dapat diterapkan.

```bash
git clone --branch main https://github.com/oscar-sinaga/oscar-decision-engine.git
cd oscar-decision-engine
docker version
docker compose version
python3 --version
openssl version
```

Compose di root untuk development berbeda dari paket mandiri ini.
Paket instalasi memakai `deploy/replica/compose.yaml`; helper memilih profile,
file env privat, dan override yang benar. JSON pada berkas tersebut valid sebagai YAML.
Pilih satu mode pada checkout baru. `init` menolak menimpa `.private/replica` existing;
`up` menolak restart implisit layanan yang sudah aktif. Untuk upgrade existing, audit
dan backup dahulu; jangan menghapus konfigurasi atau volume agar bisa mengulang init.
Untuk instalasi kedua pada daemon yang sama, pilih `--project` dan port yang berbeda.

## Instalasi Docker tanpa Nginx

Mode `direct` menjalankan HTTP pada **127.0.0.1 saja**, untuk laptop atau SSH tunnel
ke server lain. Container Nginx tidak dijalankan dan tidak perlu sertifikat TLS.

```bash
python3 deploy/replica/manage.py init --proxy direct --origin http://127.0.0.1:3000
python3 deploy/replica/manage.py check
python3 deploy/replica/manage.py build
python3 deploy/replica/manage.py migrate
python3 deploy/replica/manage.py bootstrap-admin
python3 deploy/replica/manage.py up
python3 deploy/replica/manage.py status
```

Buka **http://127.0.0.1:3000/** pada host yang menjalankan Docker.
API langsung tersedia di http://127.0.0.1:8002/v1.
Login aplikasi: user `oscar`, password dipilih pada prompt init. Bootstrap membuat satu admin dan RBAC tanpa akun/policy demo.
Frontend dibangun dengan URL API langsung; CORS otomatis mengikuti origin web. Jangan mengganti port API setelah build tanpa membangun ulang frontend.

Jika Docker berjalan pada server remote, dari laptop jalankan:

```bash
ssh -N -L 3000:127.0.0.1:3000 -L 8002:127.0.0.1:8002 USER@IP_SERVER
```

Lalu buka URL 127.0.0.1 yang sama di laptop. Tetap gunakan port lokal yang sama
agar origin/CORS sesuai. Untuk mengubah port saat init, sesuaikan `--origin`
dan `--direct-api-port` serta tunnel. Mode ini tidak membuka HTTP ke IP publik;
akses internet memakai mode HTTPS di bawah atau terminasi TLS yang dikonfigurasi operator.

## Instalasi Docker dengan Nginx

Mode `nginx` menjalankan reverse proxy rootless melalui satu port **HTTPS 443**.
API, frontend, agent dan PostgreSQL tetap di jaringan Docker tanpa port publik.
Gunakan checkout baru untuk memilih mode ini; ganti `YOUR_HOST` dengan domain atau
IP yang tercakup sertifikat, tanpa path. Tidak memerlukan domain berbayar bila
operator mempunyai sertifikat IP yang sah.

```bash
python3 deploy/replica/manage.py init --proxy nginx --origin https://YOUR_HOST
python3 deploy/replica/manage.py check
python3 deploy/replica/manage.py build
python3 deploy/replica/manage.py migrate
python3 deploy/replica/manage.py bootstrap-admin
# Pasang sertifikat seperti langkah berikut sebelum menjalankan up.
```

Simpan full certificate chain di `.private/replica/tls/fullchain.pem` dan private
key di `.private/replica/tls/privkey.pem`. Gunakan sertifikat yang sah untuk host
tujuan; sertifikat serta auto-renewal diurus operator dan tidak disalin dari Tencent.
Setup tidak mendaftarkan ACME atau menerima terms pihak ketiga secara otomatis.
Untuk init oleh user Linux biasa, file harus dapat dibaca UID operator yang sama;
batasi private key dengan `chmod 600 .private/replica/tls/privkey.pem`.
Jika init dijalankan root, proxy memakai UID/GID **10001:10001**: ownership
direktori TLS dan kedua file harus sesuai, key tetap mode 0600.

```bash
python3 deploy/replica/manage.py up
python3 deploy/replica/manage.py status
curl --fail --silent --show-error https://YOUR_HOST/login
```

Buka **https://YOUR_HOST/**. Login `oscar` memakai password yang dipilih saat init.

Pada server baru, siapkan akses firewall TCP 443 dan pertahankan akses SSH.
Beberapa aplikasi pada satu IP tidak bisa masing-masing mengikat 443 bersamaan;
gabungkan route pada satu reverse proxy atau gunakan IP publik/mesin yang berbeda. Integrasi
ACC pada Tencent mengikuti registry/guard existing, bukan instalasi standalone ini.

## Database existing, credential dan backup Docker

Untuk memakai PostgreSQL yang sudah ada, tambahkan opsi berikut pada **perintah init
mode yang dipilih** (bukan menjalankan init kedua):

```text
--database existing --db-host YOUR_DB_HOST --db-name oscar_decision --db-user decision_app
```

Buat database/role khusus aplikasi terlebih dahulu; password diminta tersembunyi.
Existing mode tidak membuat ulang server database atau mengganti volume.
Gunakan hostname/IP database yang dapat dijangkau container; `127.0.0.1` di dalam
container menunjuk container itu sendiri.
Untuk database Docker dalam jaringan private, gunakan tambahan
`--db-network NETWORK --db-network-owner COMPOSE_PROJECT` dan, hanya bila jaringan
Docker internal terpercaya itu tidak menyediakan TLS, `--db-sslmode disable`.
Helper memverifikasi bridge internal, label owner/network dan ID jaringan.
Untuk koneksi remote defaultnya TLS `require`; lihat opsi CA/verify-full pada
[panduan replikasi](deploy/replica/README.md).

Credential tersimpan di host tujuan pada `.private/replica` (0700), file env (0600),
dan tidak masuk Git/image. Jangan menaruh secret pada perintah terminal atau README.
Volume database tetap ada saat container diganti.

```bash
python3 deploy/replica/manage.py backup
python3 deploy/replica/manage.py restore-check --backup-dir backups/replica/TIMESTAMP
```

Ganti TIMESTAMP dengan direktori hasil backup. Restore-check benar-benar mengimpor
dump ke database sementara terisolasi; tidak menimpa database aplikasi yang aktif.
Enkripsi/copy backup off-host dan jadwalkan retensi sesuai kebijakan operator.
Clone source tidak memindahkan data atau credential lama. Jangan memakai `down -v`
atau `volume prune` pada deployment yang berisi data. Rincian resource, restore,
healthcheck dan batas pengujian ada di [panduan replikasi](deploy/replica/README.md).

<!-- DOCKER-INSTALL-END -->

This pack is the implementation handoff for **OSCAR Decision Engine**, an internal enterprise credit-risk decision engine for multifinance use cases such as motor/car financing, dealer/channel applications, and motor/car lease-back.

> **Implementation status:** the MVP described by this pack is implemented in
> `backend/` (FastAPI 0.139.0) and `frontend/` (SvelteKit workbench).
> See `docs/IMPLEMENTATION_STATUS.md` and `docs/FINAL_IMPLEMENTATION_REPORT.md`.
> Phase 3 specification: `docs/phase3/`. **New to credit risk / decision engines?**
> Start with the Indonesian learning curriculum in `docs/learning/`, then the
> hands-on Indonesian user guide in `docs/user-guide/` (screen-by-screen usage,
> parameters, and per-role workflows).

## Running the Implemented System

```bash
# First: copy .env.example to .env and replace BOTH secret placeholders with random values.
# Review docs/SECURITY_HARDENING.md before updating an existing PostgreSQL volume.
cp .env.example .env
# Edit .env: OSCAR_POSTGRES_PASSWORD and OSCAR_JWT_SECRET must not be placeholders.
# Optional: explicitly enable synthetic demo seeding on a fresh, LOCAL database only.
# OSCAR_ENABLE_DEMO_SEED=true and OSCAR_SEED_PASSWORD=<unique-demo-password>
docker compose up -d --build
# API:       http://localhost:8000  (OpenAPI at /docs)
# Workbench: http://localhost:3000
```

Demo accounts are **not seeded by default**. For a new, disposable local database, opt in with
`OSCAR_ENABLE_DEMO_SEED=true` and set `OSCAR_SEED_PASSWORD` in the ignored `.env` file.
Synthetic roles include `admin`, `riskanalyst`, `riskmanager`, `underwriter`,
`compliance`, `datascientist`, `engineer`, `auditor`, and `los-client`.
Do not deploy these users or the local compose stack to an untrusted network.

For local development and quality gates see `backend/README.md`, `frontend/README.md`, and
`docs/SECURITY_HARDENING.md`. GitHub Actions validates backend, frontend, and browser E2E
on pushes/PRs; branch protection must be enabled separately by a repository administrator.

IDX iDecision is used as a local benchmark and visual reference. It is not the complete product scope to copy.

## Final Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI `0.139.0`, Python, Pydantic v2 |
| Database | PostgreSQL, SQLAlchemy 2.x, Alembic |
| Backend tests | pytest + httpx |
| Frontend | SvelteKit latest stable at scaffold time |
| Frontend language | TypeScript strict mode |
| Styling | Tailwind CSS latest stable at scaffold time |
| Frontend tests | Vitest + Playwright for critical flows |
| API contract | OpenAPI generated by FastAPI |

Dependencies must be resolved to stable versions and committed through lockfiles.

## What Was Added in v1.1

This version synchronizes the implementation pack with the autonomous-agent requirements for Git, progress tracking, technical logging, decision trace, and business auditability.

Added:

- `CLAUDE.md`
- `AUTONOMOUS_IMPLEMENTATION_PROMPT.md`
- `docs/17_git_workflow_and_progress_logging.md`
- `docs/18_observability_and_audit_logging.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/IMPLEMENTATION_DECISIONS.md`
- `docs/BLOCKERS.md`
- `docs/FINAL_IMPLEMENTATION_REPORT.md`

Updated:

- PRD, architecture, scope, data model, API contract, backlog, screens, trace, simulation, manual review, governance, technology, and dependency policy.
- `AGENTS.md` now requires local phase commits, synchronized docs, structured logs, correlation IDs, PII masking, and separate business audit events.

## Logging Taxonomy

OSCAR has three distinct evidence layers:

1. **Technical application log** — operational troubleshooting; structured, sanitized, correlation-aware.
2. **Decision trace** — immutable evidence explaining and reproducing one credit decision.
3. **Business audit event** — append-only record of who changed or decided what, when, why, and under which version.

They must not be collapsed into one generic log table.

## Git Policy

- Local commits only during autonomous implementation.
- One commit per coherent vertical slice or completed phase.
- Quality gates must pass before commit.
- Never push, deploy, force-push, rewrite human commits, or commit secrets/PII.
- Update implementation status and affected documentation in the same commit.

## Recommended Reading Order

1. `CLAUDE.md`
2. `AGENTS.md`
3. `docs/01_research_summary.md`
4. `docs/04_idx_idecision_analysis.md`
5. `docs/05_mvp_scope.md`
6. `docs/02_prd_mvp.md`
7. `docs/03_architecture.md`
8. `docs/15_tech_stack.md`
9. `docs/16_dependency_version_policy.md`
10. `docs/17_git_workflow_and_progress_logging.md`
11. `docs/18_observability_and_audit_logging.md`
12. `docs/06_data_model.md`
13. `docs/07_api_contract.md`
14. `docs/08_backlog_mvp.md`
15. `docs/09_screen_spec.md`
16. `docs/10_rule_engine_design.md`
17. `docs/11_decision_trace_design.md`
18. `docs/12_simulation_design.md`
19. `docs/13_manual_review_design.md`
20. `docs/14_audit_governance.md`

## Autonomous Claude Execution

Open the repository in Claude Code and provide the contents of:

```text
AUTONOMOUS_IMPLEMENTATION_PROMPT.md
```

The agent must maintain:

- `docs/IMPLEMENTATION_STATUS.md`
- `docs/IMPLEMENTATION_DECISIONS.md`
- `docs/BLOCKERS.md` only for genuine blockers
- `docs/FINAL_IMPLEMENTATION_REPORT.md`

## First Vertical Slice

```text
Decision API
  -> Configurable Rule Execution
  -> Final Decision and Reason Codes
  -> Immutable Decision Trace
  -> Business Audit Event
  -> Structured Technical Log with Correlation ID
```

Do not begin with the frontend or a visual flow builder.
