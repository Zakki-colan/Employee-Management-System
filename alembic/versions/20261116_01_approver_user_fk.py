from alembic import op


revision = "20261116_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("leaves_approved_by_fkey", "leaves", type_="foreignkey")
    op.create_foreign_key(
        "leaves_approved_by_fkey",
        "leaves",
        "users",
        ["approved_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("leaves_approved_by_fkey", "leaves", type_="foreignkey")
    op.create_foreign_key(
        "leaves_approved_by_fkey",
        "leaves",
        "employees",
        ["approved_by"],
        ["id"],
    )
