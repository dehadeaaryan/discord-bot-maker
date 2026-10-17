"""Command definitions shared by the Python API and future visual editor."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """A prefix command that replies with an embed."""

    name: str
    reply: str
    description: str | None = None
    emoji: str | None = "😃"
    image_url: str | None = None
    help_text: str = "No description provided."

    def __post_init__(self):
        if not self.name or any(character.isspace() for character in self.name):
            raise ValueError("Command names must be nonempty and contain no whitespace.")
        if not self.reply:
            raise ValueError("A command reply cannot be empty.")
