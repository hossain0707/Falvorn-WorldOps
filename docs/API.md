# HTTP API (v1)

**Prefix:** `/api/v1`; interactive OpenAPI available under `/docs` on a running instance. The API returns JSON and standard HTTP status codes.

Authentication: `X-API-Key: <API_KEY>` for all world operations in production. Optional `READ_ONLY_API_KEY` can access **GET** world endpoints but never POST mutations. Keys are opaque and must travel over TLS in actual deployments. GET `/api/v1/live` and `/api/v1/health` require no credentials.

| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/live` | Process liveness |
| GET | `/health` | Database readiness |
| GET | `/meta` | Supported landmarks, adapter flags |
| GET / POST | `/worlds` | List / create worlds |
| GET | `/worlds/{id}` | View world state |
| POST | `/worlds/{id}/start` or `/pause` | Scheduler lifecycle |
| POST | `/worlds/{id}/steps` | Atomic batch of 1–20 turns, optional `Idempotency-Key` |
| GET / POST | `/worlds/{id}/agents` | List / add allowed agents |
| GET | `/worlds/{id}/agents/{agent_id}/memories` | Provenanced memory read |
| GET | `/worlds/{id}/events?after=&limit=` | Paginated event feed |
| GET | `/worlds/{id}/metrics` | World counters, policy health |
| GET | `/worlds/{id}/proposals` | Community text proposals |
| POST | `/worlds/{id}/feed` | Operator injection of *untrusted* content |
| POST | `/worlds/{id}/agents/{agent_id}/action` | Operator-approved simulation action test |
| GET | `/worlds/{id}/approvals` | Approval queue |
| POST | `/worlds/{id}/approvals/{approval_id}/approve` | Mark as approved; reviewer derived from API key |
| POST | `/worlds/{id}/approvals/{approval_id}/reject` | Reject; reviewer derived from API key |
| POST | `/worlds/{id}/approvals/{approval_id}/dispatch` | Send approved action to configured HMAC webhook |

Sample POST:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/worlds -H 'Content-Type: application/json' \
  -H "X-API-Key: $API_KEY" -d '{"name":"Pilot World","scenario":"workplace","seed":42}'
```

**Error codes:** 401 unauthenticated; 403 read-only key attempting mutation; 404 resource not found; 409 state conflict or replayed key with changed input; 422 request validation; 502 outbound connector failure. All runtime side effects remain behind the HMAC webhooks with separate receiver authorization; there is no generic shell/network access for agents.
