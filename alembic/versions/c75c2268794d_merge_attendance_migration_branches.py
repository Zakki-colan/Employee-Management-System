"""merge attendance migration branches

Revision ID: c75c2268794d
Revises: 146d75d47a5e, 20261123_01
Create Date: 2026-11-23 15:45:44.318907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c75c2268794d'
down_revision: Union[str, Sequence[str], None] = ('146d75d47a5e', '20261123_01')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
