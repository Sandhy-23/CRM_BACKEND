from app import app
from extensions import db
from sqlalchemy import text

def recreate_campaigns_table():
    with app.app_context():
        print("🔧 Recreating 'campaigns' table to fix schema mismatch...")
        
        # 1. Drop existing table
        try:
            with db.engine.connect() as connection:
                connection.execute(text("DROP TABLE IF EXISTS campaigns"))
                print("✅ Dropped 'campaigns' table.")
        except Exception as e:
            print(f"❌ Error dropping table: {e}")
            return

        # 2. Recreate table from model
        # This will create the table with id defined as String(36) per the model
        db.create_all()
        print("✅ Recreated 'campaigns' table with correct UUID schema.")

if __name__ == "__main__":
    recreate_campaigns_table()