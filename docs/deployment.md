# Web/backend deployment draft

**Status:** repository-only work, paused. The Python package can be released
independently. Containers have not been built locally (Docker is unavailable),
PostgreSQL integration and runner recovery are not verified, and browser tests
need attention. This document records the intended setup for when work resumes.

## Components

- **web:** Bun + SvelteKit, exposes port 3000 to Coolify's proxy. /api requests are
  proxied to the internal API so browser sessions use one public origin.
- **api:** FastAPI, port 8000 internally. Owns OAuth sessions, project ownership,
  validation, preview, export, drafts, published revisions and credential storage.
- **database:** PostgreSQL 18 with a named persistent volume. No public port.
- **migrate:** one-shot Alembic upgrade before API/runner startup.
- **runner:** optional `hosting` Compose profile. Runs one child per bot, bounded
  by MAX_HOSTED_BOTS, with leased ownership and heartbeat supervision.

The API never starts a Discord gateway client. The pilot is restricted to the
configured HOSTED_OWNER_ID. It is not a public multi-tenant hosting service.

## Environment

Copy names from .env.example into Coolify environment settings, keeping production
values out of Git. Required values are PUBLIC_ORIGIN (HTTPS), POSTGRES_PASSWORD,
ENCRYPTION_KEY, DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET. Use a URL-safe database
password in the Compose URL. Set HOSTED_OWNER_ID to the Discord user ID allowed
to publish, and MAX_HOSTED_BOTS to a small tested limit (default 3).

Create an encryption key with:

```sh
.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Keep that key securely backed up separately from the database. Existing tokens
cannot be recovered without it. The API and runner must use the same key.
Development's automatic ephemeral key is unsuitable for stored hosted credentials.
Configure the OAuth callback as `PUBLIC_ORIGIN/api/auth/callback`. Discord OAuth
identifies the human; a separate bot token is required to host their bot.

## Coolify

Create a Docker Compose resource using compose.yaml. Route the public HTTPS domain
to web port 3000 only; leave API, database and runner private. Supply required
variables and verify health checks, migrations, memory limits and persistent
storage. To enable the pilot runner, enable the `hosting` profile in the actual
Compose deployment (or remove that profile declaration in a reviewed deployment
configuration). Do not mount a Docker socket into the API.

For a local container rehearsal with production-style settings:

```sh
docker compose config --quiet
docker compose up --build -d
docker compose --profile hosting up --build -d
```

Run the export-only services first; enable hosting only after configuring the
owner and exercising a test application. Verify stop, token removal/rotation,
publish, rollback, forced termination and recovery before inviting public users.
No deployment has been performed by the repository preparation steps.

## API surface

| Route | Purpose |
| --- | --- |
| GET /api/health | Database health |
| GET /api/config, /api/schema, /api/templates | Public editor configuration/contracts/templates |
| POST /api/validate, /api/preview, /api/export | Validate, simulate or download a portable definition |
| GET /api/auth/login, /api/auth/callback | Discord OAuth |
| GET /api/auth/me; POST /api/auth/logout | Current session and logout |
| POST /api/auth/dev | Explicit development-only login |
| GET/POST /api/projects | Owned project listing/creation |
| GET/PUT/DELETE /api/projects/{id} | Owned draft read, optimistic save, stopped-project deletion |
| PUT/DELETE /api/projects/{id}/credentials | Encrypt/rotate or remove bot credentials |
| POST /api/projects/{id}/publish, /stop, /rollback | Owner-pilot lifecycle operations |
| GET /api/projects/{id}/revisions, /events | Revision history and generic runner activity |

Authenticated writes require a session, matching Origin and X-CSRF-Token.
Credential values are never returned or included in exported definitions. Drafts
and immutable published revisions are separate. The full request models are in
FastAPI /docs when the API is running and in schema/openapi.json after generation.

## Backups and restore rehearsal

Database backup (keep the file outside Git):

```sh
docker compose exec -T database pg_dump -U botmaker -d botmaker -Fc > botmaker-backup.dump
```

Test restore into a separate disposable database before relying on backups. With
that disposable database created and access configured:

```sh
pg_restore --no-owner --dbname YOUR_DISPOSABLE_DATABASE_URL botmaker-backup.dump
```

Verify projects, revision counts and encrypted credential decryption with the
separately retained key, using a test application. Document a successful restore
before production hosting. A database dump alone is not a validated backup plan.

## Outstanding acceptance checks

Browser workflows; PostgreSQL transactional behavior under concurrent saves and
publishes; stale-runner fencing and shutdown under database failure; application
ID/token correctness; resource/tenant isolation; container build/runtime checks;
OAuth against the real callback domain; migrations/backup restoration and a live
end-to-end publish/rollback smoke test. The implementation plan has more detail.
