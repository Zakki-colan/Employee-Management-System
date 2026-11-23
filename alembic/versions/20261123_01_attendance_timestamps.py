"""convert attendance times to timezone-aware timestamps

Revision ID: 20261123_01
Revises: de7a04bf249f
Create Date: 2026-11-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261123_01"
down_revision: Union[str, Sequence[str], None] = "de7a04bf249f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attendances",
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "attendances",
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE attendances
        SET check_in_at = (date + check_in) AT TIME ZONE 'Asia/Kolkata'
        """
    )
    op.execute(
        """
        UPDATE attendances
        SET check_out_at = (date + check_out) AT TIME ZONE 'Asia/Kolkata'
        WHERE check_out IS NOT NULL
        """
    )

    op.alter_column("attendances", "check_in_at", nullable=False)
    op.drop_column("attendances", "check_out")
    op.drop_column("attendances", "check_in")
    op.alter_column("attendances", "check_in_at", new_column_name="check_in")
    op.alter_column("attendances", "check_out_at", new_column_name="check_out")

    op.create_index(
        "uq_attendances_one_open_session",
        "attendances",
        ["employee_id"],
        unique=True,
        postgresql_where=sa.text("check_out IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_attendances_one_open_session",
        table_name="attendances",
    )
    op.add_column("attendances", sa.Column("check_in_time", sa.Time(), nullable=True))
    op.add_column("attendances", sa.Column("check_out_time", sa.Time(), nullable=True))
    op.execute(
        "UPDATE attendances "
        "SET check_in_time = CAST(check_in AT TIME ZONE 'UTC' AS time)"
    )
    op.execute(
        "UPDATE attendances "
        "SET check_out_time = CAST(check_out AT TIME ZONE 'UTC' AS time) "
        "WHERE check_out IS NOT NULL"
    )
    op.alter_column("attendances", "check_in_time", nullable=False)
    op.drop_column("attendances", "check_out")
    op.drop_column("attendances", "check_in")
    op.alter_column("attendances", "check_in_time", new_column_name="check_in")
    op.alter_column("attendances", "check_out_time", new_column_name="check_out")
