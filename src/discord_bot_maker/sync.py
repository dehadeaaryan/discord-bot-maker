"""Deterministic command registration diffs with before/after payloads."""

# Discord-generated identity does not describe registration behavior.
IGNORED = {"id", "application_id", "guild_id", "version"}


def normalize(value, *, top=True):
    if isinstance(value, dict):
        result = {key: normalize(item, top=False) for key, item in value.items() if not (top and key in IGNORED)}
        # Discord returns explicit defaults that local registration omits.
        for key in ("options", "choices", "channel_types", "name_localizations", "description_localizations"):
            if not result.get(key):
                result.pop(key, None)
        for key in ("min_value", "max_value", "min_length", "max_length"):
            if result.get(key) is None:
                result.pop(key, None)
        for key in ("autocomplete", "required"):
            if result.get(key) is False:
                result.pop(key, None)
        if top:
            result.setdefault("type", 1)
            result.setdefault("nsfw", False)
            permissions = result.get("default_member_permissions")
            result["default_member_permissions"] = str(permissions) if permissions is not None else None
            for key in ("contexts", "integration_types"):
                if result.get(key) is None:
                    result.pop(key, None)
            if result.get("dm_permission", True) is not False:
                result.pop("dm_permission", None)
        return result
    if isinstance(value, list):
        return [normalize(item, top=False) for item in value]
    return value


def preview(local, remote, guild_id=None):
    def index(items):
        result = {}
        for item in items:
            item = normalize(item)
            key = (item.get("type", 1), item["name"])
            if key in result:
                raise ValueError("Duplicate command in registration snapshot.")
            result[key] = item
        return result
    wanted, current = index(local), index(remote)
    changes = []
    for key in sorted(wanted.keys() | current.keys()):
        before, after = current.get(key), wanted.get(key)
        action = "add" if before is None else "remove" if after is None else "unchanged" if before == after else "change"
        changes.append({"name": key[1], "type": key[0], "action": action, "before": before, "after": after})
    return {"scope": "guild" if guild_id else "global", "guild_id": guild_id, "changes": changes}
