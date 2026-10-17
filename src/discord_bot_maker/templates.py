"""Small editable examples; no external services or credentials required."""

from .definition import BotDefinition


def template(name: str = "greeting") -> BotDefinition:
    content = {
        "greeting": ("hello", "Say hello", "Hello, {{user.display_name}}! 👋"),
        "rules": ("rules", "Read the server rules", "Be kind. Respect each other. Keep the conversation welcoming."),
        "faq": ("faq", "Find a quick answer", "Need a hand? Ask in #help and someone will be happy to help."),
    }
    if name not in content:
        raise ValueError("Unknown template.")
    command, description, reply = content[name]
    return BotDefinition.model_validate({
        "name": {"greeting": "Hello, world", "rules": "Server essentials", "faq": "A helping hand"}[name],
        "nodes": [
            {"id": "command-1", "kind": "trigger", "name": command, "description": description},
            {"id": "reply-1", "kind": "reply", "content": reply},
        ],
        "edges": [{"id": "edge-1", "source": "command-1", "target": "reply-1"}],
        "layout": {"positions": {"command-1": {"x": 80, "y": 120}, "reply-1": {"x": 400, "y": 120}}},
    })
