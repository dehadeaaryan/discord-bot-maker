# Discord Bot Maker

Make a Discord bot with a few readable Python functions. Discord Bot Maker handles
slash and prefix command registration, typed arguments, interactive responses,
permissions, cooldowns, saved data and background tasks. Start with a few lines;
opt into richer capabilities as your bot grows.

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

The prepared next release is **2.1.0** (unreleased). The package supports Python
3.10+; this checkout is tested on Python 3.15.0. The 2.1 features have offline
coverage, including real Discord command parsing, but still need live Discord
and container deployment verification.

## Contents

- [Discord application setup](#create-your-discord-bot)
- [Run Sponge and the minimal example](#run-sponge)
- [Install from a checkout](#install-from-a-fresh-checkout)
- [2.1 API in depth](#21-api-in-depth)
  - [Unified slash and prefix commands](#one-function-two-command-interfaces)
  - [Checks and searchable help](#checks-and-discoverable-help)
  - [Gateway configuration and event hooks](#gateway-configuration-and-hooks)
  - [Embeds, attachments, dropdowns, modals and autocomplete](#rich-responses-and-interactive-forms)
  - [Moderation confirmations and audit records](#focused-moderation)
  - [Packs and plugin discovery](#packs-and-installed-plugin-discovery)
  - [Versioned server settings](#versioned-per-server-settings)
  - [Durable scheduled jobs](#durable-jobs)
  - [Offline simulator](#offline-simulator)
  - [Operations, deployment and registration previews](#operations-and-registration-previews)
  - [Compatibility and limits](#compatibility-and-deliberate-limits)
- [Coding agents](#coding-agents)
- [Portable definitions](#portable-definitions)
- [Existing users](#existing-users)
- [Release and installation](#pypi-release)

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

## 2.1 API in depth

Every feature below is part of the standalone Python package and is optional.
A normal bot needs no web app, hosted runner, plugin system or separate database
service. Examples in these subsections extend the `bot` created in the first
subsection; register features before calling `bot.run()` under a main guard.
For a focused copy of this reference, see the
[2.1 guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/v2.1.md).

### One function, two command interfaces

```python
from discord_bot_maker import Bot, BotConfig, Checks, CommandContext

bot = Bot.from_env(prefix="!", slash_only=False, config=BotConfig(presence="with commands"))

@bot.command(mode="both", category="Utilities", cooldown=3,
             checks=Checks(server_only=True))
def add(ctx: CommandContext, first: int, second: int = 1):
    return f"{ctx.user.display_name}: {first + second}"

bot.help(mode="both")

if __name__ == "__main__":
    bot.run()
```

Enable Message Content Intent in the Discord developer portal for prefix commands.
`Bot.from_env()` remains slash-only unless explicitly configured otherwise.
`mode` accepts `slash` (default), `prefix`, or `both`. Both interfaces call the
same validation, authorization, per-user/per-server cooldown and error pipeline.
Handlers can be synchronous or asynchronous; synchronous handlers run in a worker
thread. Defaults make arguments optional. Supported types are `str`, `int`,
`float`, `bool` and homogeneous `typing.Literal` choices. Invalid arguments do
not consume a cooldown. Defaults are validated at registration.

Prefix arguments are positional: `!add 2 3`. Quote text containing spaces:
`!greet "Sam Smith"`. Boolean spellings are true/false, yes/no and 1/0.
There are no greedy trailing-text arguments or keyword flags. Slash autocomplete
suggestions do not restrict valid inputs; use Literal or handler validation.
Private/ephemeral command responses require `mode="slash"`; prefix messages
are public. Interactive callbacks can respond privately to the clicking user.

```python
from discord_bot_maker import UserError

@bot.on_error
def errors(ctx, error):
    if isinstance(error, UserError):
        return str(error)  # Safe user-facing validation detail.
    return "Something went wrong."
```

This handler covers command execution/argument errors and component callback
failures. Authorization denials and cooldown notices are handled directly.
Without a custom handler, internal exception values are never shown or logged.
Custom handlers are trusted application code and must avoid disclosing secrets.

### Checks and discoverable help

`permission="manage_guild"` and `role_id=123` remain supported. Add a Checks value
for `server_only=True`, `channels=(123, 456)`, `roles=(789,)`, or
`age_restricted=True`. Channel membership and role membership each use OR within
their list; distinct checks use AND. Age restriction means Discord's NSFW channel
flag, not verification of a person's age. Buttons, dropdowns and modal submissions
reapply the originating policy to the current interaction.

`bot.help(page_size=6)` registers searchable slash help; `mode="both"` adds prefix
help. Commands default to the General category; set `category=` to organize them.
`/help query:storage` searches name, description and category. Help hides commands
the caller cannot use, displays argument syntax, and offers Previous/Next buttons
and a category dropdown. Navigation belongs to the original caller and rechecks
permissions. The dropdown shows up to 24 categories; search still covers all
categories. Help and ordinary interactive messages expire; they do not persist
through restarts. Legacy `add_help_command()` retains its existing behavior.

### Gateway configuration and hooks

BotConfig accepts `intents=discord.Intents(...)`, `presence="Playing text"`,
`status="online"` (also idle/dnd/invisible), and
`allowed_mentions=discord.AllowedMentions(...)`. Explicit intents are copied;
prefix mode rejects an explicit configuration without message_content. Mentions
remain suppressed by default. Configured allowed mentions apply to command
responses; safety notices, welcomes and reminders retain their narrower policies.
`prefix="!"` or `prefix=("!", ".")` is public constructor/from_env configuration.

```python
bot.welcome(123, "Welcome, {{user.display_name}}!")
bot.auto_role(456)
bot.trigger("hello bot", "Hello, {{user.display_name}}!", exact=True)

@bot.on("reaction_add")
async def reaction(reaction, user):
    if str(reaction.emoji) == "👋":
        await reaction.message.channel.send("Hello!")
```

`bot.on()` supports message, member_join, reaction_add and ready. Hook failures
are isolated and logged by exception class. Member hooks opt into members intent;
message hooks opt into message_content. Enable those privileged intents in the
portal too. Reaction hooks use Discord's cached reaction events; uncached messages
are not covered. Bot messages are excluded from gateway message/reaction hooks
and message triggers. Direct event hooks receive raw discord.py objects. ready
can run again after reconnecting; make startup actions idempotent.

Auto-role assignment checks Manage Roles and the bot's hierarchy, and rejects
managed/default roles. Hook callbacks must handle their own application-specific
conditions. Hooks and legacy prefix commands respect the configured gateway
server/channel restrictions where applicable.

### Rich responses and interactive forms

```python
from discord_bot_maker import Attachment, Embed, Message, Select, Modal, TextInput

@bot.command()
def report():
    return Message(
        embed=Embed("Report", fields=(("Status", "Ready", True),), footer="Example"),
        attachments=[Attachment("report.txt", b"Report contents")],
        selects=[Select("Choose format", ["Text", "CSV"],
                        lambda ctx, value: f"Selected {value}")],
        owner_only=True,
    )

@bot.command(defer=False)
def feedback():
    return Modal("Feedback", [TextInput("message", "Your feedback", paragraph=True)],
                 lambda ctx, values: "Thanks for your feedback!")
```

Embed also accepts thumbnail_url and url, with field and total-character limit
checks before sending. Attachments contain in-memory bytes, not file paths;
Discord's upload limits still apply. Message supports up to 10 attachments,
five buttons and four single-selection dropdowns. Owner-only rules cover both
buttons and dropdowns. Callback signature is `(ctx, selected_value)` for dropdowns.

Forms must be the initial interaction response: use `defer=False` and respond
within Discord's acknowledgement window. A button opening a form similarly needs
`Button("Feedback", reply=callback, defer=False)`. A form callback accepts
`(ctx, values)` where values maps input names to text. Forms are owned by the
original user; submissions recheck command policies and respond privately.
Prefix commands cannot open forms directly. Do not perform slow I/O before opening
one. Existing commands still defer automatically by default.

```python
@bot.command(autocomplete={"topic": lambda ctx, current: ["Python", "Discord"]})
def topic(topic: str):
    return topic
```

Autocomplete providers receive `(ctx, current)` and return up to 25 string/int/float
values matching the option type. Providers may be async. Authorization is checked
before invoking them; failures produce an empty suggestion list and a safe log.

### Focused moderation

```python
@bot.command(permission="kick_members", checks=Checks(server_only=True), private=True)
async def kick(ctx, member_id: str, reason: str):
    member = await ctx.server.fetch_member(int(member_id))
    return bot.moderation.kick(ctx, member, reason=reason)
```

`bot.moderation.kick`, `.ban`, and `.timeout(ctx, member, minutes=10, reason=...)`
return a 60-second, owner-only confirmation prompt. No moderation occurs until
Confirm is clicked. Cancellation and duplicate clicks cannot execute the action.
The helper checks caller and bot permissions, caller and bot hierarchy, server
membership, owner/self/bot protection, and timeout limits. Confirmation fetches
fresh actor/target/bot members and rechecks permissions/hierarchy. Discord remains
the final authority if permissions change during the request.

An audit record is persisted before the request and updated afterward; Discord's
audit reason includes the moderator and local audit ID. Read local records with
`bot.moderation.audit(server_id, limit=50)`. A network failure records
failed_or_unknown, because remote success cannot always be determined. Failed
actions are not automatically retried. Audit history is local application data;
back it up and control access. This is a focused helper API, not a case-management
system or a preinstalled moderation command pack.

### Packs and installed plugin discovery

A pack is a synchronous function accepting bot and registering commands/hooks:

```python
def utilities(bot):
    @bot.command(category="Utilities")
    def ping():
        return "Pong!"

bot.use(utilities)
print(bot.discover_plugins())
# bot.use("trusted-installed-pack")
```

Installed distributions can declare `[project.entry-points."discord_bot_maker.packs"]`
with `utilities = "my_package:utilities"`. Discovery lists names without importing
plugins; use(name) explicitly loads and executes one installed entry point.
Duplicate installation is rejected. Plugins run trusted Python with the bot's
privileges; there is no sandbox or marketplace. Registration errors propagate;
a failed pack may have registered earlier commands, so discard that bot instance
and fix the pack before retrying.

### Versioned per-server settings

```python
from discord_bot_maker import Settings

schema = Settings(2, {"welcome": "Hello", "enabled": True}, migrations={
    1: lambda old: {"welcome": old["greeting"], "enabled": True},
})
settings = bot.settings(123, schema)
settings.update(welcome="Welcome!")
print(settings.get())
```

Defaults provide key/type validation; an optional validate(values) callable can
raise ValueError for domain rules. Migrations map an old version to the next
version and return a new dictionary. Reads/updates migrate transactionally;
failed migrations roll back. Older code cannot open a newer settings document.
Versions start at 1. Server scopes are isolated, and defaults are copied on read.
This extends SQLite storage; optional PostgreSQL support remains deferred.

### Durable jobs

```python
@bot.job("announcement")
async def announcement(payload):
    await bot.send(payload["channel"], payload["text"])

job_id = bot.jobs.schedule("announcement", delay=60,
                           payload={"channel": 123, "text": "Hello!"}, retries=3)
print(bot.jobs.status(job_id))
# bot.jobs.cancel(job_id)
```

Named handlers are registered in Python before startup; JSON payloads and job
state persist in SQLite. Jobs run one at a time, retry failures with bounded
exponential backoff, and recover running work after a restart. retries is the
number of additional attempts, from 0 to 10. Unknown restored handlers fail and
use the same retry budget. status reports pending/running/done/failed/cancelled
and attempt count. Completed records are retained; applications own retention.

Use one bot process per SQLite file. Delivery is at least once: a crash after an
external side effect can cause replay. Make handlers idempotent using your own
business identifier. Cancellation prevents pending execution and requests
cancellation of running async handlers; it cannot undo side effects or stop a
synchronous function already running in a worker thread. Shutdown leaves
interrupted work retryable. This is not a distributed scheduler. Existing
`bot.every()` and reminders remain available.

### Offline simulator

```python
from discord_bot_maker import Simulator

async def test_add():
    async with Simulator(bot) as sim:
        result = await sim.command("add", options={"first": 2})
        assert result.content.endswith(": 3")
        sim.advance(3)
        result = await sim.command("add", mode="prefix", arguments="2 3")
        assert result.content.endswith(": 5")
```

Use an offline bot with `storage=":memory:"` or a temporary file. Simulator calls
production command, prefix parser, hook and component callbacks without connecting
to Discord. Pass user_id/server_id/channel_id, roles, permissions and age_restricted
to simulate a caller. `sim.click(result, index, value=...)` invokes a button or
dropdown; `sim.submit(result, {"input": "value"})` submits a form;
`sim.event(name, *raw_objects)` invokes hooks; `sim.expire(result)` expires a view.
The controllable clock affects command cooldowns. Jobs expose run_pending() for
offline execution; it executes real handlers and does not simulate wall-clock time.

Simulator records sent payloads in result.messages and exposes result.view/modal.
It does not emulate Discord networking, cache, role objects, or all gateway event
semantics. Hooks take caller-supplied fake objects. Your callback code still runs:
mock external services and never use a live bot's storage or credentials. The
simulator does not intercept arbitrary network calls made by application code.
Close the bot client after tests; simulator cleanup stops views and restores the
clock but leaves the bot available for further tests.

### Operations and registration previews

`bot.validate_config()` runs offline and returns a credential-free summary.
`configure_logging()` opts the package logger into JSON records without changing
application/root logging. `bot.health()` returns ready/closed/background_tasks.
`bot.health_check(host="127.0.0.1", port=8080)` opts into GET /health: 200 when
connected, otherwise 503. This is a readiness probe, not a storage/service audit.
Do not expose the endpoint publicly unless your deployment requires it.

`bot.run()` handles SIGTERM on supported platforms/main threads, cancels managed
background tasks, closes storage and disconnects. Synchronous application callbacks
cannot be forcibly stopped; use cancellable async I/O for long operations.

```python
import json

# Fully offline: remote_snapshot is a previously saved list of Discord payloads.
print(json.dumps(bot.sync_preview(remote_snapshot), indent=2))

# Authenticated read-only inspection, without starting/synchronizing a live bot:
async def inspect_registration():
    async with bot.client:
        await bot.client.login(bot.token)
        print(json.dumps(await bot.fetch_sync_preview(), indent=2))
```

Previews include scope, command type/name, action (add/change/remove/unchanged),
and complete normalized before/after registration payloads. Option order remains
significant. Only Discord-generated IDs/versions and equivalent empty/default
fields are normalized. The target is the configured test server or global scope,
matching `bot.run(sync=True)`. A server preview uses the global authoring commands
that the managed client copies to that server during synchronization.

Inspect removals carefully: synchronization replaces the selected scope, including
commands created by other tools. Server-specific remote commands outside the
local authoring set are shown as removals. App-configured implicit context/install
defaults can appear as payload differences; the preview does not modify app-level
settings. Localization translators and manually managed guild-specific command
trees are outside this facade's preview contract. Permissions set separately via
Discord's command-permission endpoints are not registration payload changes.
Remote state can change between preview and sync; fetch a fresh preview before
synchronizing. No command sync occurs during preview or offline tests.

Generate standalone deployment files with:

```sh
discord-bot-maker scaffold --output ./my-bot
```

This creates bot.py, requirements.txt, Dockerfile, compose.yaml, ignore files and
setup instructions without overwriting files. The Compose resource works as a
Coolify starting point with environment credentials, a persistent data volume,
one replica, readiness checks and SIGTERM shutdown. The 2.1.0 pin requires that
release to exist before a normal registry image build. Generated templates still
need a real container smoke test in the deployment environment.

### Compatibility and deliberate limits

New features are optional. Legacy DBot, slash-only authoring, Store, reminders,
and static graph export retain their interfaces. Rich embeds beyond graph schema
capabilities, Python callbacks, hooks, jobs and interactive responses reject JSON
graph export instead of silently losing behavior. Existing simple embeds still
export. PostgreSQL storage, restart-persistent views, distributed execution and a
plugin marketplace are deferred. Live Discord integration and container deployment
must be verified separately; offline tests do not certify production operation.

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

After publishing 2.1.0, install the [stable release on PyPI](https://pypi.org/project/discord-bot-maker/) with:

```sh
python -m pip install --upgrade 'discord-bot-maker==2.1.0'
```

See the [release guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/releasing.md),
[changelog](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/CHANGELOG.md), and
[v1 migration guide](https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/migration.md).
Only the Python package is being prepared for PyPI; the web app is a separate work in progress.
