"""High-level command authoring, with Discord lifecycle details kept internal."""

import asyncio
import inspect
import logging
import math
import random
import time
from pathlib import Path
from typing import Any, Callable, TypeVar, get_type_hints

import discord
from discord import app_commands
from discord.ext import commands

from .config import parse_id, read_env
from .definition import BotDefinition, Trigger
from .interactions import CommandContext, command_error, invoke, private_reply, validate_template
from .reminders import ReminderQueue
from .responses import Embed, Message, Poll, Response, UserError
from .storage import Store

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])
B = TypeVar("B", bound="Features")


class ManagedClient(commands.Bot):
    def __init__(self, owner, **kwargs):
        self.dbm = owner
        super().__init__(**kwargs)

    async def setup_hook(self):
        if self.dbm._sync_commands:
            if self.dbm.guild_id:
                guild = discord.Object(id=self.dbm.guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            else:
                await self.tree.sync()
        for callback in self.dbm._schedules:
            self.dbm._background.add(asyncio.create_task(self.dbm._run_schedule(*callback)))
        if self.dbm._reminders_enabled:
            self.dbm._background.add(asyncio.create_task(self.dbm._run_reminders()))

    async def on_member_join(self, member):
        welcome = self.dbm._welcome
        if welcome is None or (self.dbm.guild_id and member.guild.id != self.dbm.guild_id):
            return
        channel_id, response = welcome
        channel = self.get_channel(channel_id) or await self.fetch_channel(channel_id)
        if getattr(channel, "guild", None) != member.guild:
            logger.warning("Welcome channel does not belong to the joining member's server.")
            return
        from .flow import context_from
        from .definition import VARIABLE_PATTERN
        values = context_from(member, channel, member.guild).variables()
        text = VARIABLE_PATTERN.sub(lambda match: str(values[match.group(1)]), response)
        if len(text) > 2000:
            logger.warning("Welcome message exceeds Discord's rendered limit.")
            return
        await channel.send(text, allowed_mentions=discord.AllowedMentions.none())

    async def close(self):
        for task in self.dbm._background:
            task.cancel()
        if self.dbm._background:
            await asyncio.gather(*self.dbm._background, return_exceptions=True)
        self.dbm._background.clear()
        self.dbm.store.close()
        await super().close()


class Features:
    """Public helpers mixed into Bot while preserving its original prefix API."""

    def _init_features(self, *, guild_id=None, channel_id=None, storage="data/bot.sqlite3", slash_only=False):
        self.guild_id = parse_id(guild_id, "Server ID")
        self.channel_id = parse_id(channel_id, "Channel ID")
        self.slash_only = slash_only
        self.store = Store(storage)
        self._sync_commands = False
        self._background: set[asyncio.Task] = set()
        self._schedules = []
        self._welcome = None
        self._reminders_enabled = False
        self._queue = ReminderQueue(self.store)
        self._custom_commands: set[str] = set()
        self._static_replies: dict = {}
        self._policies: dict = {}
        self._cooldowns: dict = {}

    @classmethod
    def from_env(cls: type[B], path: str | Path = ".env", *, guild_id: int | str | None = None, channel_id: int | str | None = None, storage: str | Path = "data/bot.sqlite3") -> B:
        """Create a slash-only bot from .env. Explicit IDs override env settings."""
        values = read_env(path)
        return cls(
            token=values["DISCORD_BOT_TOKEN"],
            guild_id=guild_id if guild_id is not None else values["DISCORD_GUILD_ID"],
            channel_id=channel_id if channel_id is not None else values["DISCORD_CHANNEL_ID"],
            storage=storage, slash_only=True, help_command=False,
        )

    async def _authorize(self, interaction, *, permission=None, role_id=None):
        error = None
        if self.guild_id and interaction.guild_id != self.guild_id:
            error = "This command is only available in the configured server."
        elif self.channel_id and interaction.channel_id != self.channel_id:
            error = f"Try this command in <#{self.channel_id}>."
        elif permission and not getattr(interaction.permissions, permission, False):
            error = f"You need the {permission.replace('_', ' ')} permission to use this command."
        elif role_id and role_id not in {role.id for role in getattr(interaction.user, "roles", [])}:
            error = "You do not have the role required for this command."
        if error:
            await private_reply(interaction, error)
            return False
        return True

    def command(self, name: str | None = None, *, description: str | None = None, private: bool = False, cooldown: float = 0, permission: str | None = None, role_id: int | str | None = None) -> Callable[[F], F]:
        """Register a slash command from a normal or async Python function.

        Type annotated parameters become Discord options. A leading `ctx`
        parameter receives CommandContext and is not shown as an option. Return
        str, Embed, Message or Poll; response deferral and errors are managed.
        """
        if not math.isfinite(cooldown) or not 0 <= cooldown <= 86400:
            raise ValueError("Cooldown must be between 0 and 86400 seconds.")
        if permission and permission not in discord.Permissions.VALID_FLAGS:
            raise ValueError(f"Unknown Discord permission: {permission}.")
        role_id = parse_id(role_id, "Role ID")

        def register(function: F) -> F:
            command_name = name or function.__name__
            command_description = description or (inspect.getdoc(function) or "A bot command").splitlines()[0]
            Trigger(id="check", name=command_name, description=command_description)
            client = self._require_client()
            if client.tree.get_command(command_name) or command_name in self.command_definitions or client.get_command(command_name):
                raise ValueError(f"Command {command_name!r} already exists. Choose another name.")
            signature = inspect.signature(function)
            parameters = list(signature.parameters.values())
            inject_context = bool(parameters and parameters[0].name in {"ctx", "context"})
            if inject_context:
                parameters = parameters[1:]
            try:
                hints = get_type_hints(function)
            except (NameError, TypeError) as error:
                raise ValueError(f"Cannot resolve annotations for {command_name!r}. Use supported built-in option types.") from error
            visible = []
            for parameter in parameters:
                if parameter.kind not in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}:
                    raise ValueError("Commands cannot use positional-only, *args or **kwargs options.")
                annotation = hints.get(parameter.name, parameter.annotation)
                if annotation is inspect.Parameter.empty:
                    raise ValueError(f"Add a type annotation to option {parameter.name!r}, for example : str or : int.")
                visible.append(parameter.replace(annotation=annotation))
            policy = {"permission": permission, "role_id": role_id}

            async def callback(interaction, **options):
                if not await self._authorize(interaction, **policy):
                    return
                now = time.monotonic()
                key = (command_name, interaction.guild_id, interaction.user.id)
                if self._cooldowns.get(key, 0) > now:
                    await private_reply(interaction, "This command is on cooldown. Try again shortly.")
                    return
                if cooldown:
                    self._cooldowns = {key: expiry for key, expiry in self._cooldowns.items() if expiry > now}
                    if len(self._cooldowns) >= 10000:
                        await private_reply(interaction, "The bot is busy. Try again shortly.")
                        return
                    self._cooldowns[key] = now + cooldown
                context = CommandContext(self, interaction, private=private)
                context._policy = policy
                await interaction.response.defer(ephemeral=private, thinking=True)
                try:
                    arguments = signature.bind_partial(*([context] if inject_context else []), **options)
                    arguments.apply_defaults()
                    result = await invoke(function, *arguments.args, **arguments.kwargs)
                    if result is not None:
                        await context.respond(result)
                    elif not context._responded:
                        await context.respond("Done.")
                except UserError as error:
                    await command_error(context, str(error))
                except Exception as error:
                    logger.error("Command %s failed (%s).", command_name, type(error).__name__)
                    await command_error(context, "That command could not be completed. Please try again.")

            callback.__signature__ = inspect.Signature([inspect.Parameter("interaction", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=discord.Interaction), *visible])
            client.tree.add_command(app_commands.Command(name=command_name, description=command_description, callback=callback))
            self._custom_commands.add(command_name)
            self._policies[command_name] = policy
            return function
        return register

    def reply(self: B, name: str, response: str | Embed | Message, *, description: str = "A bot command", private: bool = False, cooldown: int = 0) -> B:
        """Create a slash command with a fixed response; {{variables}} are supported."""
        if not isinstance(response, (str, Embed, Message)):
            raise TypeError("reply() accepts text, Embed or Message. Use @bot.command() for computed replies.")
        if type(cooldown) is not int:
            raise ValueError("Fixed reply cooldowns must be whole seconds.")
        if isinstance(response, str):
            if not 1 <= len(response) <= 2000:
                raise ValueError("Reply text must contain 1–2000 characters.")
            validate_template(response)
        elif isinstance(response, Embed):
            validate_template(response.title)
            validate_template(response.description)
        else:
            validate_template(response.content)
            if response.embed:
                validate_template(response.embed.title)
                validate_template(response.embed.description)
        def fixed_reply():
            return response
        self.command(name, description=description, private=private, cooldown=cooldown)(fixed_reply)
        if not isinstance(response, Message):
            self._custom_commands.remove(name)
            self._static_replies[name] = (response, description, private, cooldown)
        return self

    def random_reply(self: B, name: str, responses: list[str] | tuple[str, ...], *, description: str = "A random reply", cooldown: float = 0) -> B:
        """Create a command that chooses a response each time it is invoked."""
        if isinstance(responses, str):
            raise ValueError("Pass a list or tuple of replies, not a single string.")
        choices = tuple(responses)
        if not choices or any(not isinstance(value, str) or not 1 <= len(value) <= 2000 for value in choices):
            raise ValueError("Provide at least one reply containing 1–2000 characters.")
        for text in choices:
            validate_template(text)
        def choose():
            return random.choice(choices)
        self.command(name, description=description, cooldown=cooldown)(choose)
        return self

    def poll(self: B, name: str = "poll") -> B:
        """Add /poll question choices, with choices separated by |."""
        def create_poll(question: str, choices: str):
            return Poll(question, [value.strip() for value in choices.split("|")])
        self.command(name, description="Start a quick poll", cooldown=10)(create_poll)
        return self

    def reminders(self: B) -> B:
        """Add /remind, /reminders and /cancel_reminder with restart-safe storage."""
        client = self._require_client()
        for name in ("remind", "reminders", "cancel_reminder"):
            if client.tree.get_command(name) or client.get_command(name) or name in self.command_definitions:
                raise ValueError(f"Command {name!r} already exists.")
        def remind(ctx: CommandContext, minutes: int, message: str):
            reminder_id = ctx.remind_in(minutes, message)
            return f"I’ll remind you in {minutes} minute(s). Reminder ID: `{reminder_id}`."
        def list_reminders(ctx: CommandContext):
            rows = self._queue.pending(ctx.user.id, ctx.interaction.guild_id)
            return "\n".join(f"`{row['id']}` · <t:{int(row['due'])}:R> · {row['message'][:45]}" for row in rows) or "You have no pending reminders."
        def cancel(ctx: CommandContext, reminder_id: str):
            if not self._queue.cancel(reminder_id, ctx.user.id, ctx.interaction.guild_id):
                raise UserError("Pending reminder not found, or it is already being delivered.")
            return "Reminder cancelled."
        self.command("remind", description="Set a reminder in this channel", private=True, cooldown=3)(remind)
        self.command("reminders", description="List your pending reminders", private=True)(list_reminders)
        self.command("cancel_reminder", description="Cancel one of your reminders", private=True)(cancel)
        self._reminders_enabled = True
        return self

    def _schedule_reminder(self, context, minutes, message):
        if not self._reminders_enabled:
            raise RuntimeError("Enable bot.reminders() before scheduling reminders.")
        return self._queue.add(context.user.id, context.interaction.guild_id, context.interaction.channel_id, minutes, message)

    async def _deliver_reminder(self, job):
        channel = self.client.get_channel(int(job["channel_id"])) or await self.client.fetch_channel(int(job["channel_id"]))
        # Never deliver stored content into a different server after a configuration change.
        if str(getattr(getattr(channel, "guild", None), "id", "")) != job["server_id"]:
            raise ValueError("Reminder channel no longer matches its server.")
        await channel.send(f"<@{job['user_id']}> ⏰ {job['message']}", allowed_mentions=discord.AllowedMentions(users=[discord.Object(id=int(job["user_id"]))], roles=False, everyone=False, replied_user=False))

    async def _run_reminders(self):
        await self.client.wait_until_ready()
        while True:
            try:
                job = await asyncio.to_thread(self._queue.claim)
                if job:
                    try:
                        await asyncio.wait_for(self._deliver_reminder(job), timeout=30)
                        await asyncio.to_thread(self._queue.finish, job["id"], True)
                    except asyncio.CancelledError:
                        raise
                    except Exception as error:
                        logger.warning("Reminder delivery failed (%s).", type(error).__name__)
                        await asyncio.to_thread(self._queue.finish, job["id"], False, job["attempts"])
                    continue
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.warning("Reminder storage failed (%s).", type(error).__name__)
            await asyncio.sleep(5)

    def welcome(self: B, channel_id: int | str, message: str = "Welcome, {{user.display_name}}!") -> B:
        """Greet joining members; enable Server Members Intent in the portal."""
        if not 1 <= len(message) <= 2000:
            raise ValueError("Welcome messages must contain 1–2000 characters.")
        validate_template(message)
        channel_id = parse_id(channel_id, "Welcome channel ID")
        if channel_id is None:
            raise ValueError("A welcome channel ID is required.")
        if self._require_client().is_ready():
            raise RuntimeError("Configure welcome messages before starting the bot.")
        # discord.py exposes a copy through client.intents. Retain and update
        # the actual Intents object supplied when creating the connection.
        self._gateway_intents.members = True
        self._welcome = (channel_id, message)
        return self

    def every(self, *, seconds: float, channel_id: int | str) -> Callable[[F], F]:
        """Send a handler's text/Embed result at a fixed interval while online."""
        if not math.isfinite(seconds) or not 1 <= seconds <= 86400:
            raise ValueError("Scheduled intervals must be between 1 second and 1 day.")
        channel_id = parse_id(channel_id, "Scheduled channel ID")
        if channel_id is None:
            raise ValueError("A scheduled channel ID is required.")
        def register(function: F) -> F:
            if inspect.signature(function).parameters:
                raise ValueError("Scheduled functions take no parameters.")
            self._schedules.append((seconds, channel_id, function))
            return function
        return register

    async def send(self, channel_id: int | str, response: str | Embed):
        """Send text or an embed to an explicit channel from an async handler."""
        channel_id = parse_id(channel_id, "Channel ID")
        if channel_id is None:
            raise ValueError("A channel ID is required.")
        channel = self.client.get_channel(channel_id) or await self.client.fetch_channel(channel_id)
        if isinstance(response, str):
            if not 1 <= len(response) <= 2000:
                raise ValueError("Scheduled messages must contain 1–2000 characters.")
            return await channel.send(response, allowed_mentions=discord.AllowedMentions.none())
        if not isinstance(response, Embed):
            raise TypeError("send() accepts text or Embed.")
        embed = discord.Embed(title=response.title, description=response.description, color=int(response.color[1:], 16))
        if response.image_url:
            embed.set_image(url=response.image_url)
        return await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    async def _run_schedule(self, seconds, channel_id, function):
        await self.client.wait_until_ready()
        while True:
            await asyncio.sleep(seconds)
            try:
                result = await invoke(function)
                if result is not None:
                    await self.send(channel_id, result)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.warning("Scheduled action failed (%s).", type(error).__name__)

    def _export_replies(self, name):
        if self._custom_commands or self._schedules or self._welcome:
            raise ValueError("Python handlers, interactive responses and background actions cannot be exported as a JSON graph. Keep their Python source.")
        from .migration import migrate_commands
        prefix = self.prefix if isinstance(self.prefix, str) else self.prefix[0]
        if self.command_definitions:
            data = migrate_commands(self.commDict, name=name, prefix=prefix).model_dump(mode="json")
        else:
            data = {"name": name, "prefix": prefix, "nodes": [], "edges": [], "layout": {"positions": {}}}
        for index, (command, (response, description, private, cooldown)) in enumerate(self._static_replies.items()):
            trigger_id, reply_id = f"slash-{command}", f"response-{command}"
            nodes = [dict(id=trigger_id, kind="trigger", name=command, description=description, cooldown=cooldown, mode="slash")]
            if isinstance(response, Embed):
                from dataclasses import asdict
                nodes.append(dict(id=reply_id, kind="embed", ephemeral=private, **asdict(response)))
            else:
                nodes.append(dict(id=reply_id, kind="reply", content=response, ephemeral=private))
            data["nodes"].extend(nodes)
            data["edges"].append(dict(id=f"edge-{trigger_id}", source=trigger_id, target=reply_id))
            for column, node in enumerate(nodes):
                data["layout"]["positions"][node["id"]] = {"x": 80 + column * 320, "y": index * 220}
        definition = BotDefinition.model_validate(data)
        if self.channel_id:
            data = definition.model_dump(mode="json")
            for trigger in [node for node in data["nodes"] if node["kind"] == "trigger"]:
                edge = next(edge for edge in data["edges"] if edge["source"] == trigger["id"])
                target = edge["target"]
                condition, denied = f"only-{trigger['id']}", f"deny-{trigger['id']}"
                edge["target"] = condition
                data["nodes"].extend([dict(id=condition, kind="condition", field="channel", value=str(self.channel_id)), dict(id=denied, kind="reply", content=f"Try this command in <#{self.channel_id}>.", ephemeral=True)])
                data["edges"].extend([dict(id=f"yes-{trigger['id']}", source=condition, target=target, branch="true"), dict(id=f"no-{trigger['id']}", source=condition, target=denied, branch="false")])
            definition = BotDefinition.model_validate(data)
        return definition
