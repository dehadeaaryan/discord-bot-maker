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

The prepared stable release is **2.0.0**. The project uses Python **3.15.0**;
the package declares Python 3.10+. Sponge has connected and synchronized its expanded command set live;
automated tests cover the authoring features offline. More live feature testing is welcome.

## Create your Discord bot

1. Open the [Discord Developer Portal](https://discord.com/developers/applications),
   choose **New Application**, and give your bot a name.
2. Open **Bot**. Add a bot user if prompted, then choose **Reset Token** and copy
   the **bot token**. This is different from the application ID, public key, and
   OAuth client secret. Keep it private; reset it if it is exposed.
3. Open **Installation**, enable **Guild Install**, and select the `bot` and
   `applications.commands` scopes under **Default Install Settings**.
4. Give it **View Channels**, **Send Messages**, and **Embed Links**, then save.
   Open the **Discord Provided Link**, select **Add to Server**, and authorize it
   in a server you can manage. Administrator permission is unnecessary.
5. For faster testing, enable **User Settings → Advanced → Developer Mode** in
   Discord, then right-click your server and choose **Copy Server ID**.

Slash commands do not need privileged intents. Enable **Message Content Intent**
on the Bot page only if you use prefix commands. Enable **Server Members Intent**
if you use `bot.welcome()`. These bots connect through the Gateway; leave
**Interactions Endpoint URL** empty. No public key or OAuth client secret is
needed to run the Python bot.

Keep the token in a local `.env` file next to your script and add `.env` to
`.gitignore`. `Bot.from_env()` reads it automatically. The runnable examples below
show the variable names. For installation details, see
[Discord's installation guide](https://discord.com/developers/quick-start/getting-started)
and our [first-bot guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/first-bot.md).

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

## Coding agents

`AGENTS.md` and `CLAUDE.md` ship inside the Python package with public API patterns,
examples, setup, and offline testing guidance. Agents do not automatically read
instructions from installed dependencies. Point your agent at the installed guide:

```sh
python -c "from importlib.resources import files; print(files('discord_bot_maker').joinpath('AGENTS.md').read_text())"
```

In this repository, the root AGENTS.md and CLAUDE.md point to the same guide.

## Learn the API

- [Authoring guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/authoring.md): command functions, response types, permissions, storage, polls, reminders and schedules.
- [Sponge's source](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/examples/sponge.py): a complete consumer of the public package API.
- [AI coding reference](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/llms.txt): canonical patterns, API links and boundaries.
- [v2 implementation plan](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/v2-plan.md) and [implementation status](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/implementation-status.md): the visual editor is in active development; hosted deployment checks remain.

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

After publishing 2.0.0, install the [stable release on PyPI](https://pypi.org/project/discord-bot-maker/) with:

```sh
python -m pip install --upgrade 'discord-bot-maker==2.0.0'
```

See the [release guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/releasing.md),
[changelog](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/CHANGELOG.md), and
[v1 migration guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/migration.md).
Only the Python package is being prepared for PyPI; the web app is a separate work in progress.
