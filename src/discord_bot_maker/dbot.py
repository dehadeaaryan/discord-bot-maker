"""Simple Discord bots with an explicit API and legacy DBot compatibility."""

import logging
from pathlib import Path

import discord
from discord.ext import commands

from .command import Command
from .features import Features, ManagedClient
from .config import BotConfig

logger = logging.getLogger(__name__)


class Bot(Features):
    """Build a bot using reply helpers and typed slash-command functions.

    Bot.from_env() creates a slash-only bot. The original constructor retains
    its prefix behavior; slash_only=True disables the privileged message-content
    intent and prefix help command.
    """

    def __init__(
        self,
        token: str,
        prefix: str | tuple[str, ...] = ".",
        *,
        help_command: bool = True,
        owner: str | None = None,
        auto_initialize: bool = True,
        guild_id: int | str | None = None,
        channel_id: int | str | None = None,
        storage: str | Path = "data/bot.sqlite3",
        slash_only: bool = False,
        config: BotConfig | None = None,
    ):
        if not token or not token.strip():
            raise ValueError("A Discord bot token is required.")
        prefixes = (prefix,) if isinstance(prefix, str) else prefix
        if not prefixes or any(not isinstance(value, str) or not value for value in prefixes):
            raise ValueError("Provide at least one nonempty command prefix.")
        self.config = config or BotConfig()
        if not isinstance(self.config, BotConfig):
            raise TypeError("config must be a BotConfig value.")
        self.token = token
        self.prefix = prefix
        self.owner = owner
        self.command_definitions: dict[str, Command] = {}
        self.client: commands.Bot | None = None
        self._init_features(guild_id=guild_id, channel_id=channel_id, storage=storage, slash_only=slash_only)
        if auto_initialize:
            self.initialize()
            if help_command and not slash_only:
                self.add_help_command()

    def initialize(self):
        """Initialize the underlying client without making a network connection."""
        if self.client is not None:
            raise RuntimeError("The bot client is already initialized.")
        intents = discord.Intents(self.config.intents.value) if self.config.intents is not None else discord.Intents.default()
        if self.config.intents is None:
            intents.message_content = not self.slash_only
        if not self.slash_only and not intents.message_content:
            raise ValueError("Prefix commands require the message_content intent.")
        self._gateway_intents = intents
        self.client = ManagedClient(self, command_prefix=self.prefix, intents=intents, help_command=None, allowed_mentions=self.config.allowed_mentions, activity=discord.Game(self.config.presence) if self.config.presence else None, status=getattr(discord.Status, self.config.status))

        @self.client.event
        async def on_ready():
            logger.info("Connected to Discord as %s", self.client.user)
            await self.emit("ready")

        @self.client.event
        async def on_message(message):
            if message.author.bot:
                return
            if self.guild_id and getattr(message.guild, "id", None) != self.guild_id:
                return
            if self.channel_id and message.channel.id != self.channel_id:
                return
            await self.emit("message", message)
            prefixes = (self.prefix,) if isinstance(self.prefix, str) else self.prefix
            for prefix in prefixes:
                if not message.content.startswith(prefix):
                    continue
                content = message.content[len(prefix):].split(maxsplit=1)
                command = self.command_definitions.get(content[0]) if content else None
                if command is not None:
                    await message.channel.send(embed=self._render_reply(command, message))
                    return
            await self.client.process_commands(message)

    @staticmethod
    def _render_reply(command: Command, message):
        author, channel, guild = message.author, message.channel, message.guild
        variables = {
            "author name": author.name,
            "author mention": author.mention,
            "author display name": author.display_name,
            "author discriminator": author.discriminator,
            "message time": message.created_at,
            "message content": message.content,
            "message clean content": message.clean_content,
            "channel name": getattr(channel, "name", ""),
            "channel topic": getattr(channel, "topic", "") or "",
            "channel category": getattr(getattr(channel, "category", None), "name", ""),
            "channel mention": getattr(channel, "mention", ""),
            "guild name": getattr(guild, "name", ""),
            "guild member count": getattr(guild, "member_count", ""),
            "guild description": getattr(guild, "description", "") or "",
            "guild features": getattr(guild, "features", []),
        }

        def render(text):
            for name, value in variables.items():
                text = text.replace(f"<{name}>", str(value))
            return text

        embed = discord.Embed(
            title=render(command.reply),
            description=render(command.description or ""),
            color=discord.Color.orange(),
        )
        embed.set_thumbnail(url=author.display_avatar.url)
        if command.emoji:
            embed.add_field(name="\u200e", value=command.emoji, inline=False)
        if command.image_url:
            embed.set_image(url=command.image_url)
        return embed

    def _require_client(self):
        if self.client is None:
            raise RuntimeError("Call initialize() before adding commands or running the bot.")
        return self.client

    def add_command(
        self, name: str, reply: str, *, description: str | None = None,
        emoji: str | None = "😃", image_url: str | None = None,
        help_text: str = "No description provided.",
    ) -> Command:
        """Add or replace a named reply command and return its definition."""
        client = self._require_client()
        if self.slash_only:
            raise ValueError("Use reply() for slash commands, or create Bot(..., slash_only=False) for prefix commands.")
        if client.get_command(name) is not None or client.tree.get_command(name) is not None:
            raise ValueError(f"Command {name!r} is already registered on the Discord client.")
        command = Command(name, reply, description, emoji, image_url, help_text)
        self.command_definitions[name] = command
        return command

    def add_help_command(self, title: str = "Help", description: str | None = None):
        client = self._require_client()
        if "help" in self.command_definitions:
            raise ValueError("A reply command named 'help' already exists.")
        client.remove_command("help")

        @client.command(name="help", help="List available commands.")
        async def show_help(context):
            embed = discord.Embed(
                title=title, description=description or "Available commands", color=discord.Color.orange(),
            )
            entries = [f"{command.name}: {command.help or ''}" for command in client.walk_commands()]
            entries.extend(f"{command.name}: {command.help_text}" for command in self.command_definitions.values())
            # Embed descriptions support 4096 characters, including the heading.
            heading = embed.description or ""
            embed.description = (heading + "\n\n" + "\n".join(entries))[:4096]
            await context.send(embed=embed)

    def add_greeting_command(
        self, *, aliases: list[str] | None = None, reply: str = "Hello!",
        description: str = "", image_url: str | None = None,
        help_text: str = "Say hello.",
    ):
        client = self._require_client()
        names = ["hi", *(aliases or [])]
        if any(name in self.command_definitions or client.get_command(name) for name in names):
            raise ValueError("A greeting command name or alias is already in use.")

        @client.command(name="hi", aliases=list(aliases or []), help=help_text)
        async def greet(context):
            embed = discord.Embed(title=reply, description=description, color=discord.Color.orange())
            if image_url:
                embed.set_image(url=image_url)
            await context.send(embed=embed)

    def run(self, *, sync: bool = False):
        """Connect to Discord. Use sync=True on first run or after command changes."""
        self.validate_config()
        self._manage_signals = True
        self._sync_commands = sync
        self._require_client().run(self.token)

    def to_definition(self, name: str = "My bot"):
        """Export reply commands into the shared visual-builder definition.

        Custom Discord callbacks cannot be serialized. A multi-prefix v1 bot
        exports its first prefix; the definition format supports one prefix.
        """
        return self._export_replies(name)

    def __len__(self):
        return len(self.command_definitions)

    # Compatibility entry points for published DBot examples.
    def createCommand(self, trigger, reply, reply2=None, emoji="😃", image=None, help="Not Defined"):
        return self.add_command(trigger, reply, description=reply2, emoji=emoji, image_url=image, help_text=help)

    def createCommands(self, commDict):
        for name, values in commDict.items():
            self.createCommand(name, *values)

    def bRun(self):
        return self.run()

    def baseCode(self):
        return self.initialize()

    def getBotInstance(self):
        return self.client

    def commandHelp(self, title="Help", description=None):
        return self.add_help_command(title, description)

    def commandHi(self, aliases=None, help="Says hi back", message="Hey!", description="", gif=None):
        return self.add_greeting_command(aliases=aliases, reply=message, description=description, image_url=gif, help_text=help)

    @property
    def bot(self):
        return self.client

    @property
    def bPrefix(self):
        return self.prefix

    @property
    def bTOKEN(self):
        return self.token

    @property
    def commDict(self):
        return {
            name: (item.reply, item.description, item.emoji, item.image_url, item.help_text)
            for name, item in self.command_definitions.items()
        }

    def __add__(self, values):
        self.createCommand(*values)
        return self

    def __call__(self):
        return self.bRun()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        if exception_type is None:
            self.bRun()


class DBot(Bot):
    """Compatibility constructor for v1. Prefer Bot for new applications."""

    def __init__(self, bTOKEN, bPrefix=".", owner=None, helpCommand=True, baseCode=True):
        super().__init__(
            token=bTOKEN, prefix=bPrefix, owner=owner,
            help_command=helpCommand, auto_initialize=baseCode,
        )
