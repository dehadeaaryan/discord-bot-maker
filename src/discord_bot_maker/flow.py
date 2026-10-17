"""Discord adapter for the same interpreter used in previews."""

import asyncio
import logging

import discord
from discord import app_commands

from .definition import BotDefinition, Trigger
from .engine import Context, Engine, ExecutionError

logger = logging.getLogger(__name__)


def context_from(user, channel, guild, content=""):
    return Context(
        user_id=str(user.id), user_name=user.name, display_name=user.display_name,
        channel_id=str(getattr(channel, "id", "")), channel_name=getattr(channel, "name", "Direct message"),
        server_id=str(guild.id) if guild else "", server_name=guild.name if guild else "",
        message_content=content, role_ids=[str(role.id) for role in getattr(user, "roles", [])],
    )


def payload(message):
    if message["kind"] == "reply":
        return {"content": message["content"], "allowed_mentions": discord.AllowedMentions.none()}
    embed = discord.Embed(title=message["title"], description=message["description"], color=int(message["color"][1:], 16))
    if message.get("image_url"):
        embed.set_image(url=message["image_url"])
    return {"embed": embed, "allowed_mentions": discord.AllowedMentions.none()}


class FlowBot(discord.Client):
    def __init__(self, definition: BotDefinition, *, sync_commands: bool = False, guild_id: int | None = None):
        intents = discord.Intents.default()
        intents.message_content = any(isinstance(node, Trigger) and node.mode == "prefix" for node in definition.nodes)
        super().__init__(intents=intents)
        self.engine = Engine(definition)
        self.tree = app_commands.CommandTree(self)
        self.sync_commands = sync_commands
        self.guild_id = guild_id
        for node in definition.nodes:
            if isinstance(node, Trigger) and node.mode == "slash":
                self.tree.add_command(app_commands.Command(name=node.name, description=node.description, callback=self._callback(node.name)))

    def _callback(self, name):
        async def callback(interaction: discord.Interaction):
            try:
                result = self.engine.execute(name, context_from(interaction.user, interaction.channel, interaction.guild))
                for index, message in enumerate(result["messages"]):
                    send = interaction.response.send_message if index == 0 else interaction.followup.send
                    await send(**payload(message), ephemeral=message["ephemeral"])
            except ExecutionError as error:
                await interaction.response.send_message(str(error), ephemeral=True)
        return callback

    async def setup_hook(self):
        if self.sync_commands:
            if self.guild_id:
                guild = discord.Object(id=self.guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            else:
                await self.tree.sync()

    async def on_message(self, message):
        if message.author.bot or not message.content.startswith(self.engine.definition.prefix):
            return
        words = message.content[len(self.engine.definition.prefix):].split(maxsplit=1)
        if not words:
            return
        try:
            result = self.engine.execute(words[0], context_from(message.author, message.channel, message.guild, message.content), "prefix")
            for response in result["messages"]:
                await message.channel.send(**payload(response))
        except ExecutionError as error:
            if str(error) != "Command not found.":
                await message.channel.send(str(error), allowed_mentions=discord.AllowedMentions.none())

    async def on_ready(self):
        logger.info("Bot connected")
