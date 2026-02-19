import sqlite3
from datetime import datetime
import random

conn = sqlite3.connect("crm.db")
cursor = conn.cursor()

# ---------------- CHECK COUNTS ----------------
cursor.execute("SELECT COUNT(*) FROM leads")
lead_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM deals")
deal_count = cursor.fetchone()[0]

# Note: Using 'tasks' table as per existing schema context instead of 'activities' if 'activities' doesn't exist.
# However, the prompt specifically asks for 'activities'. I will check if 'activities' table exists, if not, I'll use 'tasks'.
# Based on previous context, 'activities' table might not exist or be named 'tasks'.
# Let's try to use 'activities' as requested, but fallback or create if needed.
# For this script to work as requested, I will assume 'activities' table exists or create it if missing to avoid errors.

try:
    cursor.execute("SELECT COUNT(*) FROM activities")
    activity_count = cursor.fetchone()[0]
except sqlite3.OperationalError:
    # If table doesn't exist, create it for this script to work
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type VARCHAR(50),
            completed BOOLEAN,
            created_at DATETIME,
            organization_id INTEGER
        )
    """)
    activity_count = 0

print("Existing Leads:", lead_count)
print("Existing Deals:", deal_count)
print("Existing Activities:", activity_count)

# =================================================
# ADD LEADS (Ensure minimum 200)
# =================================================
if lead_count < 200:
    sources = ["Ads", "Social", "Referral", "Direct"]
    statuses = ["New", "Contacted", "Interested", "In Progress", "Closed"]

    for i in range(200 - lead_count):
        cursor.execute("""
            INSERT INTO leads (name, source, status, created_at, email, company, score, sla, owner, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"Dashboard Lead {i}",
            random.choice(sources),
            random.choice(statuses),
            datetime(2026, random.randint(1, 12), random.randint(1, 28)),
            f"lead{i}@dashboard.test", f"Company {i}", "Hot", "24h", "Admin", "Auto-generated"
        ))

# =================================================
# ADD DEALS (Ensure minimum 100)
# =================================================
if deal_count < 100:
    stages = ["Proposed", "Negotiating", "Won", "Lost"] # Adjusted to match schema constraints if any
    
    for i in range(100 - deal_count):
        stage = random.choice(stages)
        # Ensure status matches stage logic if needed, or just use stage
        
        cursor.execute("""
            INSERT INTO deals (title, value, stage, created_at, closed_at, pipeline)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"Dashboard Deal {i}",
            random.randint(10000, 80000),
            stage,
            datetime(2026, random.randint(1, 12), random.randint(1, 28)),
            datetime(2026, random.randint(1, 12), random.randint(1, 28)),
            "Standard Pipeline"
        ))

# =================================================
# ADD ACTIVITIES (Ensure minimum 150)
# =================================================
if activity_count < 150:
    statuses = ["Pending", "Completed"]

    for i in range(150 - activity_count):
        cursor.execute("""
            INSERT INTO activities 
            (description, status, due_date, created_at, user_id, organization_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"Follow up activity {i}",
            random.choice(statuses),
            datetime(2026, random.randint(1, 12), random.randint(1, 28)),
            datetime(2026, random.randint(1, 12), random.randint(1, 28)),
            1,
            1
        ))

conn.commit()
conn.close()

print("Dashboard data ensured successfully.")