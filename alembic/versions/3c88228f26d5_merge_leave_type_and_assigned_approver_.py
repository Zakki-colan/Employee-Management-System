"""merge leave type and assigned approver migrations

Revision ID: 3c88228f26d5
Revises: 20261125_01, 95b27c854a40
Create Date: 2026-11-25 19:09:47.679543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c88228f26d5'
down_revision: Union[str, Sequence[str], None] = ('20261125_01', '95b27c854a40')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
