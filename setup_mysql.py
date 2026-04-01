import pymysql
from config import Config
import sys

def setup_mysql():
    uri = Config.SQLALCHEMY_DATABASE_URI
    print(f"\n🔌 Testing MySQL Connection: {uri}")

    if 'sqlite' in uri:
        print("❌ Config is still pointing to SQLite. Please update config.py first.")
        return

    try:
        # Parse connection string: mysql+pymysql://user:pass@host/db_name
        # This is a basic parser for standard URIs
        connection_part = uri.split("://")[1]
        creds, address = connection_part.split("@")
        user, password = creds.split(":")
        host, db_name = address.split("/")

        print(f"   User: {user}")
        print(f"   Host: {host}")
        print(f"   Target DB: {db_name}")

        # Connect to MySQL Server (no DB selected yet)
        conn = pymysql.connect(host=host, user=user, password=password)
        cursor = conn.cursor()

        # Create DB if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"✅ Database '{db_name}' ready!")

        conn.close()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("👉 Please check your username/password in config.py")

if __name__ == "__main__":
    setup_mysql()