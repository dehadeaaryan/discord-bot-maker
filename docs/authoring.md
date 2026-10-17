# Author a bot with Discord Bot Maker

Sponge is an example **using** this package. Its personality and duck belong in
[examples/sponge.py](../examples/sponge.py), not in the library. The library takes
care of Discord registration, interaction timing, response rendering, permissions,
cooldowns, storage, views, timers and shutdown.

Import `discord_bot_maker`. Do not name a new import package `dbm`: Python already
has a standard-library module with that name. `import discord_bot_maker as dbm`
is a fine local alias if desired.

## A complete bot

```python
from discord_bot_maker import Bot, Embed

bot = Bot.from_env()
bot.reply("hello", Embed("Hello, {{user.display_name}}!", "Welcome to {{server.name}}."))

@bot.command(description="Add two numbers")
def add(first: int, second: int = 1):
    return f"The answer is {first + second}."

bot.run(sync=True)
```

`.env` in the working directory supplies `DISCORD_BOT_TOKEN`, optional
`DISCORD_GUILD_ID` and optional `DISCORD_CHANNEL_ID`. Already-exported variables
win over file values. `Bot.from_env()` defaults to slash commands without
privileged intents. The original `Bot(token, prefix=...)` constructor keeps its
prefix behavior; use `Bot(token, slash_only=True)` for an explicit slash-only bot.
A missing token fails with an actionable message before connecting.

Use `sync=True` on first run and after adding, renaming or removing commands.
It synchronizes to `DISCORD_GUILD_ID` if set, otherwise globally. Sync replaces
that application's commands in that scope, so use a dedicated application.
Normal restarts can use `bot.run()`. The bot must remain running to respond.

## The public API

| Task | API |
| --- | --- |
| Load token and IDs | `Bot.from_env(path=".env", storage="data/bot.sqlite3")` |
| Explicit setup | `Bot(token, slash_only=True, guild_id=..., channel_id=..., storage=...)` |
| Fixed slash reply | `bot.reply(name, response, description=..., private=False, cooldown=0)` |
| Random text | `bot.random_reply(name, responses, description=..., cooldown=0)` |
| Custom slash command | `@bot.command(name=None, description=None, private=False, cooldown=0, permission=None, role_id=None)` |
| Button poll command | `bot.poll(name="poll")` |
| Persistent reminders | `bot.reminders()` |
| Member welcomes | `bot.welcome(channel_id, message="Welcome, {{user.display_name}}!")` |
| Repeated action | `@bot.every(seconds=..., channel_id=...)` |
| Explicit channel send | `await bot.send(channel_id, text_or_embed)` |
| Start | `bot.run(sync=False)` |
| Export static replies | `bot.to_definition(name="My bot")` |
| Advanced Discord access | `bot.client` |

The helper methods are methods on `Bot`; no feature modules need manual loading.
Configure features before calling `run()`. No command is registered with Discord
until synchronization. Local construction and registration do not connect.

## Command functions

A function's name becomes the slash command name unless `name=` is supplied.
Descriptions come from `description=`, the first docstring line, or a generic
fallback. Annotated parameters become slash options. Defaults make options
optional. Use `str`, `int`, `float`, `bool`, or `typing.Literal` for simple choices.
Discord user/member/channel/role types work through the underlying SDK when needed.
No `*args`, `**kwargs` or positional-only option parameters are supported.

```python
@bot.command(description="Pick a snack")
def snack(name: str, amount: int = 1):
    return f"{amount} servings of {name}, coming up."
```

Put `ctx` or `context` first to receive a `CommandContext`. It is not a slash option.
The context exposes `user`, `server` (None in DMs), `channel`, `store`,
`user_store`, `bot`, and the underlying `interaction` as an escape hatch.

```python
from discord_bot_maker import CommandContext, UserError

@bot.command(description="Count your visits", cooldown=3)
def visit(ctx: CommandContext):
    count = ctx.user_store.increment("visits")
    return f"Hello {ctx.user.display_name}. Visit number {count}!"

@bot.command(description="Set the server greeting", permission="manage_guild", private=True)
def greeting(ctx: CommandContext, message: str):
    if len(message) > 200:
        raise UserError("Keep the greeting under 200 characters.")
    ctx.store.set("greeting", message)
    return "Greeting saved."
```

Normal functions run on a worker thread so they do not block the Discord event
loop. Async functions run on that loop and must use async clients for network I/O.
All commands are acknowledged automatically before handlers run; do not call
`interaction.response.defer()` yourself. Return a response, or use
`await ctx.respond(...)` and return None. A handler that does neither receives
an automatic “Done.” acknowledgement. Commands and buttons suppress automatic
mentions. Raise `UserError` for a safe user-facing validation message; unexpected
exceptions return a generic failure and do not echo exception details.

Use `private=True` for commands containing personal data. If a public command
fails after acknowledgement, the package completes its public response with a
generic notice, then sends error details privately. Authorization failures are
checked before acknowledgement and always respond privately.

