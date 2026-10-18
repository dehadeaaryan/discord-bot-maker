"""Versioned, portable bot definitions. No credentials or executable code."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

VARIABLES = {
    "user.name", "user.display_name", "user.mention", "user.id",
    "channel.name", "channel.id", "server.name", "server.id", "message.content",
}
VARIABLE_PATTERN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


Snowflake = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,19}$")]


class CommandOption(Model):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    description: str = Field(default="Command argument", min_length=1, max_length=100)
    type: Literal["str", "int", "float", "bool"] = "str"
    required: bool = True
    default: str | int | float | bool | None = None
    choices: list[str] = Field(default_factory=list, max_length=25)
    autocomplete: list[str] = Field(default_factory=list, max_length=25)

    @model_validator(mode="after")
    def validate_option(self):
        if self.name in {"ctx", "context", "interaction"}:
            raise ValueError("Argument name is reserved by the command context.")
        if len(set(self.choices)) != len(self.choices) or len(set(self.autocomplete)) != len(self.autocomplete):
            raise ValueError("Choices and autocomplete values must be unique.")
        kind = {"str": str, "int": int, "float": float, "bool": bool}[self.type]
        if not self.required and (type(self.default) is not kind and not (kind is float and type(self.default) is int)):
            raise ValueError("Optional arguments need a default matching their type.")
        if (self.choices or self.autocomplete) and self.type != "str":
            raise ValueError("Visual choices and autocomplete require a text argument.")
        if self.choices and self.autocomplete:
            raise ValueError("Choose fixed choices or autocomplete, not both.")
        if any(not 1 <= len(value) <= 100 for value in self.choices + self.autocomplete):
            raise ValueError("Choices must contain 1–100 characters.")
        if self.choices and not self.required and self.default not in self.choices:
            raise ValueError("The argument default must be one of its choices.")
        return self


class CommandChecks(Model):
    server_only: bool = False
    channels: list[Snowflake] = Field(default_factory=list, max_length=25)
    roles: list[Snowflake] = Field(default_factory=list, max_length=25)
    age_restricted: bool = False
    permission: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_permission(self):
        if self.permission:
            from discord import Permissions
            if self.permission not in Permissions.VALID_FLAGS:
                raise ValueError("Unknown Discord permission.")
        return self


class EventHook(Model):
    event: Literal["message", "member_join", "reaction_add"] = "message"
    match: str = Field(default="hello", min_length=1, max_length=100)
    response: str = Field(default="Hello, {{user.display_name}}!", min_length=1, max_length=2000)
    channel_id: Snowflake | None = None
    role_id: Snowflake | None = None
    exact: bool = True

    @model_validator(mode="after")
    def event_settings(self):
        if self.event == "member_join" and not self.channel_id:
            raise ValueError("Member greetings need a channel ID.")
        if self.role_id and self.event != "member_join":
            raise ValueError("Auto-roles are only available for member joins.")
        return self


class SettingMigration(Model):
    from_version: int = Field(ge=1, le=1000)
    rename: dict[str, str] = Field(default_factory=dict, max_length=50)


class ServerSettingsConfig(Model):
    version: int = Field(default=1, ge=1, le=1000)
    defaults: dict[str, str | int | float | bool] = Field(default_factory=dict, max_length=50)
    migrations: list[SettingMigration] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def setting_keys(self):
        if any(not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", key) for key in self.defaults):
            raise ValueError("Setting names use lowercase letters, numbers and underscores.")
        versions = [item.from_version for item in self.migrations]
        if len(versions) != len(set(versions)) or any(v >= self.version for v in versions):
            raise ValueError("Settings migrations need unique source versions below the current version.")
        return self


class ScheduleConfig(Model):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    channel_id: Snowflake
    seconds: int = Field(default=3600, ge=60, le=31536000)
    response: str = Field(default="Scheduled announcement", min_length=1, max_length=2000)
    retries: int = Field(default=3, ge=0, le=10)


class RuntimeConfig(Model):
    presence: str = Field(default="", max_length=128)
    status: Literal["online", "idle", "dnd", "invisible"] = "online"
    message_content: bool = False
    members: bool = False
    mention_users: bool = False
    mention_roles: bool = False
    mention_everyone: bool = False
    help: bool = False
    help_page_size: int = Field(default=6, ge=1, le=10)
    packs: list[Literal["polls", "reminders", "moderation"]] = Field(default_factory=list, max_length=3)
    hooks: list[EventHook] = Field(default_factory=list, max_length=25)
    settings: ServerSettingsConfig = Field(default_factory=ServerSettingsConfig)
    schedules: list[ScheduleConfig] = Field(default_factory=list, max_length=25)

    @model_validator(mode="after")
    def unique_entries(self):
        if len(self.packs) != len(set(self.packs)) or len({item.id for item in self.schedules}) != len(self.schedules):
            raise ValueError("Packs and scheduled job IDs must be unique.")
        return self


class Trigger(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["trigger"] = "trigger"
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    description: str = Field(default="A bot command", min_length=1, max_length=100)
    mode: Literal["slash", "prefix", "both"] = "slash"
    cooldown: int = Field(default=0, ge=0, le=86400)
    category: str = Field(default="General", min_length=1, max_length=80)
    checks: CommandChecks = Field(default_factory=CommandChecks)
    options: list[CommandOption] = Field(default_factory=list, max_length=25)


class Reply(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["reply"] = "reply"
    content: str = Field(default="Hello, {{user.display_name}}!", min_length=1, max_length=2000)
    ephemeral: bool = False


class EmbedField(Model):
    name: str = Field(min_length=1, max_length=256)
    value: str = Field(min_length=1, max_length=1024)
    inline: bool = False


class Embed(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["embed"] = "embed"
    title: str = Field(default="Welcome", min_length=1, max_length=256)
    description: str = Field(default="", max_length=4096)
    color: str = Field(default="#ff7a30", pattern=r"^#[0-9a-fA-F]{6}$")
    image_url: HttpUrl | None = None
    thumbnail_url: HttpUrl | None = None
    url: HttpUrl | None = None
    footer: str = Field(default="", max_length=2048)
    fields: list[EmbedField] = Field(default_factory=list, max_length=25)
    ephemeral: bool = False


class Condition(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["condition"] = "condition"
    field: Literal["role", "channel"] = "role"
    value: str = Field(default="123456789", pattern=r"^[0-9]{1,25}$")


class VisualButton(Model):
    label: str = Field(default="Click me", min_length=1, max_length=80)
    reply: str = Field(default="Hello!", max_length=2000)
    url: HttpUrl | None = None
    style: Literal["primary", "secondary", "success", "danger"] = "secondary"


class VisualSelect(Model):
    placeholder: str = Field(default="Choose an option", min_length=1, max_length=150)
    options: list[str] = Field(default_factory=lambda: ["One", "Two"], min_length=1, max_length=25)
    reply: str = Field(default="You chose {{input.value}}", min_length=1, max_length=2000)

    @model_validator(mode="after")
    def unique_options(self):
        if len(set(self.options)) != len(self.options) or any(not 1 <= len(v) <= 100 for v in self.options):
            raise ValueError("Dropdown options need unique labels of 1–100 characters.")
        return self


class VisualAttachment(Model):
    filename: str = Field(default="report.txt", pattern=r"^[a-zA-Z0-9_.-]{1,100}$")
    content: str = Field(default="Report contents", max_length=16000)


class InteractiveMessage(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["message"] = "message"
    content: str = Field(default="Choose an action", min_length=1, max_length=2000)
    buttons: list[VisualButton] = Field(default_factory=list, max_length=5)
    selects: list[VisualSelect] = Field(default_factory=list, max_length=4)
    attachments: list[VisualAttachment] = Field(default_factory=list, max_length=10)
    owner_only: bool = True
    timeout: int = Field(default=180, ge=1, le=900)
    ephemeral: bool = False


class VisualInput(Model):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str = Field(min_length=1, max_length=45)
    required: bool = True
    max_length: int = Field(default=1000, ge=1, le=4000)
    paragraph: bool = False


class Form(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["form"] = "form"
    title: str = Field(default="Feedback", min_length=1, max_length=45)
    inputs: list[VisualInput] = Field(default_factory=lambda: [VisualInput(name="feedback", label="Your feedback", paragraph=True)], min_length=1, max_length=5)
    response: str = Field(default="Thanks for your feedback!", min_length=1, max_length=2000)


class Action(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["action"] = "action"
    operation: Literal["store_get", "store_set", "store_increment", "setting_get", "setting_set", "moderation", "schedule", "cancel_job"] = "store_get"
    key: str = Field(default="visits", pattern=r"^[a-z][a-z0-9_]{0,31}$")
    value: str = Field(default="1", max_length=2000)
    target: str = Field(default="{{options.member_id}}", max_length=100)
    moderation_action: Literal["kick", "ban", "timeout"] = "kick"
    reason: str = Field(default="Moderator request", min_length=1, max_length=300)
    minutes: int = Field(default=10, ge=1, le=40320)
    delay: int = Field(default=60, ge=0, le=31536000)
    retries: int = Field(default=3, ge=0, le=10)
    response: str = Field(default="Value: {{store.value}}", min_length=1, max_length=2000)
    ephemeral: bool = True


Node = Annotated[Trigger | Reply | Embed | Condition | InteractiveMessage | Form | Action, Field(discriminator="kind")]


class Edge(Model):
    id: str = Field(min_length=1, max_length=80)
    source: str
    target: str
    branch: Literal["next", "true", "false"] = "next"


class Position(Model):
    x: float = Field(ge=-100000, le=100000)
    y: float = Field(ge=-100000, le=100000)


class Layout(Model):
    positions: dict[str, Position] = Field(default_factory=dict, max_length=128)


class BotDefinition(Model):
    schema_version: Literal[1] = 1
    name: str = Field(default="My first bot", min_length=1, max_length=80)
    prefix: str = Field(default="!", min_length=1, max_length=10)
    nodes: list[Node] = Field(min_length=2, max_length=128)
    edges: list[Edge] = Field(min_length=1, max_length=256)
    layout: Layout = Field(default_factory=Layout)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

    @model_validator(mode="after")
    def validate_graph(self):
        nodes = {node.id: node for node in self.nodes}
        if len(nodes) != len(self.nodes):
            raise ValueError("Every block needs a unique ID.")
        if len({edge.id for edge in self.edges}) != len(self.edges):
            raise ValueError("Every connection needs a unique ID.")
        triggers = [node for node in self.nodes if isinstance(node, Trigger)]
        if not triggers:
            raise ValueError("Add at least one command trigger.")
        keys = [(mode, node.name) for node in triggers for mode in (("slash", "prefix") if node.mode == "both" else (node.mode,))]
        if len(set(keys)) != len(keys):
            raise ValueError("Command names must be unique within each command mode.")
        reserved = set()
        if self.runtime.help:
            reserved.add("help")
        for pack in self.runtime.packs:
            reserved.update({"polls": {"poll"}, "reminders": {"remind", "reminders", "cancel_reminder"}, "moderation": {"kick", "ban", "timeout"}}[pack])
        if reserved.intersection(node.name for node in triggers):
            raise ValueError("A command name conflicts with enabled help or a built-in pack.")
        for trigger in triggers:
            if len({o.name for o in trigger.options}) != len(trigger.options):
                raise ValueError("Command arguments need unique names.")
        outgoing: dict[str, list[Edge]] = {key: [] for key in nodes}
        for edge in self.edges:
            if edge.source not in nodes or edge.target not in nodes:
                raise ValueError("A connection references a missing block.")
            if isinstance(nodes[edge.target], Trigger):
                raise ValueError("Connections cannot lead into command triggers.")
            outgoing[edge.source].append(edge)
        for node in self.nodes:
            branches = [edge.branch for edge in outgoing[node.id]]
            if isinstance(node, Condition):
                if sorted(branches) != ["false", "true"]:
                    raise ValueError("Conditions need one True and one False connection.")
            elif isinstance(node, Trigger):
                if branches != ["next"]:
                    raise ValueError("Each command trigger needs one Next connection.")
            elif isinstance(node, Form) or (isinstance(node, Action) and node.operation == "moderation"):
                if branches:
                    raise ValueError("Forms and moderation confirmations must end a flow.")
            elif branches not in ([], ["next"]):
                raise ValueError("Reply blocks can have at most one Next connection.")
            if isinstance(node, Embed) and len(node.title) + len(node.description) + len(node.footer) + sum(len(f.name) + len(f.value) for f in node.fields) > 6000:
                raise ValueError("Embed text exceeds 6000 characters.")
            if isinstance(node, Form) and len({item.name for item in node.inputs}) != len(node.inputs):
                raise ValueError("Form input names must be unique.")
        option_names = {o.name for t in triggers for o in t.options}
        input_names = {i.name for n in self.nodes if isinstance(n, Form) for i in n.inputs} | {"value"}
        allowed = VARIABLES | {f"options.{name}" for name in option_names} | {f"input.{name}" for name in input_names} | {f"settings.{name}" for name in self.runtime.settings.defaults} | {"store.value", "job.id"}
        def validate_text(value, key=""):
            if isinstance(value, dict):
                for k, v in value.items():
                    validate_text(v, k)
            elif isinstance(value, list):
                for item in value:
                    validate_text(item, key)
            elif isinstance(value, str) and key in {"content", "title", "description", "footer", "value", "reply", "response", "reason", "target", "name"}:
                unknown = set(VARIABLE_PATTERN.findall(value)) - allowed
                if unknown:
                    raise ValueError(f"Unknown variables: {', '.join(sorted(unknown))}")
                remaining = VARIABLE_PATTERN.sub("", value)
                if "{{" in remaining or "}}" in remaining:
                    raise ValueError("Variables must use balanced {{variable.name}} syntax.")
        for node in self.nodes:
            data = node.model_dump(mode="json")
            if isinstance(node, Action) and node.operation != "moderation":
                data.pop("target", None)
            validate_text(data)
        for hook in self.runtime.hooks:
            unknown = set(VARIABLE_PATTERN.findall(hook.response)) - VARIABLES
            if unknown:
                raise ValueError("Hook responses only support user, channel, server and message variables.")
        for schedule in self.runtime.schedules:
            if "{{" in schedule.response or "}}" in schedule.response:
                raise ValueError("Scheduled announcements use literal text, without user variables.")
        visited, active = set(), set()

        def visit(node_id):
            if node_id in active:
                raise ValueError("Loops are not supported. Remove the circular connection.")
            if node_id in visited:
                return
            active.add(node_id)
            for edge in outgoing[node_id]:
                visit(edge.target)
            active.remove(node_id)
            visited.add(node_id)

        for trigger in triggers:
            visit(trigger.id)
            paths = [(edge.target, 0) for edge in outgoing[trigger.id]]
            seen_paths = set()
            while paths:
                current, responses = paths.pop()
                if (current, responses) in seen_paths:
                    continue
                seen_paths.add((current, responses))
                node = nodes[current]
                if isinstance(node, Form) and (responses or trigger.mode != "slash"):
                    raise ValueError("Forms must be the first response of a slash-only command.")
                count = responses + int(isinstance(node, (Reply, Embed, InteractiveMessage, Action)))
                if count > 5:
                    raise ValueError("A command can send at most five responses.")
                paths.extend((edge.target, count) for edge in outgoing[current])
        if len(visited) != len(nodes):
            raise ValueError("Every block must be reachable from a command trigger.")
        if set(self.layout.positions) - nodes.keys():
            raise ValueError("Layout references a missing block.")
        return self
