"""Bounded interpreter used by both preview and Discord execution."""

import time
import copy
import json
import math
from dataclasses import dataclass, field

from .definition import BotDefinition, Condition, Embed, Reply, Trigger, InteractiveMessage, Form, Action, VARIABLE_PATTERN


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
    permissions: list[str] = field(default_factory=list)
    age_restricted: bool = False
    in_server: bool = True

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
    def __init__(self, definition: BotDefinition, *, clock=time.monotonic, store=None, state=None):
        self.definition = BotDefinition.model_validate(definition.model_dump(mode="json"))
        self.clock = clock
        self.cooldowns: dict[tuple[str, str, str], float] = {}
        self.store = store
        self.state = copy.deepcopy(state or {"values": {}, "jobs": {}})
        self.state.setdefault("values", {})
        self.state.setdefault("jobs", {})

    def execute(self, command: str, context: Context, mode: str = "slash", *, options=None, component=None) -> dict:
        nodes = {node.id: node for node in self.definition.nodes}
        trigger = next((node for node in nodes.values() if isinstance(node, Trigger) and node.name == command and node.mode in {mode, "both"}), None)
        if trigger is None:
            raise ExecutionError("Command not found.")
        checks = trigger.checks
        if (checks.server_only or checks.roles or checks.age_restricted) and not context.in_server:
            raise ExecutionError("This command is only available in a server.")
        if checks.channels and context.channel_id not in checks.channels:
            raise ExecutionError("This command is not available in this channel.")
        if checks.roles and not set(checks.roles).intersection(context.role_ids):
            raise ExecutionError("You do not have a role required for this command.")
        if checks.age_restricted and not context.age_restricted:
            raise ExecutionError("Use this command in an age-restricted channel.")
        if checks.permission and checks.permission not in context.permissions and "administrator" not in context.permissions:
            raise ExecutionError(f"You need the {checks.permission.replace('_', ' ')} permission.")
        arguments = self.validate_options(trigger, options or {})
        key, now = (trigger.id, context.server_id if context.in_server else "dm", context.user_id), self.clock()
        if not component and self.cooldowns.get(key, 0) > now:
            raise ExecutionError("This command is on cooldown. Try again shortly.")
        # Bound memory for long-running bots; discard expired users.
        self.cooldowns = {key: expiry for key, expiry in self.cooldowns.items() if expiry > now}
        if len(self.cooldowns) >= 10000 and trigger.cooldown:
            raise ExecutionError("The bot is busy. Try again shortly.")
        variables = context.variables()
        variables.update({f"options.{name}": value for name, value in arguments.items()})
        settings = self.definition.runtime.settings
        variables.update({f"settings.{name}": value for name, value in settings.defaults.items()})
        if self.store and settings.defaults and context.in_server:
            from .visual_runtime import settings_schema
            values = settings_schema(settings).bind(self.store.scope("server", context.server_id)).get()
            variables.update({f"settings.{name}": value for name, value in values.items()})
        if not self.store:
            scope = context.server_id if context.in_server else f"dm:{context.user_id}"
            saved_settings = self.state["values"].get(scope, {}).get("__settings__", {})
            variables.update({f"settings.{name}": value for name, value in saved_settings.items() if name in settings.defaults})
        variables.update({"store.value": "", "job.id": ""})

        def render(text, limit):
            try:
                result = VARIABLE_PATTERN.sub(lambda match: str(variables[match.group(1)]), text)
            except KeyError:
                raise ExecutionError("A template variable is not available in this command.") from None
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
            elif component and node.id != component.get("node_id"):
                pass
            elif isinstance(node, Reply):
                messages.append({"kind": "reply", "content": render(node.content, 2000), "ephemeral": node.ephemeral})
            elif isinstance(node, Embed):
                message = {"kind": "embed", "title": render(node.title, 256), "description": render(node.description, 4096), "color": node.color, "image_url": str(node.image_url) if node.image_url else None, "ephemeral": node.ephemeral}
                if node.fields:
                    message["fields"] = [{"name": render(f.name, 256), "value": render(f.value, 1024), "inline": f.inline} for f in node.fields]
                if node.footer:
                    message["footer"] = render(node.footer, 2048)
                for attribute in ("url", "thumbnail_url"):
                    if getattr(node, attribute):
                        message[attribute] = str(getattr(node, attribute))
                if len(message["title"]) + len(message["description"]) + len(message.get("footer", "")) + sum(len(f["name"]) + len(f["value"]) for f in message.get("fields", [])) > 6000:
                    raise ExecutionError("Rendered embed exceeds Discord's 6000-character limit.")
                messages.append(message)
            elif isinstance(node, InteractiveMessage):
                if component:
                    if node.owner_only and component.get("owner_id", context.user_id) != context.user_id:
                        raise ExecutionError("This menu belongs to the person who opened it.")
                    index = component.get("index", 0)
                    if component.get("type") == "select":
                        if not 0 <= index < len(node.selects):
                            raise ExecutionError("Dropdown not found.")
                        select = node.selects[index]
                        value = component.get("value", "")
                        if value not in select.options:
                            raise ExecutionError("Choose one of the dropdown options.")
                        variables["input.value"] = value
                        content = render(select.reply, 2000)
                    else:
                        if not 0 <= index < len(node.buttons) or node.buttons[index].url:
                            raise ExecutionError("Reply button not found.")
                        content = render(node.buttons[index].reply, 2000)
                    messages.append({"kind": "reply", "content": content, "ephemeral": mode == "slash"})
                else:
                    data = node.model_dump(mode="json")
                    data.update(content=render(node.content, 2000), node_id=node.id)
                    data["attachments"] = [{"filename": f.filename, "content": render(f.content, 16000)} for f in node.attachments]
                    messages.append(data)
            elif isinstance(node, Form):
                if component:
                    values = component.get("inputs", {})
                    if set(values) - {item.name for item in node.inputs}:
                        raise ExecutionError("Unknown form input.")
                    for item in node.inputs:
                        value = values.get(item.name, "")
                        if not isinstance(value, str) or (item.required and not value) or len(value) > item.max_length:
                            raise ExecutionError(f"Invalid form input: {item.label}.")
                        variables[f"input.{item.name}"] = value
                    messages.append({"kind": "reply", "content": render(node.response, 2000), "ephemeral": True})
                else:
                    messages.append(dict(node.model_dump(mode="json"), node_id=node.id, ephemeral=True))
            elif isinstance(node, Action):
                data = node.model_dump(mode="json")
                scope = context.server_id if context.in_server else f"dm:{context.user_id}"
                values = self.state["values"].setdefault(scope, {}) if not self.store else {}
                store = self.store.scope("server", context.server_id) if self.store and context.in_server else self.store.scope("dm", context.user_id) if self.store else None
                if node.operation.startswith("setting_"):
                    if not context.in_server:
                        raise ExecutionError("Server settings require a server.")
                    if node.key not in settings.defaults:
                        raise ExecutionError("Choose a configured server setting key.")
                    if node.operation == "setting_set" and not {"manage_guild", "administrator"}.intersection(context.permissions):
                        raise ExecutionError("You need the manage server permission to change server settings.")
                    from .visual_runtime import settings_schema
                    schema = settings_schema(settings)
                    if node.operation == "setting_set":
                        value = render(node.value, 2000)
                        try:
                            value = json.loads(value)
                        except ValueError:
                            pass
                        if type(value) is not type(settings.defaults[node.key]):
                            raise ExecutionError("Setting value must match its configured default type.")
                        if self.store:
                            schema.bind(store).update(**{node.key: value})
                        else:
                            values.setdefault("__settings__", {})[node.key] = value
                    else:
                        value = schema.bind(store).get()[node.key] if self.store else values.get("__settings__", {}).get(node.key, settings.defaults[node.key])
                    variables[f"settings.{node.key}"] = value
                    variables["store.value"] = value
                    messages.append({"kind": "reply", "content": render(node.response, 2000), "ephemeral": node.ephemeral})
                elif node.operation.startswith("store_"):
                    if node.operation == "store_set":
                        value = render(node.value, 2000)
                        try:
                            value = json.loads(value)
                        except ValueError:
                            pass
                        if store:
                            store.set(node.key, value)
                        else:
                            values[node.key] = value
                    elif node.operation == "store_increment":
                        amount = render(node.value, 100)
                        try:
                            amount = int(amount)
                        except ValueError:
                            raise ExecutionError("Counter increment must be an integer.") from None
                        if store:
                            value = store.increment(node.key, amount)
                        else:
                            previous = values.get(node.key, 0)
                            if type(previous) is not int:
                                raise ExecutionError("This storage key is not an integer counter.")
                            value = previous + amount
                            values[node.key] = value
                    else:
                        value = store.get(node.key, "") if store else values.get(node.key, "")
                    variables["store.value"] = value
                    messages.append({"kind": "reply", "content": render(node.response, 2000), "ephemeral": node.ephemeral})
                else:
                    data.update(node_id=node.id, target=render(node.target, 100) if node.operation == "moderation" else "", reason=render(node.reason, 300), value=render(node.value, 2000))
                    if node.operation == "moderation":
                        if not context.in_server:
                            raise ExecutionError("Moderation requires a server.")
                        permission = {"kick": "kick_members", "ban": "ban_members", "timeout": "moderate_members"}[node.moderation_action]
                        if permission not in context.permissions and "administrator" not in context.permissions:
                            raise ExecutionError(f"You need the {permission.replace('_', ' ')} permission.")
                        data["content"] = f"Confirm {node.moderation_action} for member {data['target']}? Reason: {data['reason']}"
                    elif node.operation == "schedule":
                        job_id = f"preview-job-{len(self.state['jobs']) + 1}"
                        if not self.store:
                            self.state["jobs"][job_id] = {"status": "pending", "channel_id": context.channel_id, "text": data["value"], "delay": node.delay}
                        data["content"] = f"Scheduled job: {job_id}"
                        data["preview_job_id"] = job_id
                    else:
                        job = self.state["jobs"].get(data["value"])
                        if job:
                            job["status"] = "cancelled"
                        data["content"] = "Job cancelled." if job else "Job not found."
                    messages.append(data)
            trace.append(step)
            edge = None if component and current == component.get("node_id") else next((edge for edge in self.definition.edges if edge.source == current and edge.branch == branch), None)
            if edge is None:
                if not messages:
                    raise ExecutionError("This command produced no response.")
                if len(messages) > 5:
                    raise ExecutionError("A command can send at most five responses.")
                if trigger.cooldown and not component:
                    self.cooldowns[key] = now + trigger.cooldown
                if mode == "prefix":
                    for message in messages:
                        message["ephemeral"] = False
                return {"messages": messages, "trace": trace, "state": copy.deepcopy(self.state)}
            current = edge.target
        raise ExecutionError("Execution step budget exceeded.")


    @staticmethod
    def validate_options(trigger, supplied):
        if set(supplied) - {option.name for option in trigger.options}:
            raise ExecutionError("Unknown command argument.")
        result = {}
        for option in trigger.options:
            if option.name not in supplied and option.required:
                raise ExecutionError(f"Missing argument: {option.name}.")
            value = supplied.get(option.name, option.default)
            kind = {"str": str, "int": int, "float": float, "bool": bool}[option.type]
            if type(value) is not kind and not (kind is float and type(value) is int):
                raise ExecutionError(f"Invalid value for {option.name}.")
            if type(value) is float and not math.isfinite(value):
                raise ExecutionError(f"Invalid value for {option.name}.")
            if option.choices and value not in option.choices:
                raise ExecutionError(f"Choose a listed value for {option.name}.")
            if type(value) is str and len(value) > 6000:
                raise ExecutionError("Argument exceeds the text limit.")
            result[option.name] = value
        return result
