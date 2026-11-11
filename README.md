# Falvorn WorldOps

**Independent, governed multi-agent simulation and operational sandbox**  
**Release: 0.2.0 — internally tested foundation for controlled pilots; not certified for public or high-stakes production use.**

An original implementation motivated by the engineering questions in [*Emergence World: A Platform for Evaluating Long-Horizon Multi-Agent Autonomy*](https://arxiv.org/abs/2606.08367) (2026) and [*Emergence World: Adversarial Stress-Testing of Long-Horizon Multi-Agent Systems*](https://arxiv.org/abs/2609.17320) (2026). Source reference: [EmergenceAI/Emergence-World](https://github.com/EmergenceAI/Emergence-World).

**Independence and licensing:** This repository does **not** bundle, fork or reproduce the Emergence AI repository's agent profiles, datasets, architecture files or other licensed assets. Those are released under research-only CC BY-NC terms; commercial use of that content requires separate permission. We use high-level scientific ideas and independently authored software, personas, world layout, and test scenarios. This is not a faithful research replication and does not claim the published results.

## At a glance

| Area | Stack / boundary |
|---|---|
| API | Python 3.11+, FastAPI + Pydantic; `/api/v1` OpenAPI |
| Persistence | PostgreSQL + SQLAlchemy + Alembic; SQLite development only |
| Dashboard | Browser-native HTML/CSS/ES modules; no Node build required |
| AI engine | Reproducible heuristic agent; opt-in OpenAI-compatible provider behind allowlist |
| Execution | Transactional world actions + server-side invariant enforcement |
| Real-world effects | Human-reviewed, manually dispatched, HMAC-signed HTTPS webhook only |
| Auth | Distinct admin and optional read-only keys for **private** deployments; edge OIDC/VPN required |
| Worker | PostgreSQL advisory leader election; not yet a distributed LLM queue |
| Licenses | Proprietary original code, all rights reserved; research referenced but not copied |

## What runs now

- **Persistent world state:** transactional turn progression, worlds, fictional agent populations, places, credits, energy, conversations, social trust, governance proposals/votes, memory provenance, and append-only events.
- **Model adapters:** reproducible heuristic agents at zero API cost, with an opt-in *OpenAI-compatible* chat completion adapter for specifically server-allowed model IDs. A provider adapter is not proof that the named model is available; configure a working provider endpoint/API key first.
- **Two environments:** town/research sandbox and workplace simulation.
- **Operator control:** create/start/pause worlds, manual and scheduled turns, add agents, inspect memories and statistics, inject untrusted test messages, perform audited test actions.
- **Safety envelope:** tool/action allowlists; input constraints; untrusted source labels; server-side safety invariant enforcement; signed human-approved-only outbound webhook; no arbitrary code/shell/browser/network execution by agents; status transitions audited.
- **Visibility:** live-refresh web control room with an isometric visualization, activity feed, agent inspection and approval management; OpenAPI at `/docs`.
- **Deployment foundations:** versioned Alembic migration, PostgreSQL deployment database, leader-elected worker, nonroot/read-only API containers, environment validation, reverse-proxy-ready API, and tests.

## Structure

```text
backend/
  app/
    api/            REST request parsing, authorization and lifecycle
    core/           environment, database/session settings
    domain/         persistence models and validated schemas
    services/       transactional engine, LLM strategy, metrics, safety gateway, seeds
    evaluations.py  independent red-team/control study runner
    worker.py       single-replica scheduler
  alembic/          checked-in initial schema migration
  tests/            HTTP, governance, safety and invariant tests
  pyproject.toml
frontend/
  index.html        control room shell
  src/             isolated ES modules and responsive styling
infra/
  docker-compose.yml
  .env.example

docs/
  ARCHITECTURE.md
  THREAT_MODEL.md
  OPERATIONS.md
  DEPLOYMENT.md
  RELEASE_CHECKLIST.md
  API.md
```

## Run locally (development)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open **http://127.0.0.1:8000**. Click **New world**, use the built-in heuristic agents, then **+10 turns**. An API key is not required in local development only. The browser UI is served by the API; opening `frontend/index.html` directly without the server will not work.

Background turns (optional, *separate terminal*, single instance only):

```bash
cd backend
python -m app.worker
```

The worker advances only worlds that an operator started. World state is persisted in the database across restarts. The worker uses a PostgreSQL advisory lock to elect a single scheduler leader. It is **not** a multi-replica distributed inference queue. Do not run multiple SQLite workers.

## Deploy via Docker Compose (controlled private environment)

Create `infra/.env` from `infra/.env.example` and set a strong `POSTGRES_PASSWORD`, random 32+ character `API_KEY` (plus optional distinct `READ_ONLY_API_KEY`), and the precise public `CORS_ORIGINS`. For the Compose database URL, generate hexadecimal passwords to avoid reserved URI characters.

```bash
cp infra/.env.example infra/.env
# Edit infra/.env with strong secrets; never commit it
# Run from repository root:
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build -d
docker compose --env-file infra/.env -f infra/docker-compose.yml ps
```

Services: `db` → `migrate` → `api` and `worker`. The API binds to `127.0.0.1:8000`. Place it **behind HTTPS, authentication and network access controls** (VPN or OIDC reverse proxy). Do not expose this key-only dashboard directly to the public internet. For public multi-user SaaS, replace single admin API key with OIDC session auth, tenant-level RBAC, rate limiting and a distributed worker/queue before launch.

## Enable an LLM-backed agent

In `backend/.env` (local) or your deployment's environment:

```dotenv
LLM_API_KEY=your_server_side_provider_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_ALLOWED_MODELS=gpt-4.1-mini,gpt-4o-mini
```

Then add an agent with `provider = openai_compatible`, `model = gpt-4.1-mini`. API credentials are never exposed to agents or the frontend. All LLM output is parsed as **untrusted proposed actions** and revalidated by the backend. If an LLM call fails, a model-fallback event is created and the safe deterministic policy is used. This prototype currently has **one** OpenAI-compatible HTTP adapter; native Anthropic, Google and xAI APIs are not implemented.

## Real-world action gateway

Outbound side effects are **off by default**. In a `workplace` world an agent may only request a `publish_summary` or `create_ticket` action. It becomes a `pending` approval. An operator must explicitly approve and then separately **dispatch** it. The dispatcher posts a JSON payload to a **single server-configured HTTPS webhook** with `X-WorldOps-Signature: sha256=...` (HMAC-SHA256 over the canonical JSON body) and `Idempotency-Key` equal to the approval UUID. The receiving service should verify both and deduplicate on the key. Agent-provided URLs are impossible.

```dotenv
WEBHOOK_URL=https://your-controlled-action-gateway.example.com/actions
WEBHOOK_SIGNING_SECRET=your-long-random-secret-32-chars
```

This is not a general-purpose connector marketplace. In production, implement destination-specific payload schemas, permissions and dry-run support for each additional real action.

## REST examples

```bash
# Development mode (no key); in production pass -H 'X-API-Key: ...'
curl -X POST http://localhost:8000/api/v1/worlds \
  -H 'Content-Type: application/json' \
  -d '{"name":"Operations Lab","scenario":"workplace","starter_agents":true,"seed":42}'

curl -X POST http://localhost:8000/api/v1/worlds/WORLD_ID/steps \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: my-step-batch-001' \
  -d '{"count":20}'
```

Other endpoints are discoverable at `/docs`.

## Test and evaluate

```bash
cd backend
pytest -q
python -m app.evaluations --turns 160 --seed 42 --output evaluation.json
cd ../frontend && npm run check       # syntax checks; no npm dependencies
```

The evaluator creates two **heuristic** worlds with identical seeds, one with adversarial *untrusted* feed events, checks policy invariants, and reports comparable metrics. This **does not** replicate the original papers' LLM experiments or reproduce their multi-day findings.

## Operational limitations and release gates

This is a tested reference build **ready for internal experiments**, **not yet a publicly certified production SaaS**. Before real users or connected high-impact tools: integrate SSO/OIDC+tenant RBAC, production audit sinks and alerting, distributed queue with bounded inference, per-tenant budgets and rate limits, encrypted backups and restore drills, operational data retention/deletion, webhook receiver security review, LLM policy/red-team evaluation, and real PostgreSQL/container deployment and load tests. No external provider accounts have been connected and no real-world actions have been dispatched during development.

See [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md), [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), [`docs/OPERATIONS.md`](docs/OPERATIONS.md), [`docs/API.md`](docs/API.md) and [`SECURITY.md`](SECURITY.md) for validation and release gates. GitHub Actions are intentionally **not enabled**; all checks are local/manual.

## Ownership

Original code authored for Falvorn AI; **all rights reserved** unless the owner chooses a license. Research citations and third-party terms remain with their respective holders.
