
from alembic import op
import sqlalchemy as sa


revision = "20261125_01"
down_revision = "f582e91719d1"
branch_labels = None
depends_on = None


def _upgrade():
    # Create the leave type lookup table.
    op.create_table(
        "leave_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    # Insert the initial leave types with stable IDs.
    leave_types = sa.table(
        "leave_types",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        leave_types,
        [
            {"id": 1, "name": "Sick Leave", "is_active": True},
            {"id": 2, "name": "Casual Leave", "is_active": True},
            {"id": 3, "name": "Annual Leave", "is_active": True},
            {"id": 4, "name": "Emergency Leave", "is_active": True},
        ],
    )

    # Advance the sequence past the explicit IDs before inserting legacy names.
    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('leave_types', 'id'),
            (SELECT MAX(id) FROM leave_types)
        )
    """)

    # Preserve historical names without offering them for new requests.
    op.execute("""
        INSERT INTO leave_types (name, is_active)
        SELECT DISTINCT leaves.leave_type, false
        FROM leaves
        WHERE NOT EXISTS (
            SELECT 1 FROM leave_types WHERE leave_types.name = leaves.leave_type
        )
        ORDER BY leaves.leave_type
    """)

    # Add the new column as nullable initially.
    op.add_column(
        "leaves",
        sa.Column("leave_type_id", sa.Integer(), nullable=True),
    )

    # Convert existing leave names into their corresponding IDs.
    op.execute("""
        UPDATE leaves
        SET leave_type_id = leave_types.id
        FROM leave_types
        WHERE leaves.leave_type = leave_types.name
    """)

    # Stop migration if any old leave type could not be mapped.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM leaves
                WHERE leave_type_id IS NULL
            ) THEN
                RAISE EXCEPTION
                'Some existing leave types could not be mapped';
            END IF;
        END $$;
    """)

    # Make the new leave type reference mandatory.
    op.alter_column(
        "leaves",
        "leave_type_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_leaves_leave_type_id",
        "leaves",
        "leave_types",
        ["leave_type_id"],
        ["id"],
    )

    # Remove the old text column after successful data conversion.
    op.drop_column("leaves", "leave_type")


def _downgrade():
    op.add_column(
        "leaves",
        sa.Column("leave_type", sa.String(50), nullable=True),
    )

    op.execute("""
        UPDATE leaves
        SET leave_type = leave_types.name
        FROM leave_types
        WHERE leaves.leave_type_id = leave_types.id
    """)

    op.alter_column(
        "leaves",
        "leave_type",
        existing_type=sa.String(50),
        nullable=False,
    )

    op.drop_constraint(
        "fk_leaves_leave_type_id",
        "leaves",
        type_="foreignkey",
    )

    # Remove the foreign-key-backed lookup column after the constraint is gone.
    op.drop_column("leaves", "leave_type_id")

    op.drop_table("leave_types")


upgrade = _upgrade
downgrade = _downgrade
