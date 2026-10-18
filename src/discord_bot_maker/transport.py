"""Adapt prefix messages to the same response pipeline as interactions."""
from types import SimpleNamespace


class PrefixInteraction:
    is_prefix = True

    def __init__(self, context):
        self.context = context
        self.user, self.guild, self.channel = context.author, context.guild, context.channel
        self.guild_id = getattr(self.guild, "id", None)
        self.channel_id = self.channel.id
        self.permissions = self.channel.permissions_for(self.user) if self.guild else SimpleNamespace()
        self._done = False
        self._message = None
        self.response = SimpleNamespace(is_done=lambda: self._done, defer=self.defer, send_message=self.send)
        self.followup = SimpleNamespace(send=self.send)

    async def defer(self, **kwargs):
        self._done = True

    async def send(self, *args, **kwargs):
        # Prefix messages cannot be ephemeral. Never imply they are private.
        kwargs.pop("ephemeral", None)
        kwargs.pop("wait", None)
        self._done = True
        self._message = await self.context.send(*args, **kwargs)
        return self._message

    async def original_response(self):
        return self._message
