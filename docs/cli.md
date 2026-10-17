# Command-line reference

Installing the package provides `discord-bot-maker`. Its equivalent module entry
point is `python -m discord_bot_maker.cli`. CLI input definitions are JSON; run
commands do not execute arbitrary Python from a definition.

```sh
discord-bot-maker --version
discord-bot-maker --help
discord-bot-maker template greeting > bot.json
discord-bot-maker schema > bot-definition.schema.json
discord-bot-maker validate bot.json
discord-bot-maker preview bot.json --command hello
discord-bot-maker export bot.json --output bot.zip
```

- **template [greeting|rules|faq]:** print a starter definition. Default: greeting.
- **schema:** print the authoritative JSON Schema.
- **validate FILE:** check the complete definition and graph; exit nonzero on error.
- **preview FILE:** run the same bounded interpreter used by Discord. Options:
  `--command NAME` (hello), `--mode slash|prefix` (slash), `--context FILE`.
- **export FILE --output PATH:** ZIP containing bot.json, run_bot.py, requirements.txt
  and instructions. Tokens are never written into the archive.
- **run FILE:** connect with exported `DISCORD_BOT_TOKEN`. Options: `--sync` and
  `--guild-id ID`. Unlike Bot.from_env(), this CLI uses exported environment
  variables and does not implicitly load .env.
- **migrate FILE --prefix PREFIX:** convert a saved v1 JSON command dictionary to
  a portable graph; default prefix is `!`. Python source is not executed/imported.

Example preview context:

```json
{
  "display_name": "Sam",
  "server_name": "My server",
  "channel_name": "general",
  "channel_id": "123456789",
  "role_ids": ["987654321"]
}
```

Context fields are user_id, user_name, display_name, channel_id, channel_name,
server_id, server_name, message_content and role_ids. Omitted fields have sample
values. Preview performs no Discord network calls. Each invocation starts a fresh
engine, so cooldown state does not persist between separate CLI previews.

Set `DISCORD_BOT_TOKEN` through your shell/secret manager for `run`; do not paste
it into a terminal command that will be retained in history. The standalone
examples can instead load the ignored .env file and support first-run hidden
input. See first-bot.md for portal setup and authoring.md for Python helpers.
