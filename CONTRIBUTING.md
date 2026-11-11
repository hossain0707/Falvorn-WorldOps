# Contributor guide

All source is proprietary to Falvorn AI unless otherwise authorized. Submit changes only with the right to contribute your code. External pull requests do not imply a license grant.

## Layout

- `backend/app/api`: HTTP entrypoints and auth boundary
- `backend/app/domain`: persisted entities and validated input schemas
- `backend/app/services`: simulation policies, model adapters, audited action gateway
- `backend/app/core`: environment and persistence configuration
- `frontend`: browser UI, plain ES modules, CSS; keep independent from Python modules
- `infra`: deployment definitions
- `docs`: architecture, threat model, operational procedures and API contracts

## Local checks

```bash
cd backend
python -m pip install -e '.[dev]'
python -m pytest -q
python -m compileall -q app
cd ../frontend
node --check src/api.js && node --check src/main.js && node --check src/render.js
```

Set up secrets through local `.env` only. No real external webhooks, cloud API keys or production data should be used for tests. New API inputs need Pydantic validation and negative tests. New agent actions need deterministic enforcement in `apply_action` and an explicit threat-model update. Database changes require a versioned Alembic migration. Keep commits focused (e.g. `feat:`, `fix:`, `docs:`, `test:`, `security:`).

## Review expectations

Do not merge changes with failing local tests or without explaining security implications, migration/rollback procedure, cost limits, and an operator validation checklist. This repository intentionally does **not** include GitHub Actions; testing is local/manual until the owner authorizes CI.
