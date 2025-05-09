"""Initial database schema

Revision ID: 96daf47921b4
Revises: 
Create Date: 2025-04-23 18:42:13.290729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96daf47921b4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('markets',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('traders',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('alert_rules',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('market_id', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('threshold', sa.Float(), nullable=False),
    sa.Column('condition', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('market_snapshots',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('market_id', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('raw_data', sa.Text(), nullable=False),
    sa.Column('mid_price', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_market_snapshots_timestamp'), 'market_snapshots', ['timestamp'], unique=False)
    op.create_table('trader_scores',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('trader_id', sa.String(), nullable=False),
    sa.Column('market_id', sa.String(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], ),
    sa.ForeignKeyConstraint(['trader_id'], ['traders.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trader_scores_timestamp'), 'trader_scores', ['timestamp'], unique=False)
    op.create_table('true_prices',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('market_id', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('mid_price', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_true_prices_timestamp'), 'true_prices', ['timestamp'], unique=False)
    op.create_table('alert_notifications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('alert_rule_id', sa.String(), nullable=False),
    sa.Column('market_id', sa.String(), nullable=False),
    sa.Column('true_price', sa.Float(), nullable=False),
    sa.Column('mid_price', sa.Float(), nullable=False),
    sa.Column('difference', sa.Float(), nullable=False),
    sa.Column('sent_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['alert_rule_id'], ['alert_rules.id'], ),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('alert_notifications')
    op.drop_index(op.f('ix_true_prices_timestamp'), table_name='true_prices')
    op.drop_table('true_prices')
    op.drop_index(op.f('ix_trader_scores_timestamp'), table_name='trader_scores')
    op.drop_table('trader_scores')
    op.drop_index(op.f('ix_market_snapshots_timestamp'), table_name='market_snapshots')
    op.drop_table('market_snapshots')
    op.drop_table('alert_rules')
    op.drop_table('traders')
    op.drop_table('markets')
    # ### end Alembic commands ###
