# Discord Bot Maker v2

## Recommendation

Build a Python library and a visual web editor around the same versioned bot
definition. This fits the existing project's purpose and the surrounding app
family. Start with exportable, self-hostable bots; introduce hosted execution
through an owner-only pilot before accepting public users' bot tokens.

The editor and the always-on hosting service are separate deliverables. A useful
builder can ship before operating a public bot hosting platform.

## Current project and modernization baseline

The repository is a Python 1.0.0 package with one DBot wrapper, an unfinished
Command class, and committed distribution/egg-info artifacts. There is no web
app, API, database, authentication, container configuration, or test suite.

Existing dependencies: discord (unversioned), setuptools >=42, wheel (unversioned).
PyPI registry checked on 2026-10-17: discord.py 2.7.1 and setuptools 84.0.0.
Use discord.py directly, declare the runtime requirement in package metadata,
pin it for local installs, and use current setuptools. Remove the redundant wheel
build dependency; current setuptools supplies wheel building itself.

The first compatibility patch adds required intents, replaces removed avatar_url,
handles DMs and uncategorized channels, ignores bot-authored messages, and avoids
starting the bot when a context manager exits with an exception. Prefix commands
still need Message Content Intent enabled in the Discord Developer Portal.
Local Python minimum becomes 3.10; validate the final v2 Python support matrix in CI.

Remaining migration work: move setup.py metadata into pyproject.toml, choose a v2
prerelease version, replace the incomplete Command class, migrate examples, remove
tracked generated artifacts in a deliberate cleanup, and document API differences.
Do not publish the modified code as the existing 1.0.0 release.

Update after the naming pass: metadata now lives in pyproject.toml, the checkout
is 2.0.0a1, Command is an immutable dataclass, and README/examples use the new API.
Generated-artifact cleanup and live verification remain outstanding.

## Naming conventions

Keep **Discord Bot Maker** as the product name, `discord-bot-maker` as the
distribution/repository name, and `discord_bot_maker` as the Python import.
Do not introduce a separate brand for each delivery format or assume a new PyPI
name is available. Use “Python library” and “Visual builder” for the two entry points.

The canonical Python API is `Bot(token=..., prefix=...)`, `add_command()`,
`run()`, `client`, and immutable `Command` definitions. Use snake_case methods
and explicit fields: `name`, `reply`, `description`, `image_url`, `help_text`.
Keep documented DBot compatibility wrappers during migration.

In the visual builder, use **Bot**, **Command**, **Trigger**, **Condition**,
**Reply**, **Embed**, **Preview**, **Draft**, and **Published version** consistently.
Call a Discord guild a **server** in user-facing text. Preview simulates a reply;
Publish activates a saved version in hosted mode; Export downloads a runnable
definition. Do not label these different actions “Deploy.” Use generic service
names `web`, `api`, `runner`, and `database` in Compose. A future shared graph
model can be called `BotDefinition`; keep it distinct from today's `Bot` client.

## Design findings from the four local apps

| App | Local evidence | Carry into the builder |
| --- | --- | --- |
| aaryandehade.com | aaryandehade/src/routes/layout.css and home components | Figtree; sage light theme; black dark theme; orange and blue accents |
| shalendar | src/routes/layout.css and +page.svelte | Pill navigation and actions; rounded translucent panels; bold headings; split introduction and creation form |
| apps.aaryandehade.com | index.html | Compact family branding with orange period; glass cards; warm text; restrained hover effects |
| pollish | src/lib/styles.css, +layout.svelte, +page.svelte | Shared dark/light palette, theme toggle, product preview beside creation form, accessible focus and reduced motion |

Shared tokens: Figtree; accent #ff7a30; dark canvas #000; text #e9e3df;
muted #aaa29d; light canvas #cfd5c5; secondary blue #465c88.
These findings come from source inspection, not a rendered browser audit.

Landing page: family pill header, concise headline, a working example flow and
one primary action, “Build a bot.” Provide “Python library” as a secondary path.
Use the ambient orange glow and grain on the landing page. Keep the editor
background static and subdued so connectors and validation states stay legible.

Editor desktop layout:

```text
Bot name / saved state             Preview | Export | Publish
Triggers & actions | Flow canvas             | Selected block settings
                   | /hello -> Reply         | Message / embed / variables
                   |                         | Discord-style response preview
                   | Validation and test trace
```

Use custom themed nodes, clear connection handles, undo/redo, explicit saved
state, inline validation, keyboard actions, and a list/form alternative to dragging.
On mobile use a sequential flow list and settings sheets; avoid squeezing three
desktop panels onto a phone. Use orange for primary actions and selection, with
labels/icons as well as color for success and error states.

## Architecture

```text
SvelteKit editor -- /api --> FastAPI -- PostgreSQL
                                |
                     versioned bot definitions
                                |
                     Python core + discord.py
                                |
                   separate supervised bot runner --> Discord

PyPI users --> same Python core + local token --> Discord
```

Suggested monorepo:

```text
src/discord_bot_maker/   # publishable library: models, validation, engine, CLI
apps/api/               # FastAPI: sessions, projects, revisions, exports
apps/runner/            # supervised execution using the library
apps/web/               # SvelteKit, TypeScript, Svelte Flow, Tailwind, Lucide
examples/               # Python usage and JSON bot definitions
tests/                  # core, API, runner and schema contract tests
compose.yaml
```

Keep the library independent of FastAPI, the database, and hosted login. API and
runner dependencies belong in separate dependency groups or app manifests.
Use Bun for web tooling, commit bun.lock and packageManager, and use frozen
installs in CI and Docker. Resolve latest stable versions at implementation time,
check peer compatibility, and lock the tested graph; neighboring package versions
are references, not proof of current registry versions. Use a Python lockfile for
deployments while keeping the published library's compatible dependency ranges.

