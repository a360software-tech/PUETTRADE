"""Create initial trading platform schema.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-04-02 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "positions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("epic", sa.String(), nullable=False),
        sa.Column("execution_mode", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_positions_status_epic_mode", "positions", ["status", "epic", "execution_mode"])

    op.create_table(
        "engine_meta",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "engine_epics",
        sa.Column("epic", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("epic"),
    )

    op.create_table(
        "execution_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("epic", sa.String(), nullable=False),
        sa.Column("position_id", sa.String(), nullable=True),
        sa.Column("execution_mode", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_execution_events_position_event",
        "execution_events",
        ["position_id", "epic", "event_type"],
    )

    op.create_table(
        "candles",
        sa.Column("epic", sa.String(), nullable=False),
        sa.Column("resolution", sa.String(), nullable=False),
        sa.Column("time", sa.String(), nullable=False),
        sa.Column("open", sa.String(), nullable=False),
        sa.Column("high", sa.String(), nullable=False),
        sa.Column("low", sa.String(), nullable=False),
        sa.Column("close", sa.String(), nullable=False),
        sa.Column("volume", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("epic", "resolution", "time"),
    )
    op.create_index("idx_candles_epic_resolution_time", "candles", ["epic", "resolution", sa.text("time DESC")])

    op.create_table(
        "candle_sync_state",
        sa.Column("epic", sa.String(), nullable=False),
        sa.Column("resolution", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_synced_at", sa.String(), nullable=False),
        sa.Column("last_candle_time", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("epic", "resolution"),
    )


def downgrade() -> None:
    op.drop_table("candle_sync_state")
    op.drop_index("idx_candles_epic_resolution_time", table_name="candles")
    op.drop_table("candles")
    op.drop_index("idx_execution_events_position_event", table_name="execution_events")
    op.drop_table("execution_events")
    op.drop_table("engine_epics")
    op.drop_table("engine_meta")
    op.drop_index("idx_positions_status_epic_mode", table_name="positions")
    op.drop_table("positions")
