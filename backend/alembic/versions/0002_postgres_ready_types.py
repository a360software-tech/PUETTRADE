"""Convert payloads to JSON and candles to numeric types.

Revision ID: 0002_postgres_ready_types
Revises: 0001_initial_schema
Create Date: 2026-04-02 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_postgres_ready_types"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TABLE positions ALTER COLUMN payload TYPE JSONB USING payload::jsonb")
        op.execute("ALTER TABLE engine_meta ALTER COLUMN payload TYPE JSONB USING payload::jsonb")
        op.execute("ALTER TABLE engine_epics ALTER COLUMN payload TYPE JSONB USING payload::jsonb")
        op.execute("ALTER TABLE execution_events ALTER COLUMN payload TYPE JSONB USING payload::jsonb")
        op.execute("ALTER TABLE candles ALTER COLUMN open TYPE NUMERIC(18, 8) USING open::numeric")
        op.execute("ALTER TABLE candles ALTER COLUMN high TYPE NUMERIC(18, 8) USING high::numeric")
        op.execute("ALTER TABLE candles ALTER COLUMN low TYPE NUMERIC(18, 8) USING low::numeric")
        op.execute("ALTER TABLE candles ALTER COLUMN close TYPE NUMERIC(18, 8) USING close::numeric")
        op.execute("ALTER TABLE candles ALTER COLUMN volume TYPE NUMERIC(18, 8) USING volume::numeric")
        return

    with op.batch_alter_table("positions") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.Text(), type_=sa.JSON())
    with op.batch_alter_table("engine_meta") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.Text(), type_=sa.JSON())
    with op.batch_alter_table("engine_epics") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.Text(), type_=sa.JSON())
    with op.batch_alter_table("execution_events") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.Text(), type_=sa.JSON())
    with op.batch_alter_table("candles") as batch_op:
        batch_op.alter_column("open", existing_type=sa.String(), type_=sa.Numeric(18, 8))
        batch_op.alter_column("high", existing_type=sa.String(), type_=sa.Numeric(18, 8))
        batch_op.alter_column("low", existing_type=sa.String(), type_=sa.Numeric(18, 8))
        batch_op.alter_column("close", existing_type=sa.String(), type_=sa.Numeric(18, 8))
        batch_op.alter_column("volume", existing_type=sa.String(), type_=sa.Numeric(18, 8))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TABLE positions ALTER COLUMN payload TYPE TEXT USING payload::text")
        op.execute("ALTER TABLE engine_meta ALTER COLUMN payload TYPE TEXT USING payload::text")
        op.execute("ALTER TABLE engine_epics ALTER COLUMN payload TYPE TEXT USING payload::text")
        op.execute("ALTER TABLE execution_events ALTER COLUMN payload TYPE TEXT USING payload::text")
        op.execute("ALTER TABLE candles ALTER COLUMN open TYPE VARCHAR USING open::text")
        op.execute("ALTER TABLE candles ALTER COLUMN high TYPE VARCHAR USING high::text")
        op.execute("ALTER TABLE candles ALTER COLUMN low TYPE VARCHAR USING low::text")
        op.execute("ALTER TABLE candles ALTER COLUMN close TYPE VARCHAR USING close::text")
        op.execute("ALTER TABLE candles ALTER COLUMN volume TYPE VARCHAR USING volume::text")
        return

    with op.batch_alter_table("positions") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.JSON(), type_=sa.Text())
    with op.batch_alter_table("engine_meta") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.JSON(), type_=sa.Text())
    with op.batch_alter_table("engine_epics") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.JSON(), type_=sa.Text())
    with op.batch_alter_table("execution_events") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.JSON(), type_=sa.Text())
    with op.batch_alter_table("candles") as batch_op:
        batch_op.alter_column("open", existing_type=sa.Numeric(18, 8), type_=sa.String())
        batch_op.alter_column("high", existing_type=sa.Numeric(18, 8), type_=sa.String())
        batch_op.alter_column("low", existing_type=sa.Numeric(18, 8), type_=sa.String())
        batch_op.alter_column("close", existing_type=sa.Numeric(18, 8), type_=sa.String())
        batch_op.alter_column("volume", existing_type=sa.Numeric(18, 8), type_=sa.String())
