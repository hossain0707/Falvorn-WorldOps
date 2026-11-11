# Changelog

## 0.2.0 — 2026-11-12

- Added separate read-only operator key and server-derived audit reviewer identity; removed client-spoofable reviewer labels.
- Introduced PostgreSQL advisory-lock leader election for the world scheduler; SQLite remains single-worker development only.
- Strengthened browser-facing security headers and static frontend content security policy.
- Hardened API/worker containers with read-only filesystems, removed capabilities and resource limits.
- Added dedicated liveness probe, negative auth tests, security and contribution guides, release checklist, and source packaging excludes.
- Retained independent implementation and commercial-rights-reserved licensing.

## 0.1.0 — 2026-11-11

- Initial governed multi-agent world simulator, persistent domain, optional LLM adapter, evaluated heuristic policies, and operator dashboard.
