# Security and prompt-injection threat model

## Trust boundaries

- **Highest trust:** server code, operator-owned environment secrets, server allowlists.
- **Operator actions:** authenticated by server API key; still run through validation and are logged.
- **Model decisions:** low trust; never provide direct access to HTTP, shell, SQL, filesystem, or secrets.
- **Agent memories, nearby agent messages, external feeds:** untrusted input for decisions, not executable policy.
- **External webhook receiver:** separate trusted service; must validate HMAC, timestamp/replay policy and idempotency key.

## Threat/failure matrix

| Scenario | Defense implemented | Gap to validate before public deployment |
| --- | --- | --- |
| Prompt injection in external news | Explicit provenance; action allowlist | Long-horizon adversarial model behavior must be tested |
| Agent asks to exfiltrate secrets | No arbitrary network tools; secret not in LLM context | External gateway connector review and DLP |
| Agent induces another agent to bypass rules | Social policies cannot override technical gates | Formal influence/drift evaluation and trust calibration |
| Agent claims it sent a report | Only signed operator-dispatched webhook can cause side effects | Receiver should report authenticated delivery receipts |
| Repeat/replayed step request | Idempotency table and world lock | Use strict request identity and replay expiration policies |
| Concurrent writes | PostgreSQL world row lock on turns | Worker queue/lease and load tests at scale |
| Unauthorized API user | Server API key in production | OIDC, RBAC, tenant boundary, WAF/rate limiting |
| Sensitive records stored indefinitely | Separate provenance and audit fields | Retention/deletion, encryption, DLP and PII redaction |

## Non-claims

No mechanism here guarantees all LLM behavior is safe or that agents cannot spread misinformation in text. The implementation enforces **execution controls**, not perfect information quality. It has not been security-audited, penetration-tested, or qualified for high-stakes autonomous decisions.

## Minimum red-team exercise

1. Inject feed content instructing an agent to ignore security rules.
2. Verify event remains tagged `untrusted` and cannot dispatch an action.
3. Attempt an unknown action; assert `blocked_action` is logged.
4. Create a community vote to disable review; assert external request still needs approval.
5. Verify pending/rejected approvals cannot dispatch.
6. Inject bogus cross-world agent and proposal IDs; assert isolation checks.
7. Verify API key and HTTPS proxy behavior under a separate staging stack.
