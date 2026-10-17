"""Restart-safe reminders for one locally running bot per storage file."""

import time
import uuid

from .responses import UserError


class ReminderQueue:
    def __init__(self, store):
        self.database = store._database

    def _table(self, connection):
        connection.execute("CREATE TABLE IF NOT EXISTS reminders (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, server_id TEXT NOT NULL, channel_id TEXT NOT NULL, message TEXT NOT NULL, due REAL NOT NULL, lease REAL NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'pending')")

    def add(self, user_id, server_id, channel_id, minutes, message):
        if type(minutes) is not int or not 1 <= minutes <= 43200:
            raise UserError("Choose a reminder between 1 minute and 30 days.")
        if not isinstance(message, str) or not 1 <= len(message) <= 1500:
            raise UserError("Reminder text must contain 1–1500 characters.")
        reminder_id = uuid.uuid4().hex[:12]
        with self.database.transaction() as connection:
            self._table(connection)
            count = connection.execute("SELECT COUNT(*) FROM reminders WHERE user_id=? AND status IN ('pending','sending')", (str(user_id),)).fetchone()[0]
            if count >= 25:
                raise UserError("You already have 25 pending reminders. Cancel one first.")
            connection.execute("INSERT INTO reminders(id,user_id,server_id,channel_id,message,due) VALUES(?,?,?,?,?,?)", (reminder_id, str(user_id), str(server_id or ""), str(channel_id), message, time.time() + minutes * 60))
        return reminder_id

    def pending(self, user_id, server_id):
        with self.database.transaction() as connection:
            self._table(connection)
            return [dict(zip(("id", "message", "due", "status"), row)) for row in connection.execute("SELECT id,message,due,status FROM reminders WHERE user_id=? AND server_id=? AND status IN ('pending','sending') ORDER BY due LIMIT 25", (str(user_id), str(server_id or "")))]

    def cancel(self, reminder_id, user_id, server_id):
        with self.database.transaction() as connection:
            self._table(connection)
            return connection.execute("DELETE FROM reminders WHERE id=? AND user_id=? AND server_id=? AND status='pending'", (reminder_id, str(user_id), str(server_id or ""))).rowcount > 0

    def claim(self, now=None):
        now = time.time() if now is None else now
        with self.database.transaction() as connection:
            self._table(connection)
            connection.execute("DELETE FROM reminders WHERE status IN ('sent','failed') AND due < ?", (now - 86400,))
            row = connection.execute("SELECT id,user_id,server_id,channel_id,message,attempts FROM reminders WHERE due<=? AND lease<=? AND status IN ('pending','sending') ORDER BY due LIMIT 1", (now, now)).fetchone()
            if row:
                connection.execute("UPDATE reminders SET lease=?,status='sending',attempts=attempts+1 WHERE id=?", (now + 120, row[0]))
                return dict(zip(("id", "user_id", "server_id", "channel_id", "message", "attempts"), row))
        return None

    def finish(self, reminder_id, success, attempts=0):
        with self.database.transaction() as connection:
            connection.execute("UPDATE reminders SET status=?,lease=0,due=? WHERE id=?", ("sent" if success else "failed" if attempts >= 4 else "pending", time.time() + min(3600, 30 * 2**attempts), reminder_id))
