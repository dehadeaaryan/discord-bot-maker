# Implementation status

Web development resumed after the user published the Python prerelease on PyPI.

- Python 3.15.0 installed as the user's shell default; project .venv recreated on 3.15.0.
- Versioned graph models, bounded engine, templates, CLI, exports, migration helper,
  and Discord slash/prefix adapter implemented.
- High-level authoring facade added: Bot.from_env(), reply(), typed command
  decorators, response objects, buttons, polls, scoped SQLite storage, persistent
  reminders, scheduled callbacks and member welcomes. Sponge is a separate public
  API consumer in examples/sponge.py. The minimal example also uses the facade.
- Authoring docs and llms.txt document the supported API for humans and AI tools.
  Helpers are tested offline. Sponge was restarted and connected with its expanded
  command set synchronized live; individual new features still need more live testing.
- Runnable example: examples/bot.py; setup: docs/first-bot.md. Offline replies and
  channel restriction tested. Discord authentication and command synchronization
  succeeded against the configured test server.
- API persistence, OAuth, CSRF, project ownership, revisions, credentials and runner
  lease code implemented with offline tests. Production PostgreSQL and process
  recovery integration checks remain.
- Web editor, local drafts, previews, import/export, account/project and hosted
  controls implemented. Type checking and fresh production server build passed. Ten browser checks cover
  create/preview/export/save/reload, both condition branches, mobile list editing,
  palette drag/drop, undo/redo, import and validation. Saved drafts retain their
  project identity and optimistic version after reloading.
- Coolify Compose and Dockerfiles drafted. Docker is unavailable locally; no
  containers built or deployed. Operational restore validation remains outstanding.
  Python, production web, container-build CI and a manual PyPI publishing workflow are included; they have not
  yet run on GitHub.
- The user reports publishing 2.0.0a1 on PyPI. No website deployment performed. Export-first web deployment supports optional OAuth;
  development login and hosting are disabled by default in production.

Release preparation: stable version 2.0.0; see docs/releasing.md and CHANGELOG.md.
Only the Python package is a PyPI release target. Web/backend code is committed
as separate repository work and excluded from PyPI distributions.
