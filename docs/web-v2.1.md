# Visual builder: 2.1 authoring

The browser edits a validated BotDefinition. The API saves that same document;
ZIP exports and the hosted runner interpret it through the Python 2.1 command
facade. No user Python is evaluated by the API or runner. Existing schema-version-1
documents remain accepted; new optional fields have defaults. Regenerate the
schema and TypeScript after Python model changes, rather than editing generated
contracts. An older package that predates these fields cannot run a new export:
exports require 2.1.1 or later. This checkout prepares 2.1.1 as an unreleased runtime
update. Publish that package version before expecting normal registry installs of
new exports to succeed; use this checkout for offline development until then.

## Commands

Select a Command block, choose Slash / Prefix / Slash + prefix, and set its name,
description, cooldown and category. Both command forms share authorization,
validation and cooldown state. Add typed arguments under Typed command arguments;
optional arguments need a matching default. Text arguments support fixed choices
or autocomplete suggestions. Use `{{options.name}}` in responses. Prefix arguments
are positional; quote text containing spaces. Command names cannot conflict with
enabled help or packs. Private replies are public in prefix mode because prefix
messages cannot be ephemeral.

Permissions & checks supports a Discord permission, server-only, any listed role,
any listed channel, and an age-restricted channel flag. Checks combine with AND;
multiple roles/channels use OR within their own list. Age restriction checks the
channel flag, not a person's age. Interactive callbacks recheck the original
command's policies and the current graph conditions.

## Responses and interactions

Reply blocks send text. Embed blocks support fields, inline fields, footer,
thumbnail, title links and images, with template and total-length validation.
Interactive blocks support five buttons, four dropdowns and ten text attachments.
Buttons either open HTTP(S) links or return a configured response. Dropdown
responses can use `{{input.value}}`. Choose invoker-only access or allow other
users who meet the originating command checks. Interactions have a bounded timeout
and do not survive restarts.

Form blocks have up to five named inputs and a submission response using
`{{input.name}}`. They must be the first response of a slash-only command and end
the flow. The original user owns the form. Files are generated from text, not
uploaded binary files; arbitrary callback logic is a Python API capability.

## Bot configuration

Expand Bot configuration & features below the canvas. Configure playing presence,
availability, privileged intents and allowed mentions. Prefix commands/message
hooks enable message-content intent; member hooks enable members intent. The same
privileged capabilities must also be enabled in the Discord Developer Portal.
Mentions default to disabled.

Searchable help registers a permission-filtered /help (and prefix help when prefix
commands exist), with category selection and pagination. Built-in command packs
register polls, reminders and confirmed moderation commands. The moderation pack's
timeout command uses ten minutes; use an Action block for a configurable timeout.
Custom installed Python entry points are not loaded from web project data.

## Event hooks

Message hooks match a whole message or substring, case-insensitively, optionally
restricted to a channel. Member hooks send a greeting to a required channel and
can assign a role after permission/hierarchy checks. Reaction hooks match an emoji
and optional channel, using cached reaction events. Responses accept ordinary
user/server/channel/message variables. Bot messages and bot reactions are excluded.

Use Simulate an event hook in the test panel to test a match and response. A
simulated auto-role is an explanation of the requested role, not proof of live
permission or hierarchy availability. No event is sent to Discord.

## Actions and settings

Action blocks can read/write server data or increment a server counter. Values
are JSON-decoded when possible, otherwise stored as text. Increment values must be
integers. Use `{{store.value}}` in the action's response. Direct-message data is
isolated by user.

Versioned server settings have a schema version, named typed defaults and optional
old-key=new-key rename migrations. Migrations advance one version at a time and
run transactionally on first access. Newer stored settings cannot be opened by
older schemas. Use `{{settings.name}}` in command responses. Read/update setting
actions use the configured key; updates additionally require Manage Server and a
value of the configured type. Boolean/number values use JSON text such as true or
42; changing a setting's type needs deliberate application migration outside the
visual rename-only migration format.

Moderation actions select kick, ban or timeout, a numeric target ID (often
`{{options.member_id}}`), reason and timeout minutes. They end a flow with a
60-second owner-only confirmation. Live execution refreshes member state and
checks caller/bot permissions, hierarchy and protected targets. Local audit
records and the Discord audit reason include an audit ID. Preview renders the
prompt and checks sample caller permissions but never executes moderation or
claims to emulate live hierarchy.

## Scheduled work

Schedule-message actions persist a one-shot message in the current channel and
return a job ID. Cancel-job actions accept an ID and enforce the original user's
ownership within the original server. Recurring announcements have a stable ID,
channel, interval of at least 60 seconds, text and bounded retries. Announcement
text is literal; one-shot actions can interpolate command variables before enqueue.

Jobs persist across restarts, use bounded retries and execute serially. Delivery
is at least once, so a crash can repeat external effects. Explicitly cancelled
recurring jobs stay cancelled across restarts. Renaming/removing recurring IDs
stops obsolete jobs at the next startup. Applications own retention/backups and
can inspect/cancel jobs using the Python API. This is not a distributed scheduler.

## Offline testing

The Test bot panel accepts typed arguments and a slash/prefix mode for dual
commands. Edit sample context for permissions, roles, channel IDs, server/direct
message state and age restriction. Click reply buttons, choose dropdown values
and submit forms in the response preview. A component callback follows current
graph conditions and checks; earlier storage actions are not repeated.

Sample storage/job state is passed explicitly between previews in this browser;
it is not saved to the real bot database. Reset simulation clears it. Event tests
are independent. Command previews do not simulate wall-clock scheduling, retry
backoff, Discord caches, live hierarchy, helper-pack commands or help navigation;
the Python offline tests cover the shared callback/runtime implementations.

## Registration comparison

Expand Command registration preview and paste a previously saved Discord command
registration JSON array. An empty array shows an initial registration. Optional
server ID selects the registration scope without losing snowflake precision.
Comparison includes generated help/pack commands, option metadata, normalized
before/after payloads and add/change/remove/unchanged actions. It never reads a
stored token, connects to Discord or synchronizes commands. Get a fresh remote
snapshot before a real sync; remote registration may change afterward.

## Hosting and exports

Exports preserve new fields and use FlowBot, which delegates commands and
interactions to the managed Python facade. Sync remains explicit. The repository
API/runner must be deployed from this source revision alongside the frontend.
Hosted bots store each project's SQLite database under BOT_DATA_DIR; Compose
mounts a dedicated bot-runtime-data volume with non-root ownership. Keep one
runner/process per bot store and back up that volume. Do not scale independently
onto machines with separate copies of the same bot database.

Structured package logging, existing API/runner/container health checks and
SIGTERM cleanup remain available. The web does not expose arbitrary log injection
or public per-bot health listeners. Custom Python plugins, arbitrary executable
callbacks, persistent views, PostgreSQL bot storage and distributed scheduling
remain outside the visual format. Live Discord and container deployment checks
must be performed separately from offline tests.
