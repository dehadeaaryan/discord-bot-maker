# Implementation status

Web development is paused at the user's request while the standalone example
bot is tried in Discord.

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
  controls implemented. Type checking and production compilation passed. Initial
  browser tests failed and were interrupted when web work was deferred; inspect
  these before resuming. The UI is not yet browser-verified.
- Coolify Compose and Dockerfiles drafted. Docker is unavailable locally; no
  containers built or deployed. Operational restore validation remains outstanding.
  Python CI and a manual PyPI publishing workflow are now included; they have not
  yet run on GitHub.
- PyPI package is an unpublished 2.0.0a1 prerelease. Nothing was deployed or published.

Release preparation: version 2.0.0a1; see docs/releasing.md and CHANGELOG.md.
Only the Python package is a PyPI release target. Web/backend code is committed
as explicitly unfinished repository work and excluded from PyPI distributions.
