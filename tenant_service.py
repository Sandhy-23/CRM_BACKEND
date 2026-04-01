from sqlalchemy import create_engine, text
import os

DB_USER = "root"
DB_PASS = "1234"
DB_HOST = "localhost"

def create_tenant_database(db_name):
    """Creates a new MySQL database for the tenant."""
    print(f"🔧 [DEBUG] Attempting to create DB: {db_name}")
    engine = create_engine("mysql+pymysql://root:1234@localhost")
    with engine.begin() as conn:
        # ✅ STEP 1: Check if DB exists
        result = conn.execute(text(f"SHOW DATABASES LIKE '{db_name}'")).fetchone()
        if result:
            # ✅ STEP 2: If exists → DROP it (clean start)
            print(f"⚠️ [DEBUG] Database {db_name} already exists. Dropping it for a clean start.")
            conn.execute(text(f"DROP DATABASE {db_name}"))
        # ✅ STEP 3: Create DB again
        conn.execute(text(f"CREATE DATABASE {db_name}"))
    print(f"✅ [DEBUG] Fresh DB created successfully: {db_name}")

def clone_database_structure(target_db, source_db="crm_db"):
    """Clones all table structures from source_db to target_db."""
    engine = create_engine("mysql+pymysql://root:1234@localhost")
    
    with engine.begin() as conn:
        # 1. Get all tables from source
        result = conn.execute(text(f"SHOW TABLES FROM {source_db}"))
        tables = [row[0] for row in result]

        print(f"🚜 Cloning {len(tables)} tables from {source_db} to {target_db}...")
        
        # 2. Clone each table structure
        for table in tables:
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {target_db}.{table} LIKE {source_db}.{table}"))
    
    print(f"✅ [DEBUG] Structure cloned for {target_db}")

def seed_tenant_data(db_name, admin_email):
    """
    STEP 7 & 8: Inserts default setup data and the first Admin user.
    Avoids 'name' column mismatch by selecting specific columns.
    """
    engine = create_engine(f"mysql+pymysql://root:1234@localhost/{db_name}")
    
    with engine.begin() as conn:
        # ✅ STEP 7: Insert default data (Required roles/statuses)
        # Using try-except in case specific tables are missing in some templates
        try:
            conn.execute(text(f"INSERT INTO {db_name}.roles (name) VALUES ('Admin'), ('Manager')"))
            conn.execute(text(f"INSERT INTO {db_name}.status (name) VALUES ('New'), ('In Progress'), ('Closed')"))
        except Exception as e:
            print(f"⚠️ [DEBUG] Skipping default role/status insert: {e}")

        # ✅ STEP 8: Create admin user (Credential Clone)
        user_data = conn.execute(text("""
            SELECT email, password FROM master_db.users WHERE email = :email AND role = 'Super Admin'
        """), {"email": admin_email}).fetchone()

        if user_data:
            # user_data is a Row, accessed via .email or .password (SQLAlchemy 2.0 style)
            conn.execute(text(f"""
                INSERT INTO {db_name}.users (email, password, role, status, is_approved)
                VALUES (:email, :password, 'Admin', 'Active', 1)
            """), {"email": user_data[0], "password": user_data[1]})
        
    print(f"✅ [DEBUG] Tenant defaults and admin ({admin_email}) seeded into {db_name}")

def register_tenant(company, db_name, email):
    """Registers the tenant details in the master_db registry."""
    engine = create_engine("mysql+pymysql://root:1234@localhost/master_db")
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO tenant_registry (tenant_name, tenant_db_name, tenant_domain, super_admin_email)
            VALUES (:name, :db, :domain, :email)
        """), {"name": company, "db": db_name, "domain": company.lower().replace(' ', ''), "email": email})
    print(f"✅ [DEBUG] Tenant {company} registered in master_db")