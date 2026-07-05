# OSCAR Decision Engine — Workbench

SvelteKit (Svelte 5) + TypeScript strict + Tailwind CSS single-page workbench
for the OSCAR credit-risk decision engine. All authorization is enforced by
the FastAPI backend; the UI's permission checks are UX only.

## Screens

Dashboard KPIs · Decision history + trace detail · Rule management with a
guided condition builder and dry-run tester · Strategy builder with
activation/rollback · Single application simulator (active-vs-draft compare) ·
Manual review queue + case decisioning · Business audit log · Admin (users,
roles, pending approvals).

## Development

```bash
# backend must be running (see ../backend/README.md); CORS allows :5173/:4173/:3000
npm install
npm run dev            # http://localhost:5173
```

Set `VITE_API_BASE_URL` to point at a non-default backend (default
`http://localhost:8000`).

## Quality gates

```bash
npm run lint           # prettier + eslint
npm run check          # svelte-check (strict TypeScript)
npm run test:unit -- --run
npm run build          # production build (adapter-node)
npx playwright test    # e2e — requires the backend stack (docker compose up)
```

Demo credentials are listed in the repository root README.
