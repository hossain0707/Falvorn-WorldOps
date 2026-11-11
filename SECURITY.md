# Security policy

Falvorn WorldOps is a **controlled multi-agent simulation and action-approval prototype**. It is not an autonomous executor with arbitrary host, browser, or external service privileges. No claim of security certification or regulatory compliance is made.

## Deployment boundary

- Never expose the built-in dashboard or API to the open Internet solely behind a shared API key. Put the service behind TLS, VPN/private network access, and a managed OIDC reverse proxy or equivalent identity-aware perimeter.
- The write key (`API_KEY`) provides full control over all worlds and approvals. `READ_ONLY_API_KEY` is optional and can read all world data; **neither key provides tenant isolation**. Use long independently generated secrets and rotate them if disclosed.
- In production, no anonymous world endpoints are accepted. Key-derived pseudonyms, not self-declared JSON fields, identify the reviewer in the audit trail. This is not a replacement for per-user authentication, approval separation of duties, or tamper-resistant logs.
- Outbound actions require an operator's approval **and** a second dispatch request. Only a single operator-configured HTTPS destination is supported. Agents cannot supply URLs; receivers must verify HMAC, enforce idempotency and apply their own authorization.
- Prompt injection in untrusted memory or feeds is not proven impossible; all model outputs must still pass the server-side allowlist. Never enable new powerful action types without independent authorization design, test coverage and scoped privileges.

## Responsible reporting

Report suspected vulnerabilities privately to the repository owner via GitHub's private vulnerability reporting feature if enabled, or a private contact channel. Do not publish exploit steps, private data, credentials or attack traffic on public issues. Avoid testing against systems without permission.

## Supported release

The repository currently provides an internal/research foundation only; there is no public SLA or security-update commitment. See `docs/OPERATIONS.md` for deployment restrictions and rollout gates.