## Responses and buttons

Return text, `Embed`, `Message`, or `Poll` from a handler. Text and embed replies
accept `{{user.display_name}}`, `{{server.name}}`, `{{channel.name}}`, and the other
variables listed in the definition schema. Rendered Discord length limits apply.
Use `ctx.user` and Python expressions for arbitrary computed values.

```python
from discord_bot_maker import Button, Embed, Message

bot.reply("links", Message(
    "Where would you like to go?",
    buttons=[
        Button("Website", url="https://example.com"),
        Button("Say hello", reply="Hello, {{user.display_name}}!"),
    ],
))

def count_click(ctx: CommandContext):
    return f"You have clicked {ctx.user_store.increment('clicks')} time(s)."

@bot.command(description="Open your counter")
def counter():
    return Message("Give it a click.", buttons=[Button("Click", reply=count_click)], owner_only=True)
```

`Embed(title, description="", color="#ff7a30", image_url=None)` is independent
of the visual graph model. `Message(content="", embed=None, buttons=(),
timeout=180, owner_only=False)` accepts up to five buttons. Each button needs
exactly one `reply=` (text, Embed or callable) or `url=`. Styles are `primary`,
`secondary`, `success`, and `danger`. Button functions receive the clicking
user's context. Permission and role checks carry over from the original command.
Button actions reply privately. Buttons disable after their timeout (1–900 seconds)
and cannot survive a bot restart. An owner-only view restricts callbacks to the
invoking user; link buttons are ordinary URLs and are not access-controlled.

## Polls, reminders and schedules

`bot.poll()` installs `/poll question choices`. Separate choices with `|`:
`Minecraft | Valorant | Something else`. A user has one vote and can change it.
Polls run for five minutes and are held in memory. Return
`Poll(question, choices, timeout=...)` from a custom command to customize one.
Polls are for informal use: they are not anonymous and do not survive restarts.

`bot.reminders()` installs `/remind minutes message`, `/reminders`, and
`/cancel_reminder reminder_id`. These acknowledgement/listing commands are private;
the actual reminder is delivered to the original channel and mentions only its
owner. Reminder text is therefore visible to that channel's members. Durations
range from one minute to 30 days, with up to 25 pending reminders per user.
Custom handlers can call `ctx.remind_in(minutes, message)` once reminders are enabled.

Reminders persist in the configured SQLite file. Overdue reminders are attempted
when the bot comes online. Failed delivery retries with backoff up to five times.
There is a rare possibility of duplicate delivery if the process crashes after
Discord accepts a message but before the local delivery record is saved. Run one
bot process per storage file; these helpers are for standalone bots, not a
multi-worker reminder service.

```python
@bot.every(seconds=3600, channel_id=123456789)
def hourly_tip():
    return "Remember to take a break."
```

Schedules wait for the bot to connect, then run after each interval. They do not
run immediately or catch up after downtime. Scheduled callbacks take no arguments
and return text or Embed (or None to skip sending). Tasks stop when the client
closes. Use persistent reminders for one-off delayed delivery.

## Storage

`bot.store` is global to the bot. `ctx.store` is server-scoped; in DMs it is
isolated by user. `ctx.user_store` is scoped to both server and user. Keep separate
bots on separate storage files. All values must be JSON-serializable and at most
64 KiB. Keys have 1–128 characters.

```python
ctx.store.set("settings", {"language": "en"})
settings = ctx.store.get("settings", {"language": "en"})
count = ctx.user_store.increment("points", 10)
ctx.user_store.delete("points")
```

`increment()` is atomic; separate `get()`/`set()` calls are not a transaction.
`store.scope("feature", "key")` provides further exact-component namespaces.
The default `data/` folder is ignored by Git. Back up the SQLite file for data you
care about; the library never stores the Discord bot token there.

## Welcomes

```python
bot.welcome(123456789, "Welcome to {{server.name}}, {{user.display_name}}!")
```

This explicitly enables the member intent in code. Also enable **Server Members
Intent** in Developer Portal → Bot. Ordinary slash commands need no privileged
intents. The welcome channel must belong to the joining member's server.

## Export and compatibility

Static `.reply()` text/Embed commands and legacy `.add_command()` replies can
produce a versioned `BotDefinition`. Use `Engine`/`FlowBot` or the CLI for portable
preview and execution. Python functions, random choices, buttons, polls,
reminders, schedules and welcome callbacks are Python source features. Calling
`to_definition()` on such a bot raises an error instead of silently dropping them.
Keep the Python script when distributing a bot using these features.

Existing `DBot` constructors and legacy methods still work. Prefer
`Bot.from_env()` plus the methods above for new scripts. `Bot` and `FlowBot` are
different entry points: `Bot` is the authoring facade, while `FlowBot` executes an
already validated graph. There is no need to subclass either for ordinary bots.
