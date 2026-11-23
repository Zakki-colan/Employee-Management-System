"""correct attendance timestamps migrated with the wrong timezone

Revision ID: 20261123_02
Revises: c75c2268794d
Create Date: 2026-11-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261123_02"
down_revision: Union[str, Sequence[str], None] = "c75c2268794d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Legacy check_in values were local India times but were interpreted as UTC.
    # Their generated timestamps are exactly 5h30m ahead of created_at.
    op.execute(
        sa.text(
            """
            UPDATE attendances
            SET check_in = check_in - INTERVAL '5 hours 30 minutes',
                check_out = CASE
                    WHEN check_out IS NULL THEN NULL
                    ELSE check_out - INTERVAL '5 hours 30 minutes'
                END
            WHERE EXTRACT(EPOCH FROM (check_in - created_at))
                  BETWEEN 19770 AND 19830
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "This data correction cannot be safely reversed without restoring a database backup."
    )
