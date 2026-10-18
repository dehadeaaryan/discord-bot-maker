"""Run safe declarative visual definitions through the 2.1 public facade."""
import inspect
import logging
from typing import Literal

import discord

from .dbot import Bot
from .config import BotConfig
from .features import ManagedClient
from .policies import Checks
from .definition import BotDefinition, Trigger, Action
from .engine import Engine
from .context import context_from
from .interactions import CommandContext
from .responses import Attachment, Button, Embed, Message, Modal, Select, TextInput, UserError
from .settings import Settings

logger = logging.getLogger(__name__)


def settings_schema(config):
    migrations = {}
    for migration in config.migrations:
        def migrate(old, rename=dict(migration.rename)):
            for source, target in rename.items():
                if source in old:
                    old[target] = old.pop(source)
            return old
        migrations[migration.from_version] = migrate
    return Settings(config.version, config.defaults, migrations=migrations)


class VisualBot(ManagedClient):
    """A managed Discord client for graph exports and the hosted runner."""

    def __init__(self, definition: BotDefinition, *, sync_commands=False, guild_id=None, storage="data/bot.sqlite3"):
        definition = BotDefinition.model_validate(definition.model_dump(mode="json"))
        config = definition.runtime
        prefix_enabled = any(isinstance(n, Trigger) and n.mode != "slash" for n in definition.nodes)
        intents = discord.Intents.default()
        intents.message_content = prefix_enabled or config.message_content or any(h.event == "message" for h in config.hooks)
        intents.members = config.members or any(h.event == "member_join" for h in config.hooks)
        facade = Bot("offline-placeholder", prefix=definition.prefix, auto_initialize=False, help_command=False, slash_only=not prefix_enabled, guild_id=guild_id, storage=storage, config=BotConfig(intents=intents, presence=config.presence or None, status=config.status, allowed_mentions=discord.AllowedMentions(users=config.mention_users, roles=config.mention_roles, everyone=config.mention_everyone, replied_user=False)))
        super().__init__(facade, command_prefix=definition.prefix, intents=intents, help_command=None, activity=discord.Game(config.presence) if config.presence else None, status=getattr(discord.Status, config.status), allowed_mentions=facade.config.allowed_mentions)
        facade.client = self
        facade._gateway_intents = intents
        facade._sync_commands = sync_commands
        self.engine = Engine(definition, store=facade.store)
        self.guild_id = guild_id
        self.sync_commands = sync_commands
        self._definition = definition
        triggers = [node for node in definition.nodes if isinstance(node, Trigger)]
        for trigger in sorted(triggers, key=lambda node: node.mode == "prefix"):
            self._register(trigger)
        if config.help:
            facade.help(mode="both" if prefix_enabled else "slash", page_size=config.help_page_size)
        for pack in config.packs:
            if pack == "polls":
                facade.poll()
            elif pack == "reminders":
                facade.reminders()
            else:
                self._moderation_pack()
        self._configure_hooks()
        self._recurring = []
        if config.schedules or any(isinstance(n, Action) and n.operation in {"schedule", "cancel_job"} for n in definition.nodes):
            self._configure_jobs()

    def _register(self, trigger):
        async def handler(ctx, **options):
            context = context_from(ctx.user, ctx.channel, ctx.server)
            result = self.engine.execute(trigger.name, context, "prefix" if getattr(ctx.interaction, "is_prefix", False) else "slash", options=options)
            for message in result["messages"]:
                if message["kind"] != "form" and not ctx.interaction.response.is_done():
                    await ctx.interaction.response.defer(ephemeral=message.get("ephemeral", False), thinking=True)
                response = await self._response(ctx, trigger, options, message)
                previous = ctx.private
                ctx.private = message.get("ephemeral", False) and not getattr(ctx.interaction, "is_prefix", False)
                try:
                    await ctx.respond(response)
                finally:
                    ctx.private = previous
        annotations = {}
        parameters = [inspect.Parameter("ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        for option in sorted(trigger.options, key=lambda o: not o.required):
            annotation = {"str": str, "int": int, "float": float, "bool": bool}[option.type]
            if option.choices:
                annotation = Literal[tuple(option.choices)]
            annotations[option.name] = annotation
            parameters.append(inspect.Parameter(option.name, inspect.Parameter.KEYWORD_ONLY, annotation=annotation, default=inspect.Parameter.empty if option.required else option.default))
        handler.__signature__ = inspect.Signature(parameters)
        handler.__annotations__ = annotations
        checks = trigger.checks
        # Engine owns the cross-interface cooldown so simulations and execution agree.
        autocomplete = {}
        for option in trigger.options:
            if option.autocomplete:
                def suggest(ctx, current, values=tuple(option.autocomplete)):
                    return [value for value in values if current.casefold() in value.casefold()]
                autocomplete[option.name] = suggest
        # Legacy graphs can give separate slash/prefix flows the same name.
        # Register the prefix transport under an internal temporary name, then
        # expose the original name without replacing the distinct slash handler.
        registration_name = trigger.name
        separate_prefix = trigger.mode == "prefix" and self.tree.get_command(trigger.name) is not None
        if separate_prefix:
            import hashlib
            registration_name = "prefix_" + hashlib.sha256(trigger.id.encode()).hexdigest()[:20]
        self.dbm.command(registration_name, description=trigger.description, mode=trigger.mode, category=trigger.category, permission=checks.permission, checks=Checks(server_only=checks.server_only, channels=tuple(int(v) for v in checks.channels), roles=tuple(int(v) for v in checks.roles), age_restricted=checks.age_restricted), autocomplete=autocomplete, defer=False)(handler)
        if separate_prefix:
            command = self.remove_command(registration_name)
            command.name = trigger.name
            self.add_command(command)
            self.dbm._commands[registration_name]["name"] = trigger.name
        slash = self.tree.get_command(trigger.name) if trigger.mode != "prefix" else None
        if slash and trigger.options:
            from discord import app_commands
            app_commands.describe(**{o.name: o.description for o in trigger.options})(slash)

    def _callback(self, name):
        return self.tree.get_command(name).callback

    async def _response(self, ctx, trigger, options, message):
        kind = message["kind"]
        if kind == "reply":
            return message["content"]
        if kind == "embed":
            return Embed(message["title"], message["description"], message["color"], message.get("image_url"), fields=tuple((f["name"], f["value"], f["inline"]) for f in message.get("fields", [])), footer=message.get("footer", ""), thumbnail_url=message.get("thumbnail_url"), url=message.get("url"))
        def action(component):
            async def callback(click, value=None):
                data = dict(component, node_id=message["node_id"], owner_id=str(ctx.user.id))
                if value is not None:
                    data["value"] = value
                context = context_from(click.user, click.channel, click.server)
                result = self.engine.execute(trigger.name, context, "slash", options=options, component=data)
                return result["messages"][0]["content"]
            return callback
        if kind == "message":
            return Message(message["content"], buttons=[Button(b["label"], url=b["url"]) if b["url"] else Button(b["label"], reply=action({"type": "button", "index": index}), style=b["style"]) for index, b in enumerate(message["buttons"])], selects=[Select(s["placeholder"], s["options"], action({"type": "select", "index": index})) for index, s in enumerate(message["selects"])], attachments=[Attachment(f["filename"], f["content"].encode()) for f in message["attachments"]], owner_only=message["owner_only"], timeout=message["timeout"])
        if kind == "form":
            async def submit(click, values):
                data = {"node_id": message["node_id"], "type": "form", "inputs": values}
                result = self.engine.execute(trigger.name, context_from(click.user, click.channel, click.server), options=options, component=data)
                return result["messages"][0]["content"]
            return Modal(message["title"], [TextInput(i["name"], i["label"], required=i["required"], max_length=i["max_length"], paragraph=i["paragraph"]) for i in message["inputs"]], submit)
        if message["operation"] == "moderation":
            if not message["target"].isdigit():
                raise UserError("Member ID must be numeric.")
            member = await ctx.server.fetch_member(int(message["target"]))
            helper = getattr(self.dbm.moderation, message["moderation_action"])
            kwargs = {"reason": message["reason"]}
            if message["moderation_action"] == "timeout":
                kwargs["minutes"] = message["minutes"]
            return helper(ctx, member, **kwargs)
        if message["operation"] == "schedule":
            job_id = self.dbm.jobs.schedule("visual:send", delay=message["delay"], retries=message["retries"], payload={"channel_id": str(ctx.channel.id), "server_id": str(ctx.server.id) if ctx.server else "", "owner_id": str(ctx.user.id), "text": message["value"]})
            self.dbm.store.scope("visual-job-owner").set(job_id, [str(ctx.user.id), str(ctx.server.id) if ctx.server else ""])
            return f"Scheduled job: {job_id}"
        job_id = message["value"]
        owner = self.dbm.store.scope("visual-job-owner").get(job_id)
        if owner != [str(ctx.user.id), str(ctx.server.id) if ctx.server else ""]:
            raise UserError("Job not found or owned by another user.")
        return "Job cancelled." if self.dbm.jobs.cancel(job_id) else "Job not found or already finished."

    def _configure_hooks(self):
        for hook in self._definition.runtime.hooks:
            if hook.event == "message":
                # A channel restriction is applied before calling the safe response adapter.
                async def message_event(message, hook=hook):
                    content, match = message.content.casefold(), hook.match.casefold()
                    if (hook.channel_id and str(message.channel.id) != hook.channel_id) or not (content == match if hook.exact else match in content):
                        return
                    from .transport import PrefixInteraction
                    from types import SimpleNamespace
                    ctx = CommandContext(self.dbm, PrefixInteraction(SimpleNamespace(author=message.author, channel=message.channel, guild=message.guild, send=message.channel.send)))
                    await ctx.respond(hook.response)
                self.dbm.on("message")(message_event)
            elif hook.event == "member_join":
                if hook.role_id:
                    self.dbm.auto_role(hook.role_id)
                async def join(member, hook=hook):
                    channel = self.get_channel(int(hook.channel_id)) or await self.fetch_channel(int(hook.channel_id))
                    if getattr(channel, "guild", None) != member.guild:
                        raise UserError("Greeting channel must belong to the joining server.")
                    context = context_from(member, channel, member.guild).variables()
                    from .definition import VARIABLE_PATTERN
                    await channel.send(VARIABLE_PATTERN.sub(lambda m: str(context[m.group(1)]), hook.response), allowed_mentions=self.dbm.config.allowed_mentions)
                self.dbm.on("member_join")(join)
            else:
                async def react(reaction, user, hook=hook):
                    message = reaction.message
                    if str(reaction.emoji) != hook.match or (hook.channel_id and str(message.channel.id) != hook.channel_id):
                        return
                    from .definition import VARIABLE_PATTERN
                    values = context_from(user, message.channel, message.guild).variables()
                    await message.channel.send(VARIABLE_PATTERN.sub(lambda m: str(values[m.group(1)]), hook.response), allowed_mentions=self.dbm.config.allowed_mentions)
                self.dbm.on("reaction_add")(react)

    def _configure_jobs(self):
        @self.dbm.job("visual:send")
        async def send(payload):
            channel = self.get_channel(int(payload["channel_id"])) or await self.fetch_channel(int(payload["channel_id"]))
            if str(getattr(getattr(channel, "guild", None), "id", "")) != payload["server_id"]:
                raise UserError("Job destination does not belong to its original server.")
            await channel.send(payload["text"], allowed_mentions=self.dbm.config.allowed_mentions)
        self._recurring = []
        for schedule in self._definition.runtime.schedules:
            name = f"visual:schedule:{schedule.id}"
            async def recurring(payload, schedule=schedule, name=name):
                channel = self.get_channel(int(schedule.channel_id)) or await self.fetch_channel(int(schedule.channel_id))
                if self.guild_id and getattr(getattr(channel, "guild", None), "id", None) != self.guild_id:
                    raise UserError("Scheduled channel must belong to the configured server.")
                await channel.send(schedule.response, allowed_mentions=self.dbm.config.allowed_mentions)
                next_id = self.dbm.jobs.schedule(name, delay=schedule.seconds, retries=schedule.retries)
                self.dbm.store.scope("visual-schedules").set(schedule.id, next_id)
            self.dbm.job(name)(recurring)
            self._recurring.append((schedule, name))

    async def setup_hook(self):
        # Cancel obsolete recurring definitions, while preserving manual cancellations.
        from pathlib import Path
        database = self.dbm.store._database
        if database.connection is not None or (database.path != ":memory:" and Path(database.path).is_file()):
            with database.transaction() as connection:
                if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dbm_jobs'").fetchone():
                    allowed = {name for _, name in self._recurring}
                    rows = connection.execute("SELECT id,name FROM dbm_jobs WHERE status IN ('pending','running') AND name LIKE 'visual:schedule:%'").fetchall()
                    for job_id, name in rows:
                        if name not in allowed:
                            connection.execute("UPDATE dbm_jobs SET status='cancelled' WHERE id=?", (job_id,))
        for schedule, name in self._recurring:
            existing = self.dbm.store.scope("visual-schedules").get(schedule.id)
            status = self.dbm.jobs.status(existing) if existing else None
            if status is None or status["status"] in {"done", "failed"}:
                job_id = self.dbm.jobs.schedule(name, delay=schedule.seconds, retries=schedule.retries)
                self.dbm.store.scope("visual-schedules").set(schedule.id, job_id)
        await super().setup_hook()

    def _moderation_pack(self):
        for name, permission in (("kick", "kick_members"), ("ban", "ban_members"), ("timeout", "moderate_members")):
            async def moderate(ctx, member_id: str, reason: str, name=name):
                if not member_id.isdigit():
                    raise UserError("Member ID must be numeric.")
                member = await ctx.server.fetch_member(int(member_id))
                helper = getattr(self.dbm.moderation, name)
                return helper(ctx, member, reason=reason, **({"minutes": 10} if name == "timeout" else {}))
            # Bind the action name without exposing it as a command option.
            moderate.__signature__ = inspect.Signature([inspect.Parameter("ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD), inspect.Parameter("member_id", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str), inspect.Parameter("reason", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str)])
            self.dbm.command(name, description=f"{name.capitalize()} a member after confirmation", private=True, category="Moderation", permission=permission, checks=Checks(server_only=True))(moderate)

    def run(self, token, **kwargs):
        self.dbm._manage_signals = True
        return super().run(token, **kwargs)

    async def on_message(self, message):
        if message.author.bot or (self.guild_id and getattr(message.guild, "id", None) != self.guild_id):
            return
        await self.dbm.emit("message", message)
        await self.process_commands(message)

    async def on_ready(self):
        logger.info("Visual bot connected")
        await self.dbm.emit("ready")
