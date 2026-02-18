from app import app
from extensions import db
from sqlalchemy import text

def fix_tickets():
    with app.app_context():
        print("🔧 Attempting to manually add 'ticket_number' column to 'tickets' table...")
        
        with db.engine.connect() as connection:
            # 1. Add Column
            try:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN ticket_number VARCHAR(20)"))
                print("✅ Column 'ticket_number' added.")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("ℹ️ Column 'ticket_number' already exists.")
                else:
                    print(f"⚠️ Note on ADD COLUMN: {e}")

            # 2. Update NULL values (Using ID to ensure uniqueness: TKT-1, TKT-2, etc.)
            try:
                # SQLite concatenation syntax
                connection.execute(text("UPDATE tickets SET ticket_number = 'TKT-' || id WHERE ticket_number IS NULL"))
                print("✅ Updated NULL ticket_number values (Format: TKT-{id}).")
            except Exception as e:
                print(f"⚠️ Error updating ticket numbers: {e}")
            
            connection.commit()
            print("🚀 Database fix completed.")

if __name__ == "__main__":
    fix_tickets()