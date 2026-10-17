# Web deployment to Coolify

**Status:** local web development is active and the Python prerelease is published.
The editor is prepared for an export-first deployment, with optional Discord
login for saved projects. Containers have not been built locally (Docker is
unavailable); CI now builds both images. PostgreSQL deployment, live OAuth and
runner recovery still need verification in the actual environment.

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
configured HOSTED_OWNER_ID and also requires ENABLE_HOSTING=1. It is not a public multi-tenant hosting service.

## Environment

Copy names from .env.example into Coolify environment settings, keeping production
values out of Git. Required values are PUBLIC_ORIGIN (HTTPS), POSTGRES_PASSWORD,
and ENCRYPTION_KEY. Use a URL-safe database password in the Compose URL.
Leave DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET empty to launch without login: the
builder, local drafts, preview, and export work anonymously. Supply both OAuth
values only when enabling cloud-saved projects. Local sign-in is prohibited in
production. Keep ENABLE_HOSTING=0 for this launch. The owner pilot requires a
separate explicit opt-in, HOSTED_OWNER_ID, OAuth, and a small MAX_HOSTED_BOTS limit.

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
storage. To enable the experimental pilot runner after separate integration testing, set
ENABLE_HOSTING=1 and enable the `hosting` profile in the actual
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
SvelteKit 3 requires the public origin at build time (`paths.origin`). Compose
passes PUBLIC_ORIGIN into the web Docker build. Changing the domain requires a
rebuild. The old runtime-only ORIGIN setting is insufficient.

No deployment has been performed by the repository preparation steps.

## Login decision

Login is optional for building, previews, local browser drafts and exports. Use
Discord OAuth when you want projects stored under individual accounts across
devices. OAuth requests only the identify scope and does not grant bot access.
Do not add password registration or expose the development account in production.
The optional hosted runner is a separate feature and stays disabled by default.

## Production defenses

The web server emits a nonce/hash-based script CSP, blocks framing and plugins,
and sends nosniff, no-referrer, permissions policy, and HTTPS HSTS headers.
Inline styles remain allowed for the flow canvas; inline scripts do not. API
responses are not cached. Mutations require the configured Origin; authenticated
mutations also require the session CSRF token. Sessions are stored as hashes,
with HttpOnly, Secure, SameSite=Lax cookies in production.

Bodies are capped at 256 KiB during streaming at the web proxy and API. The web
process limits API traffic to 120 requests per minute per observed client address
and login/callback traffic to 20. Counters are bounded and process-local, not a
distributed rate limit. Behind Coolify, addresses default to the connecting proxy;
configure adapter-node ADDRESS_HEADER/XFF_DEPTH only after verifying which header
your trusted proxy overwrites. Without that configuration, the limit is shared
by clients behind that proxy. Do not expose port 3000 directly when trusting
forwarded client-address headers. Add proxy-level limits for larger deployments.

Only the web service has a public domain. API and PostgreSQL have no host port
mappings. Containers run as non-root, with capability dropping and read-only
filesystems for API/web; the backend image installs only server dependencies.
Production API docs are disabled; editor schemas remain public.

## First deployment checks

1. Set PUBLIC_ORIGIN, POSTGRES_PASSWORD and ENCRYPTION_KEY in Coolify; keep
   ENABLE_HOSTING=0 and ALLOW_DEV_LOGIN=0. Generate secrets outside Git.
2. Deploy compose.yaml, pointing your HTTPS domain at web port 3000.
3. Confirm migrations and all three service health checks pass.
4. Build a bot anonymously, preview it, export it, and run the export locally.
5. Verify the shared link preview uses your HTTPS domain.
6. If enabling login, configure the Discord redirect URL and test sign-in,
   saving, sign-out and ownership between two different accounts.
7. Rehearse backup/restore before relying on stored projects.

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

Real Discord OAuth callback and hosted browser workflows; PostgreSQL transactional behavior under concurrent saves and
publishes; stale-runner fencing and shutdown under database failure; application
ID/token correctness; resource/tenant isolation; container build/runtime checks;
OAuth against the real callback domain; migrations/backup restoration and a live
end-to-end publish/rollback smoke test. The implementation plan has more detail.
