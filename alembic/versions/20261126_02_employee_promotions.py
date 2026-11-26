"""Add employee promotion history."""

import sqlalchemy as sa
from alembic import op


revision = "20261126_02"
down_revision = "20261126_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_promotions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("promoted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("previous_position", sa.String(100), nullable=False),
        sa.Column("new_position", sa.String(100), nullable=False),
        sa.Column("previous_salary", sa.Numeric(10, 2), nullable=False),
        sa.Column("new_salary", sa.Numeric(10, 2), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["promoted_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_employee_promotions_employee_history", "employee_promotions", ["employee_id", "id"]
    )


def downgrade() -> None:
    op.drop_index("ix_employee_promotions_employee_history", table_name="employee_promotions")
    op.drop_table("employee_promotions")
