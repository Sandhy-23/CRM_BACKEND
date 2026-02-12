from app import app
from extensions import db
from sqlalchemy import text

def add_geo_columns():
    with app.app_context():
        print("--- 🌍 Checking Geo Columns in 'leads' table ---")
        columns_to_check = ["city", "state", "country", "ip_address"]
        
        with db.engine.connect() as connection:
            for col in columns_to_check:
                try:
                    # Try to select the column to see if it exists
                    connection.execute(text(f"SELECT {col} FROM leads LIMIT 1"))
                    print(f"✅ Column '{col}' already exists.")
                except Exception:
                    print(f"⚠️ Column '{col}' missing. Adding...")
                    try:
                        connection.execute(text(f"ALTER TABLE leads ADD COLUMN {col} VARCHAR(100)"))
                        print(f"   -> Added '{col}' successfully.")
                    except Exception as e:
                        print(f"   ❌ Failed to add '{col}': {e}")

if __name__ == "__main__":
    add_geo_columns()