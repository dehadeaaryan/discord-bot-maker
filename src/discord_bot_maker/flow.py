"""Discord adapter for portable visual definitions."""
from .context import context_from
from .visual_runtime import VisualBot as FlowBot

# Kept for integrations that use the original payload conversion helper.
def payload(message):
    import discord
    if message["kind"] == "reply":
        return {"content": message["content"], "allowed_mentions": discord.AllowedMentions.none()}
    embed = discord.Embed(title=message["title"], description=message["description"], color=int(message["color"][1:], 16))
    if message.get("image_url"):
        embed.set_image(url=message["image_url"])
    return {"embed": embed, "allowed_mentions": discord.AllowedMentions.none()}
