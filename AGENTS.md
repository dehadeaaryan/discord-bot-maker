# Discord Bot Maker repository

Read [the package agent guide](src/discord_bot_maker/AGENTS.md) for the public API
and bot authoring patterns. [docs/authoring.md](docs/authoring.md) is the detailed
reference; [examples/sponge.py](examples/sponge.py) demonstrates the public facade.
Read [docs/development.md](docs/development.md) for repository setup and layout.

## Work boundaries

- The distribution is `discord-bot-maker`; the import is `discord_bot_maker`.
- Keep Sponge's commands and personality in its example script. Use the name
  Sponge, not Spongey. Generic capabilities belong in the library.
- Keep Python library users independent of apps/web, apps/api and apps/runner.
- Preserve Python 3.10+ compatibility and the documented legacy DBot API.
- Do not edit generated schema/TypeScript by hand. Use
  `.venv/bin/python -m scripts.generate_schema` and `bun run types` in apps/web.
- Never print or commit .env contents, tokens, bot data or other credentials.
  Use offline fixtures; do not start, stop or synchronize a live bot during tests.

## Checks and packaging

Run `.venv/bin/python -m pytest -q` for Python changes. For web changes, run
`bun run check`, `bun run build`, and appropriate browser checks from apps/web.
Read docs/releasing.md before preparing distributions. Include both package
AGENTS.md and CLAUDE.md in wheels and source archives and run artifact/secret
checks. Do not upload a release without the user's instruction.

## Tooling and identity

Use the user's configured Git user.name and user.email for every commit; never
substitute an assistant identity. Use Bun for JavaScript/TypeScript dependencies,
runtime, lockfiles, Docker, CI and setup instructions.

Use Context7 for current library/framework/API/CLI/cloud documentation: resolve
the library ID first, then query the relevant concept. This is unnecessary for
ordinary refactoring, business-logic debugging or general programming concepts.
