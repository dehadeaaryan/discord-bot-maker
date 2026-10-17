# Discord Bot Maker

Make a Discord bot with a few readable Python functions. Discord Bot Maker handles
command registration, typed slash options, responses, buttons, permissions,
cooldowns, saved data and background tasks.

```python
from discord_bot_maker import Bot, CommandContext, Embed

bot = Bot.from_env()
bot.reply("hello", Embed("Hello, {{user.display_name}}!", "Welcome to {{server.name}}."))

@bot.command(description="Give yourself a point")
def point(ctx: CommandContext):
    return f"You have {ctx.user_store.increment('points')} points."

bot.run(sync=True)
```

No subclass, command tree, interaction response plumbing, or database setup is
needed for this example. [Sponge](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/examples/sponge.py) demonstrates the package as
a real bot, including a pet duck, saved snack counts, server settings, polls and
restart-safe reminders. Sponge's personality lives in its script; the library is
reusable for any bot.

The prepared release is **2.0.0a1**, the first v2 prerelease. The project uses Python **3.15.0**;
the package declares Python 3.10+. Sponge has connected and synchronized its expanded command set live;
automated tests cover the authoring features offline. More live feature testing is welcome.

## Run Sponge

The current checkout already has a virtual environment. Put these in `.env`:

```dotenv
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
DISCORD_CHANNEL_ID=
```

The channel is optional. `.env` is ignored by Git and loaded automatically.
Stop any previous instance, then run:

```sh
.venv/bin/python examples/sponge.py --sync
```

Try `/hello`, `/wisdom`, `/duck`, `/feed`, `/motto`, `/duck_motto`, `/poll`,
`/remind`, `/reminders`, or `/cancel_reminder`. `motto` requires Manage Server.
Use `--sync` after changing command definitions; omit it for ordinary restarts.

The original minimal example remains available:

```sh
.venv/bin/python examples/bot.py --sync
.venv/bin/python examples/bot.py --preview hello
```

[First-time Discord setup](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/first-bot.md) explains the bot token, installation,
permissions, server and channel IDs. Neither example requires an interactions URL.
Slash commands need no privileged intents. Calling `bot.welcome()` opts into
Server Members Intent, which must also be enabled in Discord's Developer Portal.

## Install from a fresh checkout

```sh
uv venv --python 3.15 .venv
uv pip install -e .
```

For contributors running all backend tests, install the locked dependencies too:

```sh
uv pip install -r requirements.lock
uv pip install --no-deps -e .
.venv/bin/python -m pytest -q
```

The core library does not require FastAPI, PostgreSQL or the web frontend. Those
are separate optional dependencies. `requirements.lock` pins the tested full
contributor/backend environment; the published package uses compatible ranges.

## Learn the API

- [Authoring guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/authoring.md): command functions, response types, permissions, storage, polls, reminders and schedules.
- [Sponge's source](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/examples/sponge.py): a complete consumer of the public package API.
- [AI coding reference](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/llms.txt): canonical patterns, API links and boundaries.
- [v2 implementation plan](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/v2-plan.md) and [implementation status](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/implementation-status.md): the web editor and hosted services remain paused.

## Portable definitions

Static text/Embed replies can be exported with `bot.to_definition()` for the shared
preview/Discord engine. Python callbacks and interactive/background features stay
in Python source; export rejects these instead of silently discarding them.

```sh
.venv/bin/discord-bot-maker template greeting > bot.json
.venv/bin/discord-bot-maker validate bot.json
.venv/bin/discord-bot-maker preview bot.json --command hello
.venv/bin/discord-bot-maker run bot.json --sync --guild-id YOUR_SERVER_ID
```

## Existing users

The distribution is `discord-bot-maker`; Python imports stay `discord_bot_maker`.
`DBot`, `createCommand()`, `bRun()`, and the original prefix API remain available.
For new bots use `Bot.from_env()`, `reply()` and `@bot.command()`.
The unfinished v1 Command builder is now an immutable command definition.
User-facing replies have no forced attribution or author mentions.

MIT licensed. Created by Aaryan Dehade.

## PyPI release

After 2.0.0a1 has been published, install the prerelease with:

```sh
python -m pip install --upgrade 'discord-bot-maker==2.0.0a1'
```

See the [release guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/releasing.md),
[changelog](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/CHANGELOG.md), and
[v1 migration guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/migration.md).
Only the Python package is being prepared for PyPI; the web app is a separate work in progress.
