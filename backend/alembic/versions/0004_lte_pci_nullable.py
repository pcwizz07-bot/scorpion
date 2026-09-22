"""lte_cells.pci nullable

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-21 00:00:00.000000

Energy-only (rtl_power) detections carry no PCI.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('lte_cells', 'pci', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('lte_cells', 'pci', existing_type=sa.Integer(), nullable=False)