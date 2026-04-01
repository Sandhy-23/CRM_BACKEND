from app import app
from extensions import db
from sqlalchemy import text
from datetime import datetime

def seed_data():
    with app.app_context():
        print("--- 📊 Seeding Reports Data ---")
        
        with db.engine.connect() as connection:
            # 1. Ensure 'target' column exists in users
            try:
                connection.execute(text("ALTER TABLE users ADD COLUMN target INTEGER DEFAULT 0"))
                print("✅ Added 'target' column to users table.")
            except Exception:
                print("ℹ️ 'target' column likely exists.")

            # 2. Insert Users (Sales Reps)
            users = [
                ('Ravi Teja', 'ravi@rvh.com', 1500000),
                ('Anu S', 'anu@rvh.com', 1200000),
                ('Varshini K', 'varshini@rvh.com', 1000000)
            ]
            for name, email, target in users:
                # Check if exists
                res = connection.execute(text(f"SELECT id FROM users WHERE email = '{email}'")).fetchone()
                if not res:
                    connection.execute(text(f"""
                        INSERT INTO users (name, email, password, role, target, is_approved, status, organization_id)
                        VALUES ('{name}', '{email}', 'pbkdf2:sha256:...', 'EMPLOYEE', {target}, 1, 'Active', 1)
                    """))
                    print(f"   + Added User: {name}")
                else:
                    # Update target
                    connection.execute(text(f"UPDATE users SET target = {target} WHERE email = '{email}'"))

            # 3. Insert Leads
            leads_sql = """
            INSERT INTO leads (name, source, city, created_at, email, company, status, score, sla, owner, description, organization_id) VALUES
            ('Rahul', 'Google Ads', 'Hyderabad', datetime('now'), 'rahul@test.com', 'Indie', 'New', 'High', '24h', 'Ravi Teja', 'Test Lead', 1),
            ('Sneha', 'LinkedIn', 'Bangalore', datetime('now'), 'sneha@test.com', 'Corp', 'New', 'Med', '48h', 'Anu S', 'Test Lead', 1),
            ('Amit', 'Referrals', 'Mumbai', datetime('now'), 'amit@test.com', 'Biz', 'New', 'Low', '72h', 'Varshini K', 'Test Lead', 1),
            ('Priya', 'Organic', 'Delhi', datetime('now'), 'priya@test.com', 'Home', 'New', 'High', '24h', 'Ravi Teja', 'Test Lead', 1),
            ('Kiran', 'Google Ads', 'Hyderabad', datetime('now'), 'kiran@test.com', 'Tech', 'New', 'Med', '48h', 'Anu S', 'Test Lead', 1);
            """
            try:
                connection.execute(text(leads_sql))
                print("✅ Added 5 Dummy Leads.")
            except Exception as e:
                print(f"⚠️ Leads insert skipped (might duplicate): {e}")

            # 4. Insert Deals
            deals_sql = """
            INSERT INTO deals (title, company, value, status, stage, owner, created_at, organization_id, pipeline) VALUES
            ('CRM Implementation', 'Tech Corp', 500000, 'won', 'Proposal', 'Ravi Teja', datetime('now'), 1, 'Sales'),
            ('Website Upgrade', 'Soft Systems', 320000, 'won', 'Qualified', 'Ravi Teja', datetime('now'), 1, 'Sales'),
            ('Automation Setup', 'Green Sol', 280000, 'won', 'Qualified', 'Anu S', datetime('now'), 1, 'Sales'),
            ('Mobile App', 'Future Tech', 150000, 'open', 'New Lead', 'Varshini K', datetime('now'), 1, 'Sales'),
            ('Cloud Migration', 'DataWorks', 90000, 'lost', 'Lost', 'Anu S', datetime('now'), 1, 'Sales');
            """
            try:
                connection.execute(text(deals_sql))
                print("✅ Added 5 Dummy Deals.")
            except Exception as e:
                print(f"⚠️ Deals insert skipped: {e}")
            
            connection.commit()

if __name__ == "__main__":
    seed_data()