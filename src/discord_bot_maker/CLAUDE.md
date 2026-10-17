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
