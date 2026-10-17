"""Import the v1 command dictionary without loading or executing user code."""

from .definition import BotDefinition

LEGACY_VARIABLES = {
    "<author name>": "{{user.name}}", "<author mention>": "{{user.mention}}",
    "<author display name>": "{{user.display_name}}", "<message content>": "{{message.content}}",
    "<message clean content>": "{{message.content}}", "<channel name>": "{{channel.name}}",
    "<channel mention>": "<#{{channel.id}}>", "<guild name>": "{{server.name}}",
}
UNSUPPORTED = ("<author discriminator>", "<message time>", "<channel topic>", "<channel category>", "<guild member count>", "<guild description>", "<guild features>")


def migrate_commands(commands: dict, *, name="Imported bot", prefix="!") -> BotDefinition:
    def convert(text):
        if any(variable in text for variable in UNSUPPORTED):
            raise ValueError("This reply uses a legacy variable without a v2 equivalent. Replace it before importing.")
        for old, new in LEGACY_VARIABLES.items():
            text = text.replace(old, new)
        return text

    nodes, edges, positions = [], [], {}
    for index, (command, values) in enumerate(commands.items()):
        if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= 5:
            raise ValueError("Legacy commands must contain 1–5 reply, description, emoji, image and help values.")
        reply, description, emoji, image, help_text = [*values, *[None] * (5 - len(values))]
        trigger_id, reply_id = f"command-{index + 1}", f"reply-{index + 1}"
        nodes.extend([
            {"id": trigger_id, "kind": "trigger", "name": command, "mode": "prefix", "description": (help_text or "A bot command")[:100]},
            {"id": reply_id, "kind": "embed", "title": convert(reply), "description": convert((description or "") + (f"\n{emoji}" if emoji else "")), "image_url": image},
        ])
        edges.append({"id": f"edge-{index + 1}", "source": trigger_id, "target": reply_id})
        positions[trigger_id], positions[reply_id] = {"x": 80, "y": index * 200}, {"x": 400, "y": index * 200}
    return BotDefinition.model_validate({"name": name, "prefix": prefix, "nodes": nodes, "edges": edges, "layout": {"positions": positions}})
