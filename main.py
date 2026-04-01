from fastapi import FastAPI, Request
from sqlalchemy import text
from db import get_engine

app = FastAPI()

# 🔹 PART 2: SIGNUP (creates tenant DB)
@app.post("/signup")
def signup(data: dict):
    tenant = data["company"]
    email = data["email"]

    db_name = f"tenant_{tenant}"

    master_engine = get_engine("master_db")

    # 1. Create database
    with master_engine.connect() as conn:
        # Drop if exists to avoid error during testing re-runs
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))

    # 2. Load template.sql
    tenant_engine = get_engine(db_name)

    with tenant_engine.connect() as conn:
        try:
            with open("template.sql", "r", encoding="utf-8") as file:
                sql = file.read()
                # Split by semicolon but ignore empty statements
                for stmt in sql.split(";"):
                    if stmt.strip():
                        conn.execute(text(stmt))
        except FileNotFoundError:
            print("⚠️ template.sql not found. Skipping schema creation.")

    # 3. Save tenant to registry
    with master_engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO tenant_registry 
            (tenant_name, tenant_db_name, tenant_domain, super_admin_email)
            VALUES (:name, :db, :domain, :email)
        """), {
            "name": tenant,
            "db": db_name,
            "domain": tenant,
            "email": email
        })

    return {"message": "Tenant created"}

# 🔹 PART 3: Tenant Resolver
def get_tenant_db(request: Request):
    tenant = request.headers.get("X-Tenant")

    if not tenant:
        raise Exception("Tenant header missing")

    master_engine = get_engine("master_db")

    with master_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT tenant_db_name FROM tenant_registry WHERE tenant_domain=:tenant"
        ), {"tenant": tenant}).fetchone()

    if not result:
        raise Exception("Invalid tenant")

    return get_engine(result[0])

# 🔹 PART 4: Test API
@app.get("/leads")
def get_leads(request: Request):
    db = get_tenant_db(request)

    with db.connect() as conn:
        result = conn.execute(text("SELECT * FROM leads"))
        # Using ._mapping for SQLAlchemy 1.4+ compatibility
        return [dict(row._mapping) for row in result]