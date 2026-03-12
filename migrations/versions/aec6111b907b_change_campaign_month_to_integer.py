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
    # Following manual SQL steps to fix AUTO_INCREMENT issue.
    
    # Step 3 (from user): Temporarily Remove Foreign Keys
    try:
        op.execute("ALTER TABLE leads DROP FOREIGN KEY leads_ibfk_1")
    except Exception as e:
        print(f"Info: Could not drop FK 'leads_ibfk_1'. It might not exist. Error: {e}")
    try:
        # Also dropping the campaign_logs FK from previous context
        op.execute("ALTER TABLE campaign_logs DROP FOREIGN KEY fk_campaign_logs_campaign_id")
    except Exception as e:
        print(f"Info: Could not drop FK 'fk_campaign_logs_campaign_id'. It might not exist. Error: {e}")

    # Make child columns compatible (good practice)
    op.execute("ALTER TABLE leads MODIFY campaign_id INT")
    op.execute("ALTER TABLE campaign_logs MODIFY campaign_id INT")

    # Step 4 (from user): Fix campaigns.id Properly
    op.execute("ALTER TABLE campaigns MODIFY COLUMN id INT NOT NULL AUTO_INCREMENT")

    # Step 5 (from user): Ensure Primary Key Exists
    try:
        op.execute("ALTER TABLE campaigns ADD PRIMARY KEY (id)")
    except Exception as e:
        print(f"Info: Primary key likely already exists. Error: {e}")

    # Step 6 (from user): Recreate the Foreign Keys
    op.execute("""
        ALTER TABLE leads
        ADD CONSTRAINT leads_ibfk_1
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        ON DELETE SET NULL
    """)
    op.execute("""
        ALTER TABLE campaign_logs
        ADD CONSTRAINT fk_campaign_logs_campaign_id
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
    """)


def downgrade():
    # Downgrading this complex, manual migration is not recommended.
    # It's safer to restore from a backup if needed.
    pass