"""lte cells + identities

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('lte_cells',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('pci', sa.Integer(), nullable=False),
    sa.Column('tac', sa.Integer(), nullable=True),
    sa.Column('band', sa.Integer(), nullable=True),
    sa.Column('earfcn', sa.Integer(), nullable=True),
    sa.Column('freq_mhz', sa.Double(), nullable=True),
    sa.Column('plmn', sa.Text(), nullable=True),
    sa.Column('signal_dbm', sa.Integer(), nullable=True),
    sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lte_cells_device_id_observed_at', 'lte_cells', ['device_id', 'observed_at'], unique=False)
    op.create_index('ix_lte_cells_observed_at', 'lte_cells', ['observed_at'], unique=False)
    op.create_index('ix_lte_cells_pci', 'lte_cells', ['pci'], unique=False)

    op.create_table('lte_identities',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('value_encrypted', sa.LargeBinary(), nullable=False),
    sa.Column('value_hash', sa.Text(), nullable=False),
    sa.Column('s_tmsi', sa.Text(), nullable=True),
    sa.Column('pci', sa.Integer(), nullable=True),
    sa.Column('tac', sa.Integer(), nullable=True),
    sa.Column('earfcn', sa.Integer(), nullable=True),
    sa.Column('band', sa.Integer(), nullable=True),
    sa.Column('plmn', sa.Text(), nullable=True),
    sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lte_identities_value_hash', 'lte_identities', ['value_hash'], unique=False)
    op.create_index('ix_lte_identities_device_id_observed_at', 'lte_identities', ['device_id', 'observed_at'], unique=False)
    op.create_index('ix_lte_identities_observed_at', 'lte_identities', ['observed_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_lte_identities_observed_at', table_name='lte_identities')
    op.drop_index('ix_lte_identities_device_id_observed_at', table_name='lte_identities')
    op.drop_index('ix_lte_identities_value_hash', table_name='lte_identities')
    op.drop_table('lte_identities')
    op.drop_index('ix_lte_cells_pci', table_name='lte_cells')
    op.drop_index('ix_lte_cells_observed_at', table_name='lte_cells')
    op.drop_index('ix_lte_cells_device_id_observed_at', table_name='lte_cells')
    op.drop_table('lte_cells')