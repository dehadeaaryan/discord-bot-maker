"""Initial project, session, revision and runner storage."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sessions", sa.Column("id", sa.String(64), primary_key=True), sa.Column("owner_id", sa.String(80), nullable=False), sa.Column("username", sa.String(100), nullable=False), sa.Column("csrf", sa.String(100), nullable=False), sa.Column("expires", sa.Float, nullable=False))
    op.create_table("projects",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("owner_id", sa.String(80), nullable=False),
        sa.Column("name", sa.String(80), nullable=False), sa.Column("draft", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False), sa.Column("created_at", sa.Float, nullable=False), sa.Column("updated_at", sa.Float, nullable=False),
        sa.Column("encrypted_token", sa.Text), sa.Column("application_id", sa.String(25), unique=True), sa.Column("guild_id", sa.String(25)),
        sa.Column("credential_version", sa.Integer, nullable=False), sa.Column("published_revision", sa.String(36)), sa.Column("synced_revision", sa.String(36)),
        sa.Column("desired_state", sa.String(20), nullable=False), sa.Column("observed_state", sa.String(30), nullable=False),
        sa.Column("lease_owner", sa.String(36)), sa.Column("lease_until", sa.Float, nullable=False))
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_table("revisions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("definition", sa.Text, nullable=False), sa.Column("created_at", sa.Float, nullable=False))
    op.create_index("ix_revisions_project_id", "revisions", ["project_id"])
    op.create_table("events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("message", sa.String(200), nullable=False), sa.Column("created_at", sa.Float, nullable=False))
    op.create_index("ix_events_project_id", "events", ["project_id"])


def downgrade():
    for name in ("events", "revisions", "projects", "sessions"):
        op.drop_table(name)
