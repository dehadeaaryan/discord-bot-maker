"""Bounded interpreter used by both preview and Discord execution."""

import time
from dataclasses import dataclass, field

from .definition import BotDefinition, Condition, Embed, Reply, Trigger, VARIABLE_PATTERN


@dataclass
class Context:
    user_id: str = "100000001"
    user_name: str = "Aaryan"
    display_name: str = "Aaryan"
    channel_id: str = "100000002"
    channel_name: str = "general"
    server_id: str = "100000003"
    server_name: str = "My server"
    message_content: str = ""
    role_ids: list[str] = field(default_factory=list)

    def variables(self):
        return {
            "user.id": self.user_id, "user.name": self.user_name,
            "user.display_name": self.display_name, "user.mention": f"<@{self.user_id}>",
            "channel.id": self.channel_id, "channel.name": self.channel_name,
            "server.id": self.server_id, "server.name": self.server_name,
            "message.content": self.message_content,
        }


class ExecutionError(ValueError):
    pass


class Engine:
    def __init__(self, definition: BotDefinition, *, clock=time.monotonic):
        self.definition = BotDefinition.model_validate(definition.model_dump(mode="json"))
        self.clock = clock
        self.cooldowns: dict[tuple[str, str], float] = {}

    def execute(self, command: str, context: Context, mode: str = "slash") -> dict:
        nodes = {node.id: node for node in self.definition.nodes}
        trigger = next((node for node in nodes.values() if isinstance(node, Trigger) and node.name == command and node.mode == mode), None)
        if trigger is None:
            raise ExecutionError("Command not found.")
        key, now = (trigger.id, context.user_id), self.clock()
        if self.cooldowns.get(key, 0) > now:
            raise ExecutionError("This command is on cooldown. Try again shortly.")
        # Bound memory for long-running bots; discard expired users.
        self.cooldowns = {key: expiry for key, expiry in self.cooldowns.items() if expiry > now}
        if len(self.cooldowns) >= 10000 and trigger.cooldown:
            raise ExecutionError("The bot is busy. Try again shortly.")
        variables = context.variables()

        def render(text, limit):
            result = VARIABLE_PATTERN.sub(lambda match: str(variables[match.group(1)]), text)
            if len(result) > limit:
                raise ExecutionError(f"Rendered response exceeds Discord's {limit}-character limit.")
            return result

        trace, messages, current = [], [], trigger.id
        started = self.clock()
        for _ in range(64):
            if self.clock() - started > 2:
                raise ExecutionError("Execution time budget exceeded.")
            node = nodes[current]
            step = {"id": node.id, "kind": node.kind}
            branch = "next"
            if isinstance(node, Condition):
                passed = node.value in context.role_ids if node.field == "role" else context.channel_id == node.value
                branch = "true" if passed else "false"
                step["result"] = branch
            elif isinstance(node, Reply):
                messages.append({"kind": "reply", "content": render(node.content, 2000), "ephemeral": node.ephemeral})
            elif isinstance(node, Embed):
                messages.append({"kind": "embed", "title": render(node.title, 256), "description": render(node.description, 4096), "color": node.color, "image_url": str(node.image_url) if node.image_url else None, "ephemeral": node.ephemeral})
            trace.append(step)
            edge = next((edge for edge in self.definition.edges if edge.source == current and edge.branch == branch), None)
            if edge is None:
                if not messages:
                    raise ExecutionError("This command produced no response.")
                if len(messages) > 5:
                    raise ExecutionError("A command can send at most five responses.")
                if trigger.cooldown:
                    self.cooldowns[key] = now + trigger.cooldown
                return {"messages": messages, "trace": trace}
            current = edge.target
        raise ExecutionError("Execution step budget exceeded.")
