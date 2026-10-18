"""Response handling kept behind the package's small public API."""

import asyncio
import io
import inspect
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import discord

from .definition import VARIABLES, VARIABLE_PATTERN
from .flow import context_from
from .responses import Modal, Embed, Message, Poll, Response, UserError
from .storage import Store

if TYPE_CHECKING:
    from .dbot import Bot

logger = logging.getLogger(__name__)


async def invoke(function: Callable, *args, **kwargs):
    """Run normal functions off the gateway thread; also accept async handlers."""
    if inspect.iscoroutinefunction(function):
        return await function(*args, **kwargs)
    result = await asyncio.to_thread(function, *args, **kwargs)
    return await result if inspect.isawaitable(result) else result


def validate_template(text: str):
    unknown = set(VARIABLE_PATTERN.findall(text)) - VARIABLES
    if unknown:
        raise ValueError(f"Unknown reply variables: {', '.join(sorted(unknown))}.")
    remaining = VARIABLE_PATTERN.sub("", text)
    if "{{" in remaining or "}}" in remaining:
        raise ValueError("Use balanced {{variable.name}} placeholders.")


@dataclass
class CommandContext:
    """Command data plus scoped storage, responding and reminder helpers."""

    bot: "Bot"
    interaction: discord.Interaction
    private: bool = False
    _responded: bool = False
    _policy: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def user(self) -> discord.User | discord.Member:
        return self.interaction.user

    @property
    def server(self) -> discord.Guild | None:
        return self.interaction.guild

    @property
    def channel(self):
        return self.interaction.channel

    @property
    def store(self) -> Store:
        """Server-scoped storage; direct messages are isolated by user instead."""
        if self.interaction.guild_id:
            return self.bot.store.scope("server", self.interaction.guild_id)
        return self.bot.store.scope("dm", self.user.id)

    @property
    def user_store(self) -> Store:
        """Storage isolated to the current user within the current server."""
        return self.store.scope("user", self.user.id)

    def render(self, text: str, limit: int = 2000) -> str:
        validate_template(text)
        context = context_from(self.user, self.channel, self.server)
        values = context.variables()
        result = VARIABLE_PATTERN.sub(lambda match: str(values[match.group(1)]), text)
        if not result or len(result) > limit:
            raise UserError(f"The response must contain 1–{limit} characters after inserting variables.")
        return result

    async def respond(self, response: Response) -> None:
        """Send a response. Return None from the handler to avoid a second reply."""
        await send_response(self, response)
        self._responded = True

    def remind_in(self, minutes: int, message: str) -> str:
        """Persist a reminder to this channel and return its cancellation ID."""
        return self.bot._schedule_reminder(self, minutes, message)