Use Pydantic models as the definition authority; export JSON Schema and generate
frontend types. FastAPI exposes OpenAPI for the API client. Bot definitions need
schema_version, stable IDs, triggers, typed action nodes, control edges, and
separate editor layout metadata. Tokens never belong in definitions or exports.

Both Python helpers and the editor produce the same definition. The engine
interprets that validated definition; do not execute generated user Python on
the server. Export a JSON definition plus a small Python launcher that loads it.
This makes import/export lossless without promising arbitrary Python round trips.

Validate supported node types, fields, Discord limits, variable names, reachable
nodes, connection types and acyclic control flow. Enforce action/time budgets.
Preview runs the same engine against a simulated Discord adapter and returns a
trace; live execution supplies the Discord adapter. Keep command synchronization
an explicit publish operation, with development-guild support.

## Initial feature scope

Include slash commands, optional legacy prefix commands, text and embed replies,
variable insertion, role/channel conditions, cooldowns, and reusable templates.
Use a small typed graph: command trigger -> optional condition -> reply/embed.
Support true/false branches with explicit labels. Start with greeting, rules and
FAQ templates. Preserve existing reply/reply2/image/emoji/help concepts through
an importer and a documented DBot compatibility layer where practical.

Defer arbitrary scripts, HTTP requests, plugin installation, music, moderation,
loops, scheduled workflows, payments, collaboration and a marketplace. Each adds
execution or operational requirements beyond the original product.

## Hosting and security decisions

Phase one exports bots to run on the user's infrastructure. Phase two hosts the
owner's bots on the VPS; public multi-user hosting follows only after runner
quotas, recovery and tenant isolation have been exercised.

Discord OAuth authenticates the human; it does not provide another application's
bot token. Users create their application in the Developer Portal and invite it
with the required scopes/permissions. Show this clearly in onboarding.

For hosted mode, store tokens encrypted with a separately managed key, redact
logs, allow rotation/removal, enforce project ownership at every API boundary,
use secure HTTP-only sessions, OAuth state and CSRF protection. Never return stored
tokens to the editor. Default to minimal intents and permissions; make privileged
intents explicit for prefix or future member-event features.

Run bot clients outside API workers. For the owner-only MVP, supervise one process
per bot in a runner service with a strict bot limit; move to stronger per-tenant
isolation before public hosting. Track desired and observed state, heartbeat,
retry backoff and logs. Use database leases to ensure only one runner owns a bot,
including during deploys. API scaling must never duplicate Discord connections.
Publish immutable revisions; keep drafts separate and support rollback.

## Coolify deployment

Use one Docker Compose resource with web, API, PostgreSQL, and an optional runner.
Expose the web entry point publicly and forward /api to the internal API so login
and CSRF controls use one origin. Keep database and runner off public host ports.
Use Compose service names for internal communication and let Coolify manage
networking. Pollish's Bun multistage Dockerfile is the closest local reference;
do not copy older npm-based setup from Shalendar into this project.

Provide service health checks, database persistence/backups and a tested restore,
secrets via Coolify environment settings, restart policies and resource limits.
Run schema migrations once before app rollout. Drain/release runner leases on
shutdown and verify recovery after a forced restart. Avoid build-time secrets and
Docker socket access from the public API. Redis is unnecessary initially; add it
only if a demonstrated job/coordination workload warrants it.

## Delivery sequence and acceptance gates

1. **Compatibility baseline:** latest existing dependencies and required discord.py
   changes; offline regression tests and wheel build. A live test bot verifies
   prefix replies, embeds, help and Developer Portal intent setup.
2. **Shared core:** versioned models, safe interpreter, simulated adapter, CLI,
   DBot migration adapter and exports. A saved definition behaves identically
   through Python and simulation; reject invalid graphs and missing variables.
3. **Editor:** SvelteKit shell matching the app family, templates, canvas,
   inspector, preview, undo/redo, import/export and local drafts. Complete a bot
   without writing code using mouse or keyboard; verify desktop/mobile layouts.
4. **API and persistence:** OAuth sessions, ownership, PostgreSQL migrations,
   draft/revision storage, conflict detection and schema-derived frontend types.
   Test cross-user access denial and save/reload/export equivalence.
5. **Owner-only hosted pilot:** encrypted credentials, invite guidance, explicit
   publish, runner supervision, status/logs, rollback and Coolify Compose. Verify
   a real slash command, token rotation, restart recovery and no duplicate runner.
6. **Release:** fresh install from built wheel, supported Python CI matrix,
   browser accessibility/interaction tests, deployment smoke checks, documentation
   and PyPI trusted publishing. Publish a v2 prerelease before stable. Public
   hosted access is a separate launch gate after capacity and isolation tests.

Recommended first vertical slice: build /hello visually, preview it, export its
definition, and run it through the Python library in a test Discord server.

## Documentation consulted

- https://pypi.org/project/discord.py/ (current release; registry JSON also checked)
- https://pypi.org/project/setuptools/ (registry JSON checked)
- https://pypi.org/project/wheel/ (standalone build dependency no longer required)
- https://discordpy.readthedocs.io/en/stable/migrating.html
- https://discordpy.readthedocs.io/en/stable/intents.html
- https://svelteflow.dev/ (Svelte 5 custom nodes and graph editing)
- https://fastapi.tiangolo.com/advanced/generate-clients/
- https://coolify.io/docs/ (Compose networking, persistence and health checks)
