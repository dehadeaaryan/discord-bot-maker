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
