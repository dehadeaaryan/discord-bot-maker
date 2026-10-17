# Discord Bot Maker: agent guide

Use this guide when writing a bot with the installed `discord-bot-maker` package.
Import `discord_bot_maker`; do not import `dbm` (a Python standard-library module).
Python 3.10+ is supported. Use the installed version's API; do not invent helpers.

## Start here

Prefer the package facade to direct discord.py command trees, interaction response
handling, or a custom storage layer. Add as many commands as the bot needs.
Keep application-specific personality and commands in the bot's own script.
Sponge is an example consumer, not a framework feature.

```python
from discord_bot_maker import Bot, CommandContext, Embed

bot = Bot.from_env()
bot.reply("hello", Embed("Hello, {{user.display_name}}!"))

@bot.command(description="Add two numbers")
def add(first: int, second: int = 1):
    return str(first + second)

@bot.command(description="Count your visits", cooldown=3)
def visit(ctx: CommandContext):
    count = ctx.user_store.increment("visits")
    return f"Visit {count}."

if __name__ == "__main__":
    bot.run(sync=True)
```

Configure features before `run()`. Use `sync=True` on first run and after command
changes; normal restarts can use `bot.run()`. Synchronization replaces the app's
commands in the selected server or global scope. Do not start or sync a real bot
as part of an offline test. Keep bot construction separate from process startup.

## Credentials and Discord setup

`Bot.from_env(path=".env", storage="data/bot.sqlite3")` reads `.env` relative to the
working directory. Exported environment variables take priority. Settings:

```dotenv
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_test_server_id
DISCORD_CHANNEL_ID=
```

Only the token is required. Server ID scopes test registration; optional channel
ID restricts where commands respond. Add `.env` and bot data to `.gitignore`.
Never read, print, commit, export, or request a real token in chat. Use placeholders
for tests. Application ID, public key and OAuth client secret are not bot tokens.

Create an app in https://discord.com/developers/applications. Under Bot, add a bot
user if prompted and use Reset Token. Under Installation, enable Guild Install,
select `bot` and `applications.commands`, and grant View Channels, Send Messages
and Embed Links. Open the Discord Provided Link and install to a server you manage.
Use Discord's Developer Mode to copy a server/channel ID.

`Bot.from_env()` is slash-only and needs no privileged intents. Prefix commands
require Message Content Intent; member welcomes require Server Members Intent.
Gateway bots do not need an Interactions Endpoint URL. Reset an exposed token.

## Command contract

- `bot.reply(name, response, description=..., private=False, cooldown=0)` registers
  a fixed reply. `bot.random_reply(name, responses, ...)` picks a random response.
- `@bot.command(name=None, description=None, private=False, cooldown=0,
  permission=None, role_id=None)` accepts normal or async functions.
- Annotate slash options with `str`, `int`, `float`, `bool`, or `typing.Literal`.
  Defaults make options optional. No `*args`, `**kwargs`, or positional-only options.
- An optional first parameter named `ctx` or `context` receives `CommandContext`;
  it is not a Discord slash option. Use `ctx.user`, `ctx.server`, `ctx.channel`,
  `ctx.store` (server data) and `ctx.user_store` (server + user data).
- Return `str`, `Embed`, `Message`, or `Poll`. Async handlers can instead use
  `await ctx.respond(...)`. Do not manually defer or acknowledge the interaction;
  the package handles that. A handler returning None without a response gets Done.
- Use `permission="manage_guild"` for server administration, `role_id` for a role
  restriction, and `private=True` for private responses. Raise `UserError` for a
  safe validation message. Never expose credentials in errors or responses.
- Normal handlers run on worker threads. Async handlers run on the event loop;
  use async I/O there instead of blocking it.

## Responses and opt-in features

Public imports include `Bot`, `CommandContext`, `Embed`, `Message`, `Button`,
`Poll`, `UserError`, `Store`, `BotDefinition`, `Context`, `Engine`, and `FlowBot`.
`Embed` is a response value; it is different from the graph's embed block model.

```python
from discord_bot_maker import Button, Message

bot.reply("links", Message("Useful links", buttons=[
    Button("Website", url="https://example.com"),
    Button("Hello", reply="Hello, {{user.display_name}}!"),
]))
bot.poll()       # /poll
bot.reminders()  # /remind, /reminders, /cancel_reminder
```

Each Button takes exactly one of `url=` or `reply=` (a response or callback).
`Message(..., owner_only=True)` restricts interactive callbacks to the invoker.
Buttons and polls are temporary; reminders persist in SQLite. Reminder delivery
is visible in the original channel. Run one bot process per storage file.

- `bot.welcome(channel_id, message=...)` opts into member welcomes and members intent.
- `@bot.every(seconds=..., channel_id=...)` schedules a zero-argument callback.
- `await bot.send(channel_id, response)` explicitly sends a response to a channel.
- Use `ctx.store.get/set/increment` or `ctx.user_store.get/set/increment` for data.
- Use `bot.client` only when the public facade does not support the needed feature.

Template variables use double braces, for example `{{user.display_name}}`,
`{{server.name}}`, and `{{channel.name}}`. Use normal Python expressions for
computed values in callbacks. Do not assume arbitrary Python executes in templates.

## Portable graphs and offline preview

`bot.to_definition(name="My bot")` exports supported static text/Embed replies.
Python callbacks, buttons and background features cannot be serialized to graphs;
export rejects unsupported features rather than silently dropping them.

```python
from discord_bot_maker import Bot, Context, Engine

bot = Bot("offline-placeholder", slash_only=True)
bot.reply("hello", "Hello, {{user.display_name}}!")
result = Engine(bot.to_definition()).execute("hello", Context(display_name="Sam"))
assert result["messages"][0]["content"] == "Hello, Sam!"
```

This does not connect to Discord. Close `bot.client` with
`await bot.client.close()` when cleaning up async tests.

The CLI supports `template`, `validate`, `preview`, `export`, `run`, and `migrate`.
Use `discord-bot-maker --help` and each subcommand's `--help` for exact flags.
The CLI and exported launcher read environment variables; unlike `Bot.from_env()`,
they do not automatically load `.env`.

## More examples

- Authoring: https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/authoring.md
- Sponge: https://github.com/dehadeaaryan/discord-bot-maker/blob/main/examples/sponge.py
- Setup: https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/first-bot.md
- Migration: https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/migration.md

Legacy `DBot`, `createCommand()`, and `bRun()` remain available for old projects.
Prefer `Bot.from_env()`, `reply()`, and `@bot.command()` for new bots. The Python
library works independently of the repository's website, API and hosted runner.
