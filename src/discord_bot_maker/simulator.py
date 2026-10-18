"""Offline command/event/component execution using the production callbacks.

Use a bot with storage=':memory:' or a temporary file. Handlers are real Python:
external I/O performed by application callbacks is the application's responsibility.
"""
import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace


@dataclass
class SimulationResult:
    messages: list[dict] = field(default_factory=list)
    view: object = None
    modal: object = None

    @property
    def content(self):
        return self.messages[-1].get("content", "") if self.messages else ""


class Simulator:
    def __init__(self, bot):
        if bot.client.is_ready():
            raise ValueError("Use a separate offline bot for simulation.")
        self.bot = bot
        self.now = 0.0
        self._previous_clock = bot._clock
        bot._clock = lambda: self.now
        self._views = []

    def advance(self, seconds):
        import math
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Advance by a finite nonnegative number of seconds.")
        self.now += seconds

    def interaction(self, *, user_id=1, server_id=10, channel_id=20, roles=(), permissions=(), age_restricted=False):
        result = SimulationResult()
        state = {"done": False}
        user = SimpleNamespace(id=user_id, name="Sam", display_name="Sam", mention=f"<@{user_id}>", bot=False, roles=[SimpleNamespace(id=role) for role in roles])
        guild = SimpleNamespace(id=server_id, name="Test server") if server_id else None
        perms = SimpleNamespace(**{name: True for name in permissions})
        channel = SimpleNamespace(id=channel_id, name="general", guild=guild, is_nsfw=lambda: age_restricted, permissions_for=lambda user: perms)
        async def edit(**kwargs):
            result.messages.append(kwargs)
        message = SimpleNamespace(edit=edit)
        async def send(*args, **kwargs):
            state["done"] = True
            kwargs.pop("wait", None)
            if args:
                kwargs["content"] = args[0]
            result.messages.append(kwargs)
            if "view" in kwargs:
                result.view = kwargs["view"]
                self._views.append(result.view)
            return message
        channel.send = send
        async def defer(**kwargs):
            state["done"] = True
        async def send_modal(modal):
            state["done"] = True
            result.modal = modal
            self._views.append(modal)
        async def original_response():
            return message
        interaction = SimpleNamespace(user=user, guild=guild, guild_id=server_id, channel=channel, channel_id=channel_id, permissions=perms, response=SimpleNamespace(is_done=lambda: state["done"], defer=defer, send_message=send, edit_message=edit, send_modal=send_modal), followup=SimpleNamespace(send=send), original_response=original_response)
        return interaction, result

    async def command(self, name, *, mode="slash", arguments="", options=None, **identity):
        interaction, result = self.interaction(**identity)
        definition = self.bot._commands.get(name)
        if definition is None:
            raise ValueError("Unknown facade command.")
        if mode not in {"slash", "prefix"} or definition["mode"] not in {mode, "both"}:
            raise ValueError("Command does not support this mode.")
        if mode == "slash":
            await definition["callback"](interaction, **(options or {}))
        else:
            context = SimpleNamespace(author=interaction.user, guild=interaction.guild, channel=interaction.channel, send=interaction.followup.send)
            await self.bot.client.get_command(name).callback(context, arguments=arguments)
        return result

    async def click(self, result, index=0, *, value=None, **identity):
        view = result.view
        if view is None or not 0 <= index < len(view.children):
            raise ValueError("No such component.")
        interaction, clicked = self.interaction(**identity)
        child = view.children[index]
        if getattr(child, "disabled", False):
            raise ValueError("This component is disabled.")
        if getattr(child, "url", None):
            raise ValueError("Link buttons have no callback.")
        if value is not None:
            if value not in {option.value for option in child.options}:
                raise ValueError("Unknown dropdown value.")
            child._values = [value]
        await child.callback(interaction)
        return clicked

    async def submit(self, result, values, **identity):
        modal = result.modal
        if modal is None or modal.is_finished():
            raise ValueError("No active modal.")
        if set(values) - {item.custom_id for item in modal.children}:
            raise ValueError("Unknown form input.")
        for item in modal.children:
            value = values.get(item.custom_id, "")
            if not isinstance(value, str) or (item.required and not value) or len(value) > item.max_length:
                raise ValueError("Invalid form input.")
            item._value = value
        interaction, submitted = self.interaction(**identity)
        await modal.on_submit(interaction)
        modal.stop()
        return submitted

    async def event(self, event, *args):
        await self.bot.emit(event, *args)

    async def expire(self, result):
        if result.view:
            await result.view.on_timeout()
            result.view.stop()

    async def close(self):
        for view in self._views:
            view.stop()
        self.bot._clock = self._previous_clock

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
