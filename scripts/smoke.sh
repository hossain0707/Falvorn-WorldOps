#!/usr/bin/env sh
set -eu
BASE="${WORLDOPS_BASE_URL:-http://127.0.0.1:8000}"
# Liveness is anonymous; readiness checks the database. Never log the API key.
python - "$BASE" <<'PY'
import json,sys,urllib.request
base=sys.argv[1].rstrip('/')
for path in ('/api/v1/live','/api/v1/health'):
    with urllib.request.urlopen(base+path,timeout=5) as res:
        payload=json.load(res)
        assert payload.get('status')=='ok',payload
        print(path,':',res.status,payload['status'])
PY
