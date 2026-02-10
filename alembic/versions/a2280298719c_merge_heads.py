"""merge heads

Revision ID: a2280298719c
Revises: f1f6g7h8i9j0, h3i4j5k6l7m8
Create Date: 2026-02-09 21:26:22.925486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2280298719c'
down_revision: Union[str, Sequence[str], None] = ('f1f6g7h8i9j0', 'h3i4j5k6l7m8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
