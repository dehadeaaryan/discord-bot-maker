# Discord Bot Maker

Read the adjacent [AGENTS.md](AGENTS.md) before writing or modifying a bot. It is
the shared guide for Claude, Codex and other coding agents: public API, complete
examples, credentials, command behavior, storage, features and offline preview.

Use `from discord_bot_maker import Bot` and start with `Bot.from_env()`. Prefer
`bot.reply()` and `@bot.command()` to direct Discord SDK plumbing. Sponge belongs
in an application script, not the core library. Never expose tokens or connect a
real bot during an offline test.

These guides ship inside the Python package. They are reference material, not
configuration automatically loaded into a consuming project's agent session.
When helping a user in another repository, explicitly read AGENTS.md from the
installed package or copy the relevant guidance into that project's instructions.


## 2.1 optional extensions

Read docs/v2.1.md in the repository (or the corresponding GitHub documentation)
for the complete 2.1 API. `@bot.command(mode="both")` supports shared slash/prefix
handlers; prefix mode requires `Bot.from_env(slash_only=False, prefix="!")`.
Checks, BotConfig, bot.help(), bot.on(), bot.trigger(), bot.auto_role(), bot.use(),
Settings, bot.job(), Simulator and sync previews are opt-in. Modal commands use
`defer=False`. Never use live bot storage in Simulator; callbacks execute real
application code. New durable jobs require one process per SQLite file and
idempotent handlers. PostgreSQL and restart-persistent views are not supported.
