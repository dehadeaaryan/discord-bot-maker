# Development and repository layout

## Python setup

The project pins Python 3.15.0 in .python-version. The library supports 3.10+.
Python is managed with uv on the author's machine; system Python is not changed.

```sh
uv venv --python 3.15 .venv
uv pip install -r requirements.lock
uv pip install -e '.[release]'
.venv/bin/python -m pytest -q
.venv/bin/python examples/bot.py --preview hello
```

Core-only contributors can install `.[test,release]` and run the library tests:

```sh
.venv/bin/python -m pytest tests/test_authoring.py tests/test_compatibility.py tests/test_engine.py tests/test_example.py -q
```

Tests use fake tokens and mocked interactions. They do not connect to Discord,
sync commands, or post messages. Never print a real .env file while debugging.
The Sponge example loads .env only when started, not when imported.

## Structure

| Path | Responsibility |
| --- | --- |
| src/discord_bot_maker/dbot.py | Public Bot facade and DBot compatibility |
| features.py | Slash authoring, policies, helpers, schedules and managed client |
| interactions.py | Context, templates, response sending, buttons and poll views |
| responses.py | Public response values and UserError |
| storage.py / reminders.py | Scoped SQLite JSON data and persistent reminder queue |
| config.py | Safe environment-file parsing and Discord IDs |
| definition.py / engine.py | Validated portable schema and bounded interpreter |
| flow.py | Discord adapter for portable definitions |
| export.py / migration.py / cli.py | ZIP exports, v1 importer and command line |
| examples/sponge.py | Sponge, using only public package APIs |
| examples/bot.py / package example.py | Minimal first-run example and offline preview |
| apps/api | Repository-only FastAPI backend |
| apps/runner | Repository-only owner-pilot supervisor |
| apps/web | Repository-only SvelteKit visual editor |
| migrations | Alembic schema revisions |
| schema | Generated JSON Schema and OpenAPI contracts |
| assets | Sponge avatar/banner artwork; not included in PyPI artifacts |

Module paths abbreviated in the table refer to src/discord_bot_maker.
See [authoring](authoring.md), [migration](migration.md), [release](releasing.md)
and [deployment](deployment.md) docs for their workflows.

## Dependency policy

Package runtime dependencies are declared in pyproject.toml. The optional test,
server and release extras serve different workflows; a normal install does not
pull in FastAPI or PostgreSQL dependencies. requirements.txt pins direct runtime
versions. requirements.lock resolves the full contributor/backend environment.
SQLAlchemy resolves to the newest compatible major: 2.0 on Python 3.10 and 2.1
on the current development interpreter. SQLAlchemy 2.1 requires Python 3.11+.
requirements-release.lock separately pins publishing tools and core dependencies.

```sh
uv pip compile --universal --python-version 3.10 --extra server --extra test pyproject.toml -o requirements.lock
```

Use the lowest supported interpreter for universal resolution. Re-run the supported
Python checks after changing dependencies. Build-system setuptools is separate
from installed runtime dependencies.

## Working on the web app later

Web development is paused. The editor compiles and type-checks, but the initial
browser suite failed and its integration work remains unfinished. Do not describe
it or the hosted service as production-ready. Bun is the frontend package manager
and runtime; its version is recorded in packageManager and Dockerfiles.

In separate terminals from the repository root:

```sh
ALLOW_DEV_LOGIN=1 sh scripts/dev-api.sh
```

```sh
cd apps/web
bun install --frozen-lockfile
bun run dev
```

Development defaults: web http://localhost:5173, API http://127.0.0.1:8000,
SQLite development.db. Settings read exported environment variables; backend
Settings does not implicitly load the standalone bot's .env. Development login is
explicitly opt-in and prohibited when APP_ENV=production.

```sh
cd apps/web
bun run check
bun run build
bun run test:ui
```

The browser-test config starts its own API and development web server and uses a
temporary SQLite file. Those tests are not part of the PyPI release gate while
web integration is deferred. See implementation-status.md for outstanding work.

## Contracts and migrations

Run the schema generator as a module from the root:

```sh
.venv/bin/python -m scripts.generate_schema
cd apps/web
bun run types
```

Pydantic models are the bot-schema authority; never edit generated TypeScript or
JSON by hand. The OpenAPI schema comes from the API implementation. Generated
contracts contain schemas and examples, not configured credentials.

```sh
.venv/bin/alembic upgrade head
```

Alembic uses DATABASE_URL if exported and otherwise local SQLite. Repository API
integration tests create temporary schemas and verify ownership, CSRF, conflicts,
credential encryption, publishing and rollback. Runner tests exercise database
lease ownership. A production PostgreSQL/runner recovery test remains necessary.

## Git and artifacts

Commit source, docs, lockfiles, schema and intentional artwork. Do not commit
.env, bot databases, .DS_Store, node_modules, virtual environments, .egg-info,
build/, dist/ or browser-test artifacts. Generated distributions are uploaded to
PyPI/release artifacts, not versioned in Git.
