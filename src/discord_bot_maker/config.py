"""Small, explicit environment-file support for standalone bots."""

import os
import shlex
from pathlib import Path

SETTINGS = {"DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "DISCORD_CHANNEL_ID"}


def read_env(path: str | Path = ".env") -> dict[str, str]:
    """Read bot settings without executing shell syntax or mutating the environment.

    Exported environment variables take priority over the file, including empty
    values. Only token/server/channel settings are read. Errors never echo values.
    """
    values = {}
    path = Path(path)
    if path.is_file():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            key, separator, value = line.strip().partition("=")
            key = key.strip().removeprefix("export ").strip()
            if not separator or key not in SETTINGS:
                continue
            try:
                parts = shlex.split(value, comments=True)
            except ValueError:
                raise ValueError(f"Invalid quoting in {path.name} on line {number}.") from None
            if len(parts) > 1:
                raise ValueError(f"Quote values containing spaces in {path.name} on line {number}.")
            values[key] = parts[0] if parts else ""
    return {key: os.environ.get(key, values.get(key, "")) for key in SETTINGS}


def parse_id(value: str | int | None, label: str) -> int | None:
    if value is None or value == "":
        return None
    text = str(value)
    if not text.isdigit() or not 0 < int(text) < 2**64:
        raise ValueError(f"{label} must be a numeric Discord ID.")
    return int(text)


class BotConfig:
    """Optional gateway configuration. Defaults preserve the existing Bot API.

    Intents and allowed_mentions are discord.py values; callers can opt into
    individual capabilities without replacing the managed client.
    """

    def __init__(self, *, intents=None, presence: str | None = None, status: str = "online", allowed_mentions=None):
        import discord
        if intents is not None and not isinstance(intents, discord.Intents):
            raise TypeError("intents must be discord.Intents.")
        if allowed_mentions is not None and not isinstance(allowed_mentions, discord.AllowedMentions):
            raise TypeError("allowed_mentions must be discord.AllowedMentions.")
        if status not in {"online", "idle", "dnd", "invisible"}:
            raise ValueError("Status must be online, idle, dnd or invisible.")
        if presence is not None and (not isinstance(presence, str) or not 1 <= len(presence) <= 128):
            raise ValueError("Presence must contain 1–128 characters.")
        self.intents = discord.Intents(intents.value) if intents is not None else None
        self.presence = presence
        self.status = status
        self.allowed_mentions = allowed_mentions if allowed_mentions is not None else discord.AllowedMentions.none()
