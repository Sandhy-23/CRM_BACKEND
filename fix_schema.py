from app import app
from extensions import db
from sqlalchemy import text

def migrate_db():
    with app.app_context():
        with db.engine.connect() as connection:
            print("Migrating database schema...")
            
            # 1. Fix Leads Table
            try:
                connection.execute(text("ALTER TABLE leads ADD COLUMN created_at DATETIME"))
                print("Added 'created_at' to leads table.")
            except Exception as e:
                print(f"leads.created_at check: {e}")

            # 2. Fix Deals Table
            deal_columns = [
                ("created_at", "DATETIME"),
                ("closed_at", "DATETIME"),
                ("status", "VARCHAR(50)")
            ]
            for col_name, col_type in deal_columns:
                try:
                    connection.execute(text(f"ALTER TABLE deals ADD COLUMN {col_name} {col_type}"))
                    print(f"Added '{col_name}' to deals table.")
                except Exception as e:
                    print(f"deals.{col_name} check: {e}")

            # 3. Fix Activities Table (if it exists but is missing columns)
            try:
                connection.execute(text("ALTER TABLE activities ADD COLUMN created_at DATETIME"))
                print("Added 'created_at' to activities table.")
            except Exception as e:
                print(f"activities.created_at check: {e}")
            
            # 4. Fix Users Table (Employee Master Data)
            user_columns = [
                ("phone", "VARCHAR(20)"),
                ("department", "VARCHAR(50)"),
                ("designation", "VARCHAR(50)"),
                ("status", "VARCHAR(20) DEFAULT 'Active'"),
                ("date_of_joining", "DATETIME")
            ]
            for col_name, col_type in user_columns:
                try:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                    print(f"Added '{col_name}' to users table.")
                except Exception as e:
                    print(f"users.{col_name} check: {e}")
            
            # 5. Fix Tasks Table
            try:
                connection.execute(text("ALTER TABLE tasks ADD COLUMN description TEXT"))
                print("Added 'description' to tasks table.")
            except Exception as e:
                print(f"tasks.description check: {e}")

            # 6. Fix Tasks Table (Quick Actions)
            task_qa_cols = [("created_by", "INTEGER"), ("created_at", "DATETIME")]
            for col_name, col_type in task_qa_cols:
                try:
                    connection.execute(text(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}"))
                    print(f"Added '{col_name}' to tasks table.")
                except Exception as e:
                    print(f"tasks.{col_name} check: {e}")

            # 7. Fix Leads Table (Assignment)
            try:
                connection.execute(text("ALTER TABLE leads ADD COLUMN assigned_to INTEGER"))
                print("Added 'assigned_to' to leads table.")
            except Exception as e:
                print(f"leads.assigned_to check: {e}")

            # 8. Fix Activity Logs (Entity Tracking)
            log_cols = [("entity_type", "VARCHAR(50)"), ("entity_id", "INTEGER")]
            for col_name, col_type in log_cols:
                try:
                    connection.execute(text(f"ALTER TABLE activity_logs ADD COLUMN {col_name} {col_type}"))
                    print(f"Added '{col_name}' to activity_logs table.")
                except Exception as e:
                    print(f"activity_logs.{col_name} check: {e}")

            # 9. Fix Contacts Table (New Module)
            contact_cols = [
                ("company", "VARCHAR(100)"),
                ("status", "VARCHAR(20) DEFAULT 'Lead'"),
                ("updated_at", "DATETIME"),
                ("assigned_to", "INTEGER"),
                ("created_by", "INTEGER")
            ]
            for col_name, col_type in contact_cols:
                try:
                    connection.execute(text(f"ALTER TABLE contacts ADD COLUMN {col_name} {col_type}"))
                    print(f"Added '{col_name}' to contacts table.")
                except Exception as e:
                    print(f"contacts.{col_name} check: {e}")

            connection.commit()
            print("Migration complete. You can now restart the server.")

if __name__ == "__main__":
    migrate_db()