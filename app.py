from flask import Flask, jsonify
from extensions import db, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from routes import auth_bp, website_bp, dashboard_bp, plan_bp, quick_actions_bp, contact_bp, lead_bp, deal_bp
from routes.chart_routes import chart_bp
from config import Config
import models
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
jwt.init_app(app)

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(website_bp) # No prefix for main website
app.register_blueprint(dashboard_bp, url_prefix="/api")
app.register_blueprint(plan_bp, url_prefix="/api")
app.register_blueprint(chart_bp, url_prefix="/api")
app.register_blueprint(quick_actions_bp, url_prefix="/api")
app.register_blueprint(contact_bp)
app.register_blueprint(lead_bp)
app.register_blueprint(deal_bp)

@app.errorhandler(IntegrityError)
def handle_integrity_error(e):
    db.session.rollback()
    print(f"❌ Database Integrity Error: {e.orig}")
    return jsonify({"error": "Database integrity error", "message": str(e.orig)}), 400

@app.errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify({"error": "Method not allowed", "message": "The method is not allowed for the requested URL."}), 405

with app.app_context():
    # db.drop_all() # Uncomment this ONLY if you need to reset the DB completely
    db.create_all()
    
    # --- Auto-Migration for Users Table (Fix for missing columns) ---
    try:
        with db.engine.connect() as connection:
            # Check if is_verified column exists
            try:
                connection.execute(text("SELECT is_verified FROM users LIMIT 1"))
            except Exception:
                print("⚠️ Column 'is_verified' not found. Applying migrations...")
                auth_cols = [
                    ("is_verified", "BOOLEAN DEFAULT 0"),
                    ("otp", "VARCHAR(6)"),
                    ("otp_expiry", "DATETIME"),
                    ("reset_token", "VARCHAR(100)"),
                    ("reset_token_expiry", "DATETIME")
                ]
                for col_name, col_type in auth_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name}")
                    except Exception:
                        pass # Column might already exist
                connection.commit()
                print("✅ User table migration complete.")
    except Exception as e:
        print(f"Migration Error: {e}")
    
    # --- Auto-Migration for Leads & Deals (Fix for missing columns) ---
    try:
        with db.engine.connect() as connection:
            # 1. Fix Leads Table
            try:
                connection.execute(text("SELECT first_name FROM leads LIMIT 1"))
            except Exception:
                print("⚠️ Column 'first_name' not found in leads. Applying migrations...")
                lead_cols = [
                    ("first_name", "VARCHAR(50)"),
                    ("last_name", "VARCHAR(50)"),
                    ("company", "VARCHAR(100)"),
                    ("mobile", "VARCHAR(20)"),
                    ("lead_source", "VARCHAR(50)"),
                    ("lead_status", "VARCHAR(50) DEFAULT 'New'"),
                    ("company_id", "INTEGER"),
                    ("owner_id", "INTEGER"),
                    ("assigned_to", "INTEGER"),
                    ("created_at", "DATETIME")
                ]
                for col_name, col_type in lead_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name} to leads")
                    except Exception:
                        pass
                connection.commit()

            # 2. Fix Deals Table
            try:
                connection.execute(text("SELECT deal_name FROM deals LIMIT 1"))
            except Exception:
                print("⚠️ Column 'deal_name' not found in deals. Applying migrations...")
                deal_cols = [
                    ("deal_name", "VARCHAR(100)"),
                    ("amount", "FLOAT"),
                    ("stage", "VARCHAR(50)"),
                    ("probability", "INTEGER"),
                    ("owner_id", "INTEGER"),
                    ("company_id", "INTEGER"),
                    ("created_at", "DATETIME"),
                    ("closed_at", "DATETIME"),
                    ("status", "VARCHAR(50)"),
                    ("account_id", "INTEGER"),
                    ("contact_id", "INTEGER")
                ]
                for col_name, col_type in deal_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE deals ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name} to deals")
                    except Exception:
                        pass
                connection.commit()

            # 2.1 Fix Deals Table (Ensure account_id exists for Lead Conversion)
            try:
                connection.execute(text("SELECT account_id FROM deals LIMIT 1"))
            except Exception:
                print("⚠️ Column 'account_id' not found in deals. Adding it...")
                try:
                    connection.execute(text("ALTER TABLE deals ADD COLUMN account_id INTEGER"))
                    connection.execute(text("ALTER TABLE deals ADD COLUMN contact_id INTEGER"))
                    print("✔ Added columns: account_id, contact_id to deals")
                    connection.commit()
                except Exception:
                    pass

            # 3. Fix Leads Table (Drop 'name' column to resolve TypeError/IntegrityError conflict)
            try:
                connection.execute(text("SELECT name FROM leads LIMIT 1"))
                print("⚠️ Column 'name' detected in leads table. Dropping it to match Lead model...")
                connection.execute(text("ALTER TABLE leads DROP COLUMN name"))
                print("✔ Dropped column: name from leads")
            except Exception:
                pass # Column likely doesn't exist, which is correct

            # 4. Fix Deals Table (Drop 'title' column to resolve TypeError/IntegrityError conflict)
            try:
                connection.execute(text("SELECT title FROM deals LIMIT 1"))
                print("ℹ️ Maintenance: Column 'title' detected in deals table. Dropping it to match Deal model...")
                connection.execute(text("ALTER TABLE deals DROP COLUMN title"))
                print("✔ Dropped column: title from deals")
            except Exception:
                pass 

                print("✅ Leads & Deals table migration complete.")
    except Exception as e:
        print(f"CRM Migration Error: {e}")

    # --- Seeding Script ---
    if not models.Plan.query.first():
        print("Seeding database with default plans and features...")
        
        # Create Features
        feat_user = models.Feature(name="User Management", key="user_management")
        feat_logs = models.Feature(name="Activity Logs", key="activity_logs")
        feat_analytics = models.Feature(name="Analytics", key="analytics")
        
        db.session.add_all([feat_user, feat_logs, feat_analytics])
        db.session.commit()
        
        # Create Plans & Link Features
        basic = models.Plan(name="Basic", price="$10/mo", user_limit=5, description="Entry level plan")
        basic.features.append(feat_user)
        
        pro_exec = models.Plan(name="Pro-Executive", price="$50/mo", user_limit=20, description="For growing teams")
        pro_exec.features.extend([feat_user, feat_logs])
        
        executive = models.Plan(name="Executive", price="$100/mo", user_limit=None, description="Full enterprise access")
        executive.features.extend([feat_user, feat_logs, feat_analytics])
        
        db.session.add_all([basic, pro_exec, executive])
        db.session.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    app.run(debug=True)
