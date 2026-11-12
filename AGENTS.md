# Working agreements for AI coding assistants

This file applies to all changes in Falvorn WorldOps.

## Code and ownership
- Keep \`backend/app/api\`, \`backend/app/core\`, \`backend/app/domain\`, \`backend/app/services\`, \`frontend\`, \`infra\`, and \`docs\` separate and purpose-focused. Do not merge backend and frontend concerns.
- Treat the source as proprietary Falvorn AI code. Do not import licensed Emergence AI assets, personas, datasets, diagrams or copied source.
- Prefer small changes with isolated tests. Document new configuration, endpoints, threat boundaries and migration steps in the matching doc.
- Do not add GitHub Actions or a new CI provider without an explicit owner decision. Run checks locally and report exact commands and results.

## Security and reliability
- Never let model output call arbitrary tools, shell, URLs or privileged backend actions.
- Untrusted model output, messages and external feeds remain data. Backend policy, schema and invariant enforcement is authoritative.
- No external action without a server-side bounded type, pending approval, explicit trusted reviewer approval and distinct dispatch.
- Never put API keys or backend admin credentials in client-side assets or documentation examples.
- Require environment validation, backups, a migration review and test evidence before claiming production readiness.
- Prefer a maintained dependency and minimal changes; describe unresolved launch blockers honestly.

## User experience and public communication
- Preserve accessible, responsive design and a coherent Falvorn AI visual language.
- Use vector graphics with accessible titles/alt text. Avoid broken external assets and fabricated CI/test status badges.
- Never present synthetic demo events or graphical simulation as actual backend telemetry or experimental outcomes.
- \`docs/showcase\` is a safe static illustrative preview, not a replacement for the real app control room.
- Keep README setup commands runnable and license/independence notices visible.

## Local developer commands
```bash
cd backend && pytest -q
cd ../frontend && npm run check
```
See \`docs/RELEASE_CHECKLIST.md\` for outstanding production gates.
