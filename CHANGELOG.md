# Changelog

## 2.0.0a1 — 2026-10-17

First v2 prerelease, following PyPI 1.0.0. The Python package is the release target;
the repository's unfinished web app and hosted services are not in the artifacts.

### Authoring

- `Bot.from_env()` reads bot token/server/channel settings without executing shell
  syntax. Exported variables take precedence. Defaults to slash-only operation.
- `reply()` and `random_reply()` turn text or rich responses into slash commands.
- `@bot.command()` turns typed normal/async functions into slash commands, with
  defaults for optional options and an injectable `CommandContext`.
- Text, `Embed`, `Message`, `Button`, and `Poll` response types; automatic
  acknowledgement, safe rendering and exception handling.
- Permission/role checks, per-user cooldowns, optional server/channel restrictions,
  private commands and suppressed automatic mentions.
- Scoped SQLite JSON storage, atomic counters, opt-in reminders, polls, member
  welcomes and repeated callbacks. Background tasks stop with the client.
- Reminders persist across restarts with ownership checks and bounded retries.
  Polls and buttons are deliberately temporary; see authoring docs for limits.

### Portable bot definitions

- Versioned Pydantic graph models with typed triggers, replies, embeds, role/channel
  conditions, validation for IDs, connections, loops, reachability and variables.
- Shared bounded engine for previews and Discord execution; slash and prefix modes,
  reply rendering, execution traces, cooldowns and Discord response limits.
- CLI commands: template, schema, validate, preview, export, run and migrate.
- Static reply export includes JSON plus a Python launcher. Python callbacks and
  interactive/background features reject JSON export rather than silently vanish.

### Compatibility and packaging

- Direct discord.py 2.7.1+ dependency, required intents and current avatar APIs.
- Python 3.10+ package requirement; project development environment uses 3.15.0.
- `DBot` and documented legacy constructor/method entry points retained. Command
  matching now uses a full word and bot-authored messages are ignored.
- Missing server/channel information no longer crashes DM replies.
- The unfinished mutable Command builder is replaced by an immutable dataclass.
- Legacy dictionary access is a snapshot. Default author mentions and promotional
  embed fields removed. Context-manager exceptions no longer start a bot.
- PEP 621 metadata, MIT license expression, type marker, explicit runtime
  dependencies, source manifest and release validation.
- Sponge is a separate example consumer of the public API. Documentation includes
  first-run setup, complete authoring recipes, migration and AI coding guidance.

### Repository-only work

- FastAPI persistence/OAuth/ownership/revision APIs, Alembic migrations, runner
  lease/supervision code, Svelte visual editor and Coolify configuration drafts.
- Web work remains paused; browser, production PostgreSQL, runner recovery and
  container deployment checks remain outstanding. See implementation-status.md.

## 1.0.0

Original Discord bot wrapper published on PyPI. Supported terse DBot prefix reply
commands, help/greeting helpers and string placeholders.
