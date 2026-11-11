# Controlled private deployment walkthrough

1. Copy `infra/.env.example` to `infra/.env`. Use **hexadecimal** secrets generated locally; avoids special characters that would need URL-encoding in the Compose database URL:

   ```bash
   python -c 'import secrets; print(secrets.token_hex(32))'
   ```

   Generate **different** hex secrets for `POSTGRES_PASSWORD`, `API_KEY`, `READ_ONLY_API_KEY` (optional), and webhook HMAC signing secret. Do not commit `.env`.
2. Provision persistent storage and put the service on a private host. Restrict ingress to localhost as configured. Use HTTPS and an identity-aware reverse proxy or VPN.
3. Run `docker compose --env-file infra/.env -f infra/docker-compose.yml config` to validate YAML, then `docker compose --env-file infra/.env -f infra/docker-compose.yml up --build -d`. The migration job runs before API/worker startup.
4. From the host, run `make smoke` and use the browser dashboard on the private endpoint. Verify key-based access and review gates. Never put API keys in frontend source or screenshots.
5. Configure automated PostgreSQL backups, retention, restoration tests, resource limits and logging. Verify recovery after crashing the API and worker. Do not expose outbound webhook destinations before reviewing and testing the receiver.
6. For upgrades, back up the database, test migration on a restored staging copy, and roll out API+worker together. A schema downgrade may require manual data rollback and is not guaranteed reversible.

The compose configuration uses a **single database service** without HA. It is appropriate only for controlled pilots after owner-side infrastructure validation, not a turnkey hosted SaaS. Public launch requires `OPERATIONS.md` gates to be closed. The supplied worker elects a PostgreSQL leader but still makes synchronous provider calls inside transactions; high-load operation requires a queued redesign.
