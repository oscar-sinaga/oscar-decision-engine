// The workbench is an internal SPA: authentication lives in the browser
// (bearer token) and all data comes from the FastAPI backend, so SSR is
// disabled (ADR-009).
export const ssr = false;
export const prerender = false;
