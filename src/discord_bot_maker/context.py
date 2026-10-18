"""Shared Discord-to-portable context conversion."""
import discord
from .engine import Context


def context_from(user, channel, guild, content=""):
    permissions = channel.permissions_for(user) if guild and hasattr(channel, "permissions_for") else None
    return Context(
        user_id=str(user.id), user_name=user.name, display_name=user.display_name,
        channel_id=str(getattr(channel, "id", "")), channel_name=getattr(channel, "name", "Direct message"),
        server_id=str(guild.id) if guild else "", server_name=guild.name if guild else "",
        message_content=content, role_ids=[str(role.id) for role in getattr(user, "roles", [])],
        permissions=[name for name in discord.Permissions.VALID_FLAGS if getattr(permissions, name, False)],
        age_restricted=getattr(channel, "is_nsfw", lambda: False)(), in_server=guild is not None,
    )
