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


class Trigger(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["trigger"] = "trigger"
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    description: str = Field(default="A bot command", min_length=1, max_length=100)
    mode: Literal["slash", "prefix"] = "slash"
    cooldown: int = Field(default=0, ge=0, le=86400)


class Reply(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["reply"] = "reply"
    content: str = Field(default="Hello, {{user.display_name}}!", min_length=1, max_length=2000)
    ephemeral: bool = False


class Embed(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["embed"] = "embed"
    title: str = Field(default="Welcome", min_length=1, max_length=256)
    description: str = Field(default="", max_length=4096)
    color: str = Field(default="#ff7a30", pattern=r"^#[0-9a-fA-F]{6}$")
    image_url: HttpUrl | None = None
    ephemeral: bool = False


class Condition(Model):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["condition"] = "condition"
    field: Literal["role", "channel"] = "role"
    value: str = Field(default="123456789", pattern=r"^[0-9]{1,25}$")


Node = Annotated[Trigger | Reply | Embed | Condition, Field(discriminator="kind")]


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
        keys = [(node.mode, node.name) for node in triggers]
        if len(set(keys)) != len(keys):
            raise ValueError("Command names must be unique within each command mode.")
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
            elif branches not in ([], ["next"]):
                raise ValueError("Reply blocks can have at most one Next connection.")
            for field in ("content", "title", "description"):
                text = getattr(node, field, "")
                unknown = set(VARIABLE_PATTERN.findall(text)) - VARIABLES
                if unknown:
                    raise ValueError(f"Unknown variables: {', '.join(sorted(unknown))}")
                remaining = VARIABLE_PATTERN.sub("", text)
                if "{{" in remaining or "}}" in remaining:
                    raise ValueError("Variables must use balanced {{variable.name}} syntax.")
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
        if len(visited) != len(nodes):
            raise ValueError("Every block must be reachable from a command trigger.")
        if set(self.layout.positions) - nodes.keys():
            raise ValueError("Layout references a missing block.")
        return self
