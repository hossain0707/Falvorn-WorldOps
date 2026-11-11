# Operations and production rollout

## Environment profiles

**Local:** SQLite, auth optional, seeded agents, manual steps. No public exposure.

**Staging:** PostgreSQL, exact CORS, long random API key, HTTPS reverse proxy and VPN. Dedicated disposable data. Run migration and full tests. Enable outbound webhook only to a mock receiver.

**Internal production:** PostgreSQL with automated PITR backups, TLS and access controls, telemetry, support runbook, rotation of API credentials and signing keys, and PostgreSQL advisory-leader scheduler workers. Restrict to approved low-risk workflows.

**Public multi-user production (not yet implemented):** OIDC sessions and role/tenant isolation, distributed scheduling and job budgets, rate limiting, metrics/tracing alerts, privacy retention, model-specific safety evaluation, scaling/DR drills and security audit.

## Startup

1. Provision PostgreSQL and apply `alembic -c backend/alembic.ini upgrade head` from `backend/` or use Compose's `migrate` service.
2. Set `APP_ENV=production`, `DATABASE_URL`, `API_KEY` 24+ characters, exact `CORS_ORIGINS`, and optional LLM config.
3. Run API and scheduler; PostgreSQL advisory lock elects exactly one scheduler leader. SQLite development remains single-worker only.
4. Verify `GET /api/v1/health` from the private network.
5. Start a world explicitly. A paused world never runs in the scheduler.
6. Smoke test manual 1-step/10-step operations, events, state persistence after restart and approval gates.

## Observability

Current: structured event types stored with timestamp, world/agent references and limited event details; basic health, world KPIs, and logs from the worker. Missing: centralized immutable audit store, metrics exporter, traces, alerts and SLO policies.

## Backup/restore

For production Postgres, configure automated backups and perform a **tested** restore into staging with schema migration compatibility. Keep API keys out of snapshots. Do not rely on local SQLite for production durability.

## Rate & cost controls

Set `MAX_MODEL_CALLS_PER_WORLD` and `LLM_ALLOWED_MODELS`; use provider-side hard spending limits. The current call-count cap is not a dollar-cost cap. Model calls run while the world transaction is held; before high load, move external model inference into a leased work queue with optimistic revalidation and bounded retries.

## Critical release blockers

- Per-user authentication/authorization with real tenancy and role-bound approvals.
- Distributed-safe scheduling and queue-driven provider calls.
- Real PostgreSQL/container integration test, network policies, resource quotas, load test and backup drill.
- Strong observability, data privacy and retention controls.
- Approved webhook receiver with idempotency enforcement and signed receipt verification.
- Comprehensive LLM red-team campaigns and review of legal/regulatory implications for the intended operational domain.

**Do not route money transfers, emergency response, physical equipment control, patient records, or irreversible external operations through this current reference build.**
