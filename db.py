from sqlalchemy import create_engine
import os

engine_cache = {}

def get_engine(db_name):
    """
    Creates or retrieves a SQLAlchemy engine for the specified database.
    Credentials are fetched from environment variables.
    """
    if db_name not in engine_cache:
        # ✅ FIXED CREDENTIALS (NO GUESSING)
        db_user = os.getenv("DB_USER", "root")
        db_password = os.getenv("DB_PASSWORD", "1234")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "3306")
        
        # Construct connection string
        db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        engine_cache[db_name] = create_engine(db_url, pool_pre_ping=True)
        
    return engine_cache[db_name]