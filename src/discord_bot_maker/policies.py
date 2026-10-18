"""Declarative policies shared by commands, help and interactive callbacks."""
from dataclasses import dataclass

from .config import parse_id


@dataclass(frozen=True)
class Checks:
    server_only: bool = False
    channels: tuple[int, ...] = ()
    roles: tuple[int, ...] = ()
    age_restricted: bool = False

    def __post_init__(self):
        for name in ("channels", "roles"):
            object.__setattr__(self, name, tuple(parse_id(value, name) for value in getattr(self, name)))
            if any(value is None for value in getattr(self, name)):
                raise ValueError(f"{name} must contain Discord IDs.")

    def failure(self, interaction):
        if (self.server_only or self.roles or self.age_restricted) and not interaction.guild_id:
            return "This command is only available in a server."
        if self.channels and interaction.channel_id not in self.channels:
            return "This command is not available in this channel."
        if self.roles and not set(self.roles).intersection(role.id for role in getattr(interaction.user, "roles", [])):
            return "You do not have a role required for this command."
        if self.age_restricted and not getattr(interaction.channel, "is_nsfw", lambda: False)():
            return "Use this command in an age-restricted channel."
        return None
