"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(8), unique=True, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="ACTIVE"),
        sa.Column("settings", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "session_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.Text, nullable=False),
        sa.Column("role", sa.String(10), nullable=False, server_default="GUEST"),
        sa.Column("is_banned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", "display_name", name="uq_session_members_name"),
    )

    op.create_table(
        "tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("provider_track_id", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("artist", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("artwork_url", sa.Text, nullable=True),
        sa.Column("explicit", sa.Boolean, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("metadata_status", sa.String(10), nullable=False, server_default="PENDING"),
        sa.UniqueConstraint("provider", "provider_track_id", name="uq_tracks_provider_id"),
    )

    op.create_table(
        "session_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("added_by_member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("session_members.id"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(10), nullable=False, server_default="QUEUED"),
        sa.Column("score_cached", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("session_id", "track_id", name="uq_session_tracks_dedup"),
    )

    op.create_table(
        "votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("session_tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("session_members.id"), nullable=False),
        sa.Column("value", sa.SmallInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("session_track_id", "member_id", name="uq_votes_member_track"),
        sa.CheckConstraint("value IN (1, -1)", name="ck_votes_value"),
    )

    op.create_table(
        "playback_states",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("current_session_track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("session_tracks.id"), nullable=True),
        sa.Column("state", sa.String(10), nullable=False, server_default="STOPPED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("position_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("events_session_id_idx", "events", ["session_id"])


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("playback_states")
    op.drop_table("votes")
    op.drop_table("session_tracks")
    op.drop_table("tracks")
    op.drop_table("session_members")
    op.drop_table("sessions")
