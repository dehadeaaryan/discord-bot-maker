"""Focused, opt-in moderation with confirmation and local audit records."""
import asyncio
import json
import logging
import time
import uuid

from .responses import Button, Message, UserError

logger = logging.getLogger(__name__)
PERMISSIONS = {"kick": "kick_members", "ban": "ban_members", "timeout": "moderate_members"}


class Moderation:
    def __init__(self, bot):
        self.bot = bot

    def _check(self, ctx, member, action):
        if ctx.server is None or member.guild.id != ctx.server.id:
            raise UserError("Moderation requires a member of this server.")
        me, actor = ctx.server.me, ctx.user
        permission = PERMISSIONS[action]
        if not getattr(ctx.interaction.permissions, permission, False):
            raise UserError(f"You need the {permission.replace('_', ' ')} permission.")
        if not getattr(me.guild_permissions, permission, False):
            raise UserError(f"The bot needs the {permission.replace('_', ' ')} permission.")
        if member.id in {actor.id, me.id, ctx.server.owner_id}:
            raise UserError("You cannot moderate yourself, the bot, or the server owner.")
        if actor.id != ctx.server.owner_id and member.top_role >= actor.top_role:
            raise UserError("The member's role must be below your highest role.")
        if member.top_role >= me.top_role:
            raise UserError("The member's role must be below the bot's highest role.")
        if action == "timeout" and member.guild_permissions.administrator:
            raise UserError("Administrators cannot be timed out.")

    def _audit(self, audit_id, ctx, member, action, reason, status):
        record = {"id": audit_id, "time": time.time(), "server_id": ctx.server.id, "actor_id": ctx.user.id, "target_id": member.id, "action": action, "reason": reason, "status": status}
        with self.bot.store._database.transaction() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS dbm_audit (id TEXT PRIMARY KEY, server_id TEXT NOT NULL, record TEXT NOT NULL)")
            connection.execute("INSERT INTO dbm_audit(id,server_id,record) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET record=excluded.record", (audit_id, str(ctx.server.id), json.dumps(record)))
        logger.info("Moderation action=%s status=%s server=%s actor=%s target=%s audit=%s", action, status, ctx.server.id, ctx.user.id, member.id, audit_id)

    def audit(self, server_id, *, limit=50):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Audit limit must be between 1 and 100.")
        with self.bot.store._database.transaction() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS dbm_audit (id TEXT PRIMARY KEY, server_id TEXT NOT NULL, record TEXT NOT NULL)")
            rows = connection.execute("SELECT record FROM dbm_audit WHERE server_id=? ORDER BY rowid DESC LIMIT ?", (str(server_id), limit)).fetchall()
            return [json.loads(row[0]) for row in rows]

    def _prompt(self, ctx, member, action, reason, *, minutes=None):
        self._check(ctx, member, action)
        if not isinstance(reason, str) or not 1 <= len(reason) <= 300:
            raise UserError("Provide a moderation reason containing 1–300 characters.")
        if minutes is not None and (type(minutes) is not int or not 1 <= minutes <= 40320):
            raise UserError("Timeout must be between 1 minute and 28 days.")
        lock = asyncio.Lock()
        state = {"finished": False}
        audit_id = uuid.uuid4().hex
        async def confirm(click):
            if click.user.id != ctx.user.id:
                raise UserError("Only the moderator who opened this prompt can confirm it.")
            async with lock:
                if state["finished"]:
                    raise UserError("This confirmation has already been used or cancelled.")
                # Fetch fresh roles and permissions; do not trust the prompt's snapshot.
                target = await click.server.fetch_member(member.id)
                actor = await click.server.fetch_member(click.user.id)
                me = await click.server.fetch_member(click.server.me.id)
                from types import SimpleNamespace
                refreshed = SimpleNamespace(server=SimpleNamespace(id=click.server.id, me=me, owner_id=click.server.owner_id), user=actor, interaction=SimpleNamespace(permissions=click.channel.permissions_for(actor)))
                self._check(refreshed, target, action)
                self._audit(audit_id, click, target, action, reason, "requested")
                state["finished"] = True
                discord_reason = f"{reason} | moderator {actor.id} | audit {audit_id}"
                try:
                    if action == "kick":
                        await target.kick(reason=discord_reason)
                    elif action == "ban":
                        await click.server.ban(target, reason=discord_reason, delete_message_seconds=0)
                    else:
                        from datetime import timedelta
                        await target.timeout(timedelta(minutes=minutes), reason=discord_reason)
                except Exception:
                    # Network errors may leave an ambiguous remote outcome. Never auto-retry.
                    self._audit(audit_id, click, target, action, reason, "failed_or_unknown")
                    raise
                self._audit(audit_id, click, target, action, reason, "completed")
                return f"{action.capitalize()} completed. Audit: {audit_id}"
        async def cancel(click):
            if click.user.id != ctx.user.id:
                raise UserError("Only the moderator who opened this prompt can cancel it.")
            async with lock:
                if state["finished"]:
                    raise UserError("This confirmation has already been used or cancelled.")
                state["finished"] = True
            return "Cancelled."
        return Message(f"Confirm {action} for member {member.id}? Reason: {reason}", buttons=[Button("Confirm", reply=confirm, style="danger"), Button("Cancel", reply=cancel)], timeout=60, owner_only=True)

    def kick(self, ctx, member, *, reason):
        return self._prompt(ctx, member, "kick", reason)

    def ban(self, ctx, member, *, reason):
        return self._prompt(ctx, member, "ban", reason)

    def timeout(self, ctx, member, *, minutes, reason):
        return self._prompt(ctx, member, "timeout", reason, minutes=minutes)
