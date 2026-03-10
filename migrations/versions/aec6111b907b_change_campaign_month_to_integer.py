"""Change campaign month to integer and fix ID types

Revision ID: aec6111b907b
Revises: ff9b1a2eed45
Create Date: 2026-03-10 17:05:14.123456

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'aec6111b907b'
down_revision = 'ff9b1a2eed45'
branch_labels = None
depends_on = None


def upgrade():
    # 1️⃣ Drop foreign keys
    op.drop_constraint('fk_campaign_logs_campaign_id', 'campaign_logs', type_='foreignkey')
    op.drop_constraint('leads_ibfk_1', 'leads', type_='foreignkey')

    # 2️⃣ Change campaigns.id type
    op.alter_column(
        'campaigns',
        'id',
        existing_type=sa.String(length=36),
        type_=sa.Integer(),
        autoincrement=True
    )

    # 3️⃣ Change campaign_logs.campaign_id
    op.alter_column(
        'campaign_logs',
        'campaign_id',
        existing_type=sa.String(length=36),
        type_=sa.Integer()
    )

    # 4️⃣ Change leads.campaign_id
    op.alter_column(
        'leads',
        'campaign_id',
        existing_type=sa.String(length=36),
        type_=sa.Integer()
    )

    # 5️⃣ Add foreign keys again
    op.create_foreign_key(
        'fk_campaign_logs_campaign_id',
        'campaign_logs',
        'campaigns',
        ['campaign_id'],
        ['id']
    )
    op.create_foreign_key(
        'leads_ibfk_1',
        'leads',
        'campaigns',
        ['campaign_id'],
        ['id']
    )


def downgrade():
    # Revert month change
    op.alter_column('campaigns', 'month',
               existing_type=sa.Integer(),
               type_=mysql.VARCHAR(length=20),
               existing_nullable=True)

    # Revert ID changes
    op.drop_constraint('fk_campaign_logs_campaign_id', 'campaign_logs', type_='foreignkey')

    op.alter_column('campaign_logs', 'campaign_id', existing_type=sa.Integer(), type_=sa.String(length=36))
    op.alter_column('campaigns', 'id', existing_type=sa.Integer(), type_=sa.String(length=36))

    op.create_foreign_key('fk_campaign_logs_campaign_id', 'campaign_logs', 'campaigns', ['campaign_id'], ['id'])