# Release readiness — 0.2.0

| Gate | Status | Evidence / remaining action |
|---|---|---|
| Source and backend modularization | Implemented | Isolated API/core/domain/services/frontend/infra |
| Persistent schema and migrations | Implemented | Alembic initial migration checked in; production migration dry-run needed |
| Research sandbox reproducibility | Implemented | Seeded heuristic agents and evaluation script; does not reproduce research results |
| API security | Partially implemented | Admin/read-only keys; behind TLS+VPN/OIDC edge; lacks app-native per-user SSO |
| Agent action security | Implemented for allowlisted actions | All proposals verified by deterministic policy; no general tool execution |
| Human review and dispatch | Implemented for configured webhook | Explicit approve+dispatch, signed payload; receiver idempotency must be verified |
| Background concurrency | Partially implemented | PG advisory leader election and per-world row locks; LLM call still holds transaction |
| Tests | Locally verified | Backend pytest and JS syntax checks, no PostgreSQL/Docker load/integration suite |
| Container | Configured | Non-root image, no new privileges, read-only API/worker, localhost binding; real deploy untested |
| Observability | Incomplete | Event DB + worker logs; no hosted alerting, OTEL or external immutable audit sink |
| Privacy and tenancy | Not implemented | No tenant RBAC, retention/deletion policies or individual user sessions |
| Reliability | Not fully validated | Requires restored-backup drill, live PG failover test, scale test and worker queue redesign |
| Public SaaS readiness | **Blocked** | Do not claim production certification; see `OPERATIONS.md` |

**Release scope:** private development, research, and controlled single-organization pilots **without high-impact actions**. Public SaaS and high-stakes workflows remain out of scope until all release blockers pass.
