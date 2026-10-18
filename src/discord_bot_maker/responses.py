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
    fields: tuple = ()
    footer: str = ""
    thumbnail_url: str | None = None
    url: str | None = None

    def __post_init__(self):
        _text(self.title, "Embed title", 256)
        _text(self.description, "Embed description", 4096, empty=True)
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", self.color):
            raise ValueError("Embed color must be a hex color, such as #ff7a30.")
        _url(self.image_url)
        _url(self.thumbnail_url)
        _url(self.url)
        _text(self.footer, "Embed footer", 2048, empty=True)
        if len(self.fields) > 25:
            raise ValueError("An embed supports at most 25 fields.")
        fields = []
        for item in self.fields:
            if len(item) not in (2, 3):
                raise ValueError("Embed fields contain name, value and optional inline flag.")
            name, value = item[:2]
            _text(name, "Field name", 256)
            _text(value, "Field value", 1024)
            fields.append((name, value, bool(item[2]) if len(item) == 3 else False))
        object.__setattr__(self, "fields", tuple(fields))
        if len(self.title) + len(self.description) + len(self.footer) + sum(len(n) + len(v) for n, v, _ in fields) > 6000:
            raise ValueError("Embed text exceeds 6000 characters.")


@dataclass(frozen=True)
class Button:
    """A link, a canned reply, or a function accepting a CommandContext."""

    label: str
    reply: str | Embed | Callable[..., Any] | None = None
    url: str | None = None
    style: Literal["primary", "secondary", "success", "danger"] = "secondary"
    defer: bool = True

    def __post_init__(self):
        _text(self.label, "Button label", 80)
        if (self.reply is None) == (self.url is None):
            raise ValueError("Provide exactly one button reply or URL.")
        if self.style not in {"primary", "secondary", "success", "danger"}:
            raise ValueError("Unknown button style.")
        _url(self.url)


@dataclass(frozen=True)
class Attachment:
    filename: str
    data: bytes

    def __post_init__(self):
        _text(self.filename, "Attachment filename", 255)
        if "/" in self.filename or "\\" in self.filename:
            raise ValueError("Attachment filename cannot contain a path.")
        if not isinstance(self.data, bytes):
            raise TypeError("Attachment data must be bytes.")


@dataclass(frozen=True)
class Select:
    placeholder: str
    options: tuple[str, ...] | list[str]
    callback: Callable[..., Any]

    def __post_init__(self):
        _text(self.placeholder, "Dropdown placeholder", 150)
        if not 1 <= len(self.options) <= 25 or len(set(self.options)) != len(self.options):
            raise ValueError("Dropdowns need 1–25 unique options.")
        for option in self.options:
            _text(option, "Dropdown option", 100)
        if not callable(self.callback):
            raise TypeError("Dropdown callback must be callable.")
        object.__setattr__(self, "options", tuple(self.options))


@dataclass(frozen=True)
class TextInput:
    name: str
    label: str
    required: bool = True
    max_length: int = 1000
    paragraph: bool = False

    def __post_init__(self):
        _text(self.name, "Input name", 100)
        _text(self.label, "Input label", 45)
        if not 1 <= self.max_length <= 4000:
            raise ValueError("Input max_length must be between 1 and 4000.")


@dataclass(frozen=True)
class Modal:
    title: str
    inputs: tuple[TextInput, ...] | list[TextInput]
    callback: Callable[..., Any]
    timeout: float = 300

    def __post_init__(self):
        _text(self.title, "Modal title", 45)
        if not 1 <= len(self.inputs) <= 5 or len({item.name for item in self.inputs}) != len(self.inputs):
            raise ValueError("A modal needs 1–5 uniquely named inputs.")
        if not callable(self.callback) or not 1 <= self.timeout <= 900:
            raise ValueError("Provide a callback and a timeout between 1 and 900 seconds.")
        object.__setattr__(self, "inputs", tuple(self.inputs))


@dataclass(frozen=True)
class Message:
    """Combine text, an embed and buttons in a single response."""

    content: str = ""
    embed: Embed | None = None
    buttons: tuple[Button, ...] | list[Button] = field(default_factory=tuple)
    timeout: float = 180
    owner_only: bool = False
    attachments: tuple[Attachment, ...] | list[Attachment] = ()
    selects: tuple[Select, ...] | list[Select] = ()

    def __post_init__(self):
        _text(self.content, "Message", 2000, empty=True)
        if not self.content and self.embed is None and not self.attachments:
            raise ValueError("A message needs text or an embed.")
        if len(self.buttons) > 5:
            raise ValueError("A message can have at most five buttons.")
        if not 1 <= self.timeout <= 900:
            raise ValueError("Button timeout must be between 1 and 900 seconds.")
        if len(self.attachments) > 10 or len(self.selects) > 4:
            raise ValueError("Messages support at most 10 attachments and four dropdowns.")
        object.__setattr__(self, "buttons", tuple(self.buttons))
        object.__setattr__(self, "attachments", tuple(self.attachments))
        object.__setattr__(self, "selects", tuple(self.selects))


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


Response = str | Embed | Message | Poll | Modal