async def private_reply(interaction: discord.Interaction, text: str):
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
    else:
        await interaction.response.send_message(text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


async def command_error(context: CommandContext, text: str):
    """Keep details private even after acknowledging a public command.

    Discord fixes the first deferred followup's visibility. Complete that
    public acknowledgement with a generic notice before sending private details.
    """
    if not getattr(context.interaction, "is_prefix", False) and context.interaction.response.is_done() and not context.private and not context._responded:
        await context.respond("I couldn’t complete that command. Check the private message below.")
    await private_reply(context.interaction, text)


def make_embed(context: CommandContext, embed: Embed) -> discord.Embed:
    result = discord.Embed(
        title=context.render(embed.title, 256),
        description=context.render(embed.description, 4096) if embed.description else "",
        color=int(embed.color[1:], 16),
    )
    if embed.image_url:
        result.set_image(url=embed.image_url)
    if embed.thumbnail_url:
        result.set_thumbnail(url=embed.thumbnail_url)
    if embed.url:
        result.url = embed.url
    if embed.footer:
        result.set_footer(text=context.render(embed.footer, 2048))
    for name, value, inline in embed.fields:
        result.add_field(name=context.render(name, 256), value=context.render(value, 1024), inline=inline)
    if len(result) > 6000:
        raise UserError("Rendered embed text exceeds 6000 characters.")
    return result


class _ExpiringView(discord.ui.View):
    def __init__(self, context, timeout):
        super().__init__(timeout=timeout)
        self.context = context
        self.message = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                logger.info("Could not disable an expired view's buttons.")

    async def on_error(self, interaction, error, item):
        context = CommandContext(self.context.bot, interaction, private=True)
        context._policy = self.context._policy
        await self.context.bot._handle_error(context, error)


class ButtonsView(_ExpiringView):
    def __init__(self, context: CommandContext, message: Message, policy):
        super().__init__(context, message.timeout)
        self.owner_only = message.owner_only
        self.policy = policy
        for definition in message.buttons:
            button = discord.ui.Button(label=definition.label, url=definition.url, style=discord.ButtonStyle.link if definition.url else getattr(discord.ButtonStyle, definition.style))
            if not definition.url:
                button.callback = self._callback(definition.reply, defer=definition.defer)
            self.add_item(button)
        for definition in message.selects:
            select = discord.ui.Select(placeholder=definition.placeholder, options=[discord.SelectOption(label=value) for value in definition.options])
            async def selected(interaction, definition=definition, select=select):
                async def action(ctx):
                    return await invoke(definition.callback, ctx, select.values[0])
                await self._callback(action)(interaction)
            select.callback = selected
            self.add_item(select)

    def _callback(self, action, *, defer=True):
        async def callback(interaction):
            if self.is_finished():
                await private_reply(interaction, "This button has expired. Run the command again.")
                return
            if self.owner_only and interaction.user.id != self.context.user.id:
                await private_reply(interaction, "This button belongs to the person who ran the command.")
                return
            if not await self.context.bot._authorize(interaction, **self.policy):
                return
            context = CommandContext(self.context.bot, interaction, private=True)
            context._policy = self.policy
            if defer:
                await interaction.response.defer(ephemeral=True, thinking=True)
            try:
                result = await invoke(action, context) if callable(action) else action
                if result is not None:
                    await context.respond(result)
                elif not context._responded:
                    await context.respond("Done.")
            except Exception as error:
                await self.context.bot._handle_error(context, error)
        return callback


class PollView(_ExpiringView):
    def __init__(self, context: CommandContext, poll: Poll, policy):
        super().__init__(context, poll.timeout)
        self.poll, self.policy = poll, policy
        self.votes: dict[int, int] = {}
        self.lock = asyncio.Lock()
        for index, choice in enumerate(poll.choices):
            button = discord.ui.Button(label=choice, style=discord.ButtonStyle.secondary)
            button.callback = self._vote(index)
            self.add_item(button)

    def embed(self):
        counts = [sum(value == index for value in self.votes.values()) for index in range(len(self.poll.choices))]
        return discord.Embed(title=self.poll.question, description="\n".join(f"{choice} — **{count}**" for choice, count in zip(self.poll.choices, counts)), color=0xFF7A30).set_footer(text="One vote each · click another option to change your vote")

    def _vote(self, index):
        async def callback(interaction):
            if self.is_finished():
                await private_reply(interaction, "This poll has ended.")
                return
            if not await self.context.bot._authorize(interaction, **self.policy):
                return
            async with self.lock:
                previous = self.votes.get(interaction.user.id)
                self.votes[interaction.user.id] = index
                try:
                    await interaction.response.edit_message(embed=self.embed(), view=self)
                except Exception:
                    if previous is None:
                        self.votes.pop(interaction.user.id, None)
                    else:
                        self.votes[interaction.user.id] = previous
                    raise
        return callback


class ModalView(discord.ui.Modal):
    def __init__(self, context, definition):
        super().__init__(title=definition.title, timeout=definition.timeout)
        self.context, self.definition = context, definition
        for item in definition.inputs:
            self.add_item(discord.ui.TextInput(label=item.label, custom_id=item.name, required=item.required, max_length=item.max_length, style=discord.TextStyle.paragraph if item.paragraph else discord.TextStyle.short))

    async def on_submit(self, interaction):
        if interaction.user.id != self.context.user.id:
            await private_reply(interaction, "This form belongs to the person who opened it.")
            return
        if not await self.context.bot._authorize(interaction, **self.context._policy):
            return
        context = CommandContext(self.context.bot, interaction, private=True)
        context._policy = self.context._policy
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            values = {item.custom_id: item.value for item in self.children}
            result = await invoke(self.definition.callback, context, values)
            if result is not None:
                await context.respond(result)
            elif not context._responded:
                await context.respond("Done.")
        except Exception as error:
            await self.context.bot._handle_error(context, error)

    async def on_error(self, interaction, error):
        await self.context.bot._handle_error(CommandContext(self.context.bot, interaction, private=True), error)


async def send_response(context: CommandContext, response: Response):
    from .help import Help, HelpView
    view = None
    policy = getattr(context, "_policy", {})
    kwargs: dict[str, Any] = {"allowed_mentions": context.bot.config.allowed_mentions}
    if isinstance(response, Modal):
        if getattr(context.interaction, "is_prefix", False):
            raise UserError("Forms require a slash command or button interaction.")
        if context.interaction.response.is_done():
            raise UserError("Forms require @bot.command(defer=False) and an immediate response.")
        await context.interaction.response.send_modal(ModalView(context, response))
        return
    if isinstance(response, Help):
        view = HelpView(context, response)
        kwargs["embed"] = view.embed(context.interaction)
    elif isinstance(response, str):
        kwargs["content"] = context.render(response)
    elif isinstance(response, Embed):
        kwargs["embed"] = make_embed(context, response)
    elif isinstance(response, Message):
        if response.content:
            kwargs["content"] = context.render(response.content)
        if response.embed:
            kwargs["embed"] = make_embed(context, response.embed)
        if response.attachments:
            kwargs["files"] = [discord.File(io.BytesIO(item.data), filename=item.filename) for item in response.attachments]
        if response.buttons or response.selects:
            view = ButtonsView(context, response, policy)
    elif isinstance(response, Poll):
        poll = Poll(context.render(response.question, 256), [context.render(choice, 60) for choice in response.choices], response.timeout)
        view = PollView(context, poll, policy)
        kwargs["embed"] = view.embed()
    else:
        raise TypeError("Commands must return text, Embed, Message, Poll, or None after ctx.respond().")
    if view:
        kwargs["view"] = view
    try:
        if context.interaction.response.is_done():
            message = await context.interaction.followup.send(**kwargs, ephemeral=context.private, wait=True)
        else:
            await context.interaction.response.send_message(**kwargs, ephemeral=context.private)
            message = await context.interaction.original_response() if view else None
        if view:
            view.message = message
    except BaseException:
        if view:
            view.stop()
        raise
