"""Optional hooks, installed command packs and registration previews."""
import logging
from importlib import metadata

from .interactions import invoke
from .responses import UserError

logger = logging.getLogger(__name__)


class Extensions:
    def on(self, event):
        """Register a reusable event handler. Failures are isolated and logged."""
        self._require_client()
        if event not in {"message", "member_join", "reaction_add", "ready"}:
            raise ValueError("Supported events: message, member_join, reaction_add, ready.")
        if event == "member_join":
            self._gateway_intents.members = True
        if event == "message":
            self._gateway_intents.message_content = True
        def register(function):
            self._hooks.setdefault(event, []).append(function)
            return function
        return register

    async def emit(self, event, *args):
        """Dispatch through the same hooks used by the gateway and simulator."""
        subject = args[0] if args else None
        guild = getattr(subject, "guild", None) or getattr(getattr(subject, "message", None), "guild", None)
        if self.guild_id and guild is not None and guild.id != self.guild_id:
            return
        for function in self._hooks.get(event, ()):
            try:
                await invoke(function, *args)
            except Exception as error:
                logger.error("Event %s failed (%s).", event, type(error).__name__)

    def trigger(self, text, response, *, exact=False, case_sensitive=False):
        """Reply to a message containing text (bot messages are excluded)."""
        if not isinstance(text, str) or not text:
            raise ValueError("Trigger text must be nonempty.")
        from .interactions import CommandContext
        from .transport import PrefixInteraction
        from types import SimpleNamespace
        @self.on("message")
        async def match(message):
            if getattr(message.author, "bot", False):
                return
            content, needle = message.content, text
            if not case_sensitive:
                content, needle = content.casefold(), needle.casefold()
            if (content == needle if exact else needle in content):
                context = CommandContext(self, PrefixInteraction(SimpleNamespace(author=message.author, guild=message.guild, channel=message.channel, send=message.channel.send)))
                result = await invoke(response, context) if callable(response) else response
                if result is not None:
                    await context.respond(result)
        return self

    def auto_role(self, role_id):
        """Opt into members intent and assign a role after permission/hierarchy checks."""
        from .config import parse_id
        role_id = parse_id(role_id, "Role ID")
        if role_id is None:
            raise ValueError("A role ID is required.")
        @self.on("member_join")
        async def assign(member):
            role = member.guild.get_role(role_id)
            me = member.guild.me
            if role is None or role.is_default() or role.managed or not me.guild_permissions.manage_roles or role >= me.top_role:
                raise UserError("The bot cannot assign the configured role.")
            await member.add_roles(role, reason="Discord Bot Maker auto-role")
        return self

    @staticmethod
    def discover_plugins():
        """List installed entry points without importing or executing plugins."""
        return sorted(entry.name for entry in metadata.entry_points(group="discord_bot_maker.packs"))

    def use(self, pack):
        """Install a callable pack(bot), or explicitly load an installed entry point."""
        key = pack
        if key in self._packs:
            raise ValueError("This command pack is already installed.")
        if isinstance(pack, str):
            matches = [entry for entry in metadata.entry_points(group="discord_bot_maker.packs") if entry.name == pack]
            if len(matches) != 1:
                raise ValueError("Plugin name must match exactly one installed command pack.")
            pack = matches[0].load()
        if not callable(pack):
            raise TypeError("A command pack must be callable.")
        import inspect
        if inspect.iscoroutinefunction(pack):
            raise TypeError("Command packs must register synchronously.")
        pack(self)
        self._packs.add(key)
        return self

    def help(self, *, name="help", mode="slash", page_size=6):
        """Opt into searchable, permission-filtered help with category navigation."""
        from .help import Help
        if not 1 <= page_size <= 10:
            raise ValueError("Help page size must be between 1 and 10.")
        # Replace only the automatically installed legacy help command.
        existing = self.client.get_command(name)
        if existing and existing.callback.__name__ == "show_help":
            self.client.remove_command(name)
        @self.command(name, description="Search available commands", mode=mode, category="Help")
        def show_help(ctx, query: str = ""):
            return Help(query, page_size)
        return self

    def sync_preview(self, remote):
        """Diff a remote snapshot without network requests or registration changes."""
        from .sync import preview
        local = [command.to_dict(self.client.tree) for command in self.client.tree.get_commands()]
        return preview(local, remote, self.guild_id)

    async def fetch_sync_preview(self):
        """Read Discord's current registration. Requires an authenticated client."""
        import discord
        guild = discord.Object(id=self.guild_id) if self.guild_id else None
        remote = await self.client.tree.fetch_commands(guild=guild)
        snapshot = []
        for command in remote:
            payload = command.to_dict()
            permissions = getattr(command, "default_member_permissions", None)
            payload.update(default_member_permissions=str(permissions.value) if permissions is not None else None, nsfw=getattr(command, "nsfw", False), dm_permission=getattr(command, "dm_permission", True))
            snapshot.append(payload)
        return self.sync_preview(snapshot)

    def validate_config(self):
        """Offline validation; returns a credential-free configuration summary."""
        from .config import parse_id
        self._require_client()
        parse_id(self.guild_id, "Server ID")
        parse_id(self.channel_id, "Channel ID")
        if not self.slash_only and not self.client.intents.message_content:
            raise ValueError("Prefix commands require message_content intent.")
        return {"valid": True, "scope": self.guild_id or "global", "commands": len(self._commands), "prefix_enabled": not self.slash_only, "intents": self.client.intents.value}

    def health(self):
        """A small snapshot for an application's own health endpoint."""
        return {"ready": self.client.is_ready(), "closed": self.client.is_closed(), "background_tasks": len(self._background)}

    def settings(self, server_id, schema):
        """Bind a Settings schema to one server, migrating on first read/update."""
        from .config import parse_id
        server_id = parse_id(server_id, "Server ID")
        if server_id is None:
            raise ValueError("A server ID is required.")
        return schema.bind(self.store.scope("server", server_id))

    def job(self, name):
        """Register a durable job handler accepting one JSON payload."""
        if not isinstance(name, str) or not 1 <= len(name) <= 100:
            raise ValueError("Job names must contain 1–100 characters.")
        def register(function):
            if name in self.jobs.handlers:
                raise ValueError("Job name is already registered.")
            self.jobs.handlers[name] = function
            return function
        return register

    def health_check(self, *, host="127.0.0.1", port=8080):
        """Opt into GET /health; starts with the bot and stops during shutdown."""
        if not isinstance(host, str) or not host or type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Provide a host and port between 1 and 65535.")
        self._health_endpoint = (host, port)
        return self
