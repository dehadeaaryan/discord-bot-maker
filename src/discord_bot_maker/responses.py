"""Return values for commands. No discord.py imports needed in a bot script."""

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from urllib.parse import urlparse


class UserError(ValueError):
    """A friendly error that is safe to show privately to a command's user."""


def _text(value: str, label: str, maximum: int, *, empty=False):
    if not isinstance(value, str) or len(value) > maximum or (not value and not empty):
        raise ValueError(f"{label} must contain {'0' if empty else '1'}–{maximum} characters.")


def _url(value: str | None):
    if value and (urlparse(value).scheme not in {"https", "http"} or not urlparse(value).netloc):
        raise ValueError("Use an absolute HTTP or HTTPS URL.")


@dataclass(frozen=True)
class Embed:
    """A rich reply. Orange is the default; no forced package attribution."""

    title: str
    description: str = ""
    color: str = "#ff7a30"
    image_url: str | None = None

    def __post_init__(self):
        _text(self.title, "Embed title", 256)
        _text(self.description, "Embed description", 4096, empty=True)
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", self.color):
            raise ValueError("Embed color must be a hex color, such as #ff7a30.")
        _url(self.image_url)


@dataclass(frozen=True)
class Button:
    """A link, a canned reply, or a function accepting a CommandContext."""

    label: str
    reply: str | Embed | Callable[..., Any] | None = None
    url: str | None = None
    style: Literal["primary", "secondary", "success", "danger"] = "secondary"

    def __post_init__(self):
        _text(self.label, "Button label", 80)
        if (self.reply is None) == (self.url is None):
            raise ValueError("Provide exactly one button reply or URL.")
        if self.style not in {"primary", "secondary", "success", "danger"}:
            raise ValueError("Unknown button style.")
        _url(self.url)


@dataclass(frozen=True)
class Message:
    """Combine text, an embed and buttons in a single response."""

    content: str = ""
    embed: Embed | None = None
    buttons: tuple[Button, ...] | list[Button] = field(default_factory=tuple)
    timeout: float = 180
    owner_only: bool = False

    def __post_init__(self):
        _text(self.content, "Message", 2000, empty=True)
        if not self.content and self.embed is None:
            raise ValueError("A message needs text or an embed.")
        if len(self.buttons) > 5:
            raise ValueError("A message can have at most five buttons.")
        if not 1 <= self.timeout <= 900:
            raise ValueError("Button timeout must be between 1 and 900 seconds.")
        object.__setattr__(self, "buttons", tuple(self.buttons))


@dataclass(frozen=True)
class Poll:
    """A short-lived, one-vote-per-person button poll."""

    question: str
    choices: tuple[str, ...] | list[str]
    timeout: float = 300

    def __post_init__(self):
        _text(self.question, "Poll question", 256)
        if not 2 <= len(self.choices) <= 5 or len(set(self.choices)) != len(self.choices):
            raise UserError("Choose 2–5 different poll options, separated by |.")
        for choice in self.choices:
            _text(choice, "Poll option", 60)
        if not 1 <= self.timeout <= 900:
            raise ValueError("Poll timeout must be between 1 and 900 seconds.")
        object.__setattr__(self, "choices", tuple(self.choices))


Response = str | Embed | Message | Poll
