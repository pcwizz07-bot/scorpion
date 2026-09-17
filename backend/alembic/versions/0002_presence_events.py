"""presence events

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('presence_events',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('tmsi_old', sa.Text(), nullable=True),
    sa.Column('tmsi_new', sa.Text(), nullable=True),
    sa.Column('lac', sa.Integer(), nullable=True),
    sa.Column('cell_id', sa.Integer(), nullable=True),
    sa.Column('chan', sa.Text(), nullable=True),
    sa.Column('signal_dbm', sa.Integer(), nullable=True),
    sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_presence_events_device_id_observed_at', 'presence_events', ['device_id', 'observed_at'], unique=False)
    op.create_index('ix_presence_events_tmsi_old', 'presence_events', ['tmsi_old'], unique=False)
    op.create_index('ix_presence_events_tmsi_new', 'presence_events', ['tmsi_new'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_presence_events_tmsi_new', table_name='presence_events')
    op.drop_index('ix_presence_events_tmsi_old', table_name='presence_events')
    op.drop_index('ix_presence_events_device_id_observed_at', table_name='presence_events')
    op.drop_table('presence_events')
