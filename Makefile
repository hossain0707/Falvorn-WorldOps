.PHONY: test check evaluate smoke

test:
	cd backend && python -m pytest -q

check:
	cd backend && python -m compileall -q app
	cd backend && python -m pytest -q
	cd frontend && node --check src/api.js && node --check src/main.js && node --check src/render.js

evaluate:
	cd backend && python -m app.evaluations --turns 160 --seed 42 --output ../docs/sample-evaluation.json

smoke:
	bash scripts/smoke.sh
