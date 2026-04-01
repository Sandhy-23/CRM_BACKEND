from app import app
from extensions import db
from sqlalchemy import text

def check_tables():
    print("\n--- 🔍 CHECKING MYSQL TABLES ---")
    print(f"Target DB: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    with app.app_context():
        try:
            # Run raw SQL to list tables
            with db.engine.connect() as connection:
                result = connection.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result]
                
                print(f"✅ Found {len(tables)} tables:")
                for t in tables:
                    print(f"   - {t}")
                
                required = ['leads', 'deals', 'tasks', 'notes']
                missing = [t for t in required if t not in tables]
                
                if missing:
                    print(f"\n❌ MISSING CRITICAL TABLES: {missing}")
                    print("👉 Run 'python app.py' to trigger auto-creation (db.create_all)")
        except Exception as e:
            print(f"❌ Error connecting to MySQL: {e}")

if __name__ == "__main__":
    check_tables()