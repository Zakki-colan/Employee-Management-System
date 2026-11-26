"""Store half-day leave sessions and fractional balances."""

import sqlalchemy as sa
from alembic import op


revision = "20261126_01"
down_revision = "3c88228f26d5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("leaves") as batch:
        batch.alter_column(
            "leave_days", existing_type=sa.Integer(), type_=sa.Numeric(11, 1),
            existing_nullable=False,
        )
        batch.add_column(sa.Column("half_day_session", sa.Integer(), nullable=True))
        batch.create_check_constraint(
            "ck_leaves_half_day_session",
            "half_day_session IS NULL OR "
            "(half_day_session IN (1, 2) AND start_date = end_date AND leave_days = 0.5)",
        )

    with op.batch_alter_table("leave_balances") as batch:
        batch.alter_column(
            "used_days", existing_type=sa.Integer(), type_=sa.Numeric(11, 1),
            existing_nullable=False,
        )


def downgrade():
    # Check constraints stop the downgrade before fractional records can be rounded.
    with op.batch_alter_table("leaves") as batch:
        batch.create_check_constraint(
            "ck_leaves_can_drop_half_day",
            "half_day_session IS NULL AND leave_days = CAST(leave_days AS INTEGER)",
        )
    with op.batch_alter_table("leave_balances") as batch:
        batch.create_check_constraint(
            "ck_leave_balances_can_drop_half_day",
            "used_days = CAST(used_days AS INTEGER)",
        )

    with op.batch_alter_table("leaves") as batch:
        batch.drop_constraint("ck_leaves_can_drop_half_day", type_="check")
        batch.drop_constraint("ck_leaves_half_day_session", type_="check")
        batch.drop_column("half_day_session")
        batch.alter_column(
            "leave_days", existing_type=sa.Numeric(11, 1), type_=sa.Integer(),
            existing_nullable=False,
        )
    with op.batch_alter_table("leave_balances") as batch:
        batch.drop_constraint("ck_leave_balances_can_drop_half_day", type_="check")
        batch.alter_column(
            "used_days", existing_type=sa.Numeric(11, 1), type_=sa.Integer(),
            existing_nullable=False,
        )
