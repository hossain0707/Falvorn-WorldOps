"""Operator-reviewed outbound action gateway. No user-supplied destinations or arbitrary tools."""
import hashlib
import hmac
import json
import httpx
from app.core.config import get_settings

class GatewayError(Exception): pass

def dispatch_approved(approval):
    cfg = get_settings()
    if approval.action_type not in {'publish_summary','create_ticket'}:
        raise GatewayError('Unsupported connector capability')
    if not cfg.webhook_url:
        raise GatewayError('WEBHOOK_URL not configured; approval remains safe and undispatched')
    if not cfg.webhook_url.startswith('https://') or len(cfg.webhook_signing_secret) < 24:
        raise GatewayError('Webhook needs HTTPS and a strong signing secret')
    # Destination comes ONLY from operator-controlled environment, not the agent payload.
    body = json.dumps({'id': approval.id, 'type': approval.action_type, 'payload': approval.payload},
                      sort_keys=True, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(cfg.webhook_signing_secret.encode(), body, hashlib.sha256).hexdigest()
    try:
        with httpx.Client(timeout=8.0, follow_redirects=False) as client:
            r = client.post(cfg.webhook_url, content=body, headers={
                'Content-Type': 'application/json', 'X-WorldOps-Signature': f'sha256={signature}',
                'Idempotency-Key': approval.id,
            })
            r.raise_for_status()
            return str(r.headers.get('X-Request-ID', f'http-{r.status_code}'))[:200]
    except httpx.HTTPError as exc:
        raise GatewayError(f'Connector failure: {type(exc).__name__}') from exc
