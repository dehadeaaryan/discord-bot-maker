# Migrating from 1.0.0 to 2.0.0a1

This is a major-version prerelease. Keep existing working bots backed up and try
changes in a dedicated Discord application/server before moving them into use.

## New bot scripts

```python
from discord_bot_maker import Bot

bot = Bot.from_env()
bot.reply("hello", "Hello, {{user.display_name}}!")
bot.run(sync=True)
```

New scripts use slash commands by default through `from_env()`. Put the token and
optional IDs in `.env`. No privileged intent is required for these commands.

## Existing DBot scripts

`from discord_bot_maker import DBot` still works with `bTOKEN`, `bPrefix`,
`helpCommand`, `baseCode`, `createCommand()`, `createCommands()`, `commandHi()`,
`commandHelp()`, `getBotInstance()`, `bRun()`, tuple addition, call syntax and
context-manager startup. Enable Message Content Intent in the portal for prefix
commands. The original `Bot(token, prefix=...)` constructor also retains prefix
behavior. `Bot(token, slash_only=True)` explicitly opts into slash-only operation.

| Older API | Preferred API |
| --- | --- |
| `DBot(bTOKEN, bPrefix, ...)` | `Bot.from_env()` for slash commands; explicit constructor for prefix bots |
| `createCommand(trigger, reply, reply2, emoji, image, help)` | `reply(name, Embed(reply, description=...))` for slash commands, or `add_command()` for prefix compatibility |
| `bRun()` | `run()` |
| `getBotInstance()` / `.bot` | `.client` |
| `commandHi()` | `add_greeting_command()` for prefix bots |
| `commandHelp()` | `add_help_command()` for prefix bots |
| `commDict` | `command_definitions` |
| `baseCode()` | `initialize()` after `auto_initialize=False` |

## Behavior changes

- Python 3.10+ is required. The default development interpreter is Python 3.15.0.
- The formerly incomplete `Command` class is an immutable dataclass, not a mutable
  builder. `add_command()` returns one; static slash replies use `reply()`.
- `.commDict` returns a snapshot; mutate commands through public methods instead.
  `.bTOKEN` and `.bPrefix` are read-only compatibility properties.
- Commands match a complete first word. `!hello there` matches `hello`;
  `!helloworld` does not. Bot-authored messages are ignored.
- The package does not add promotional attribution or a hard-coded author mention.
  The unused legacy `owner` field is retained as configuration but does not grant
  administrator access. Use explicit `permission=` or `role_id=` checks.
- Context-manager exceptions no longer launch the bot. Prefer an explicit run().
- DMs have empty server values; some channel properties may also be absent.
- The direct runtime dependency is `discord.py`, replacing the `discord` alias.

## Variables and definitions

Legacy prefix replies continue to accept `<author display name>` and other
existing placeholders. New replies use `{{user.display_name}}` and the variables
listed in the [authoring guide](authoring.md).

`bot.to_definition()` exports static text/Embed slash replies and legacy static
prefix replies. Multi-prefix bots export the first prefix only. Python callbacks,
buttons, random replies and background features cannot be represented as static
JSON; preserve their Python source instead. Export raises an error rather than
silently omitting these features.

To import a saved v1 command dictionary (JSON mapping names to reply tuples/lists):

```sh
discord-bot-maker migrate legacy-commands.json --prefix '!' > bot.json
```

The importer does not execute Python. It converts supported legacy variables and
rejects variables without a v2 graph equivalent with an actionable error.
