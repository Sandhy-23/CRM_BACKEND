from flask import Flask, jsonify, g
from flask_cors import CORS
from extensions import db, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from routes import auth_bp, social_bp, website_bp, dashboard_bp, plan_bp, quick_actions_bp, contact_bp, lead_bp, deal_bp, note_file_bp, calendar_bp, activity_bp
from routes.import_export_routes import import_export_bp
from routes.chart_routes import chart_bp
from routes.organization_routes import organization_bp
from routes.analytics_routes import analytics_bp
from routes.pipeline_routes import pipeline_bp
from routes.task_routes import task_bp
from config import Config
import models
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from models.calendar_event import CalendarEvent
from models.reminder import Reminder
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.config.from_object(Config)
print(f"✅ Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True
)

@app.before_request
def load_user_context_from_token():
    """
    Load user context (user_id, company_id, role) from JWT into Flask's g object.
    This runs before every request, making user context globally available.
    """
    try:
        # Use optional=True to not fail on public routes
        verify_jwt_in_request(optional=True)
        claims = get_jwt()
        if claims:
            g.user_id = int(claims.get('sub'))
            g.company_id = claims.get('organization_id')
            g.role = claims.get('role')
        else:
            g.user_id = None
            g.company_id = None
            g.role = None
    except Exception:
        g.user_id = None
        g.company_id = None
        g.role = None

db.init_app(app)
jwt.init_app(app)

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(social_bp, url_prefix="/api/auth")
app.register_blueprint(website_bp) # No prefix for main website
app.register_blueprint(dashboard_bp, url_prefix="/api")
app.register_blueprint(plan_bp, url_prefix="/api")
app.register_blueprint(chart_bp, url_prefix="/api")
app.register_blueprint(quick_actions_bp, url_prefix="/api")
app.register_blueprint(contact_bp)
app.register_blueprint(lead_bp)
app.register_blueprint(deal_bp)
app.register_blueprint(import_export_bp, url_prefix="/api")
app.register_blueprint(note_file_bp)
app.register_blueprint(organization_bp, url_prefix="/api")
app.register_blueprint(analytics_bp)
app.register_blueprint(pipeline_bp, url_prefix="/api")
app.register_blueprint(task_bp)
app.register_blueprint(calendar_bp, url_prefix="/api")
app.register_blueprint(activity_bp, url_prefix="/api")

@app.errorhandler(IntegrityError)
def handle_integrity_error(e):
    db.session.rollback()
    print(f"❌ Database Integrity Error: {e.orig}")
    return jsonify({"error": "Database integrity error", "message": str(e.orig)}), 400

@app.errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify({"error": "Method not allowed", "message": "The method is not allowed for the requested URL."}), 405

# --- Monkey Patch Deal Model (Since models/crm.py is not editable) ---
from models.crm import Deal
if not hasattr(Deal, 'pipeline_id'):
    Deal.pipeline_id = db.Column(db.Integer)
    Deal.stage_id = db.Column(db.Integer)
# ---------------------------------------------------------------------

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
                print("⚠️ Column 'is_verified' not found. Applying migration...")
                # This part is now simplified as other columns are removed from the model
                try:
                    connection.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0"))
                    print("✔ Added column: is_verified")
                    connection.commit()
                except Exception:
                    pass # Column might already exist

            # Check if provider column exists (Social Auth)
            try:
                connection.execute(text("SELECT provider FROM users LIMIT 1"))
            except Exception:
                print("⚠️ Column 'provider' not found. Applying migrations...")
                provider_cols = [
                    ("provider", "VARCHAR(20) DEFAULT 'email'"),
                    ("provider_id", "VARCHAR(100)")
                ]
                for col_name, col_type in provider_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name}")
                    except Exception:
                        pass
                connection.commit()

                print("✅ User table migration complete.")
    except Exception as e:
        print(f"Migration Error: {e}")
    
    # --- Fix Users with NULL Organization ID ---
    try:
        with db.engine.connect() as connection:
            # If users exist with NULL org_id, assign them to the first organization found (Dev Fix)
            connection.execute(text("UPDATE users SET organization_id = (SELECT id FROM organizations LIMIT 1) WHERE organization_id IS NULL"))
            connection.commit()
            # print("✔ Fixed users with missing organization_id")
    except Exception as e:
        print(f"Data Fix Error: {e}")
    # -------------------------------------------

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
                connection.execute(text("SELECT title FROM deals LIMIT 1"))
            except Exception:
                print("⚠️ Column 'title' not found in deals. Applying migrations...")
                deal_cols = [
                    ("title", "VARCHAR(150)"),
                    ("amount", "FLOAT DEFAULT 0"),
                    ("stage", "VARCHAR(50) DEFAULT 'Prospecting'"),
                    ("status", "VARCHAR(20) DEFAULT 'Open'"),
                    ("expected_close_date", "DATE"),
                    ("lead_id", "INTEGER"),
                    ("owner_id", "INTEGER"),
                    ("organization_id", "INTEGER"),
                    ("created_at", "DATETIME"),
                    ("updated_at", "DATETIME")
                ]
                for col_name, col_type in deal_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE deals ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name} to deals")
                    except Exception:
                        pass
                connection.commit()

            # 2.2 Fix Deals Table (Pipelines)
            try:
                connection.execute(text("SELECT pipeline_id FROM deals LIMIT 1"))
            except Exception:
                print("⚠️ Column 'pipeline_id' not found in deals. Adding column...")
                try:
                    connection.execute(text("ALTER TABLE deals ADD COLUMN pipeline_id INTEGER"))
                    print("✔ Added column: pipeline_id to deals")
                    connection.commit()
                except Exception as e:
                    print(f"Error adding pipeline_id column: {e}")

            try:
                connection.execute(text("SELECT stage_id FROM deals LIMIT 1"))
            except Exception:
                print("⚠️ Column 'stage_id' not found in deals. Adding column...")
                try:
                    connection.execute(text("ALTER TABLE deals ADD COLUMN stage_id INTEGER"))
                    print("✔ Added column: stage_id to deals")
                    connection.commit()
                except Exception as e:
                    print(f"Error adding stage_id column: {e}")

            # 2.1 Fix Deals Table (Win/Loss Analytics)
            try:
                connection.execute(text("SELECT outcome FROM deals LIMIT 1"))
            except Exception:
                print("⚠️ Column 'outcome' not found in deals. Applying analytics migrations...")
                analytics_cols = [
                    ("outcome", "VARCHAR(10)"),
                    ("win_reason", "VARCHAR(100)"),
                    ("loss_reason", "VARCHAR(100)"),
                    ("closed_at", "DATETIME")
                ]
                for col_name, col_type in analytics_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE deals ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name} to deals")
                    except Exception:
                        pass
                connection.commit()

            # 5. Fix Contacts Table (New Requirements)
            try:
                connection.execute(text("SELECT first_name FROM contacts LIMIT 1"))
            except Exception:
                print("⚠️ Column 'first_name' not found in contacts. Applying migrations...")
                contact_cols = [
                    ("first_name", "VARCHAR(50)"),
                    ("last_name", "VARCHAR(50)"),
                    ("mobile", "VARCHAR(20)"),
                    ("source", "VARCHAR(50)"),
                    ("owner_id", "INTEGER")
                ]
                for col_name, col_type in contact_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE contacts ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name} to contacts")
                    except Exception:
                        pass
                connection.commit()
            
            # 6. Fix Organizations Table (Setup Flow Requirements)
            try:
                connection.execute(text("SELECT company_size FROM organizations LIMIT 1"))
            except Exception:
                print("⚠️ Column 'company_size' not found in organizations. Applying migrations...")
                org_cols = [
                    ("company_size", "VARCHAR(50)"),
                    ("industry", "VARCHAR(100)"),
                    ("phone", "VARCHAR(20)"),
                    ("country", "VARCHAR(100)"),
                    ("state", "VARCHAR(100)"),
                    ("city_or_branch", "VARCHAR(100)"),
                    ("created_by", "INTEGER"),
                    ("updated_at", "DATETIME")
                ]
                for col_name, col_type in org_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE organizations ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name} to organizations")
                    except Exception:
                        pass
                connection.commit()

            # 7. Fix OTP Verifications Table (New Signup Flow Requirements)
            try:
                connection.execute(text("SELECT created_at FROM otp_verifications LIMIT 1"))
            except Exception:
                print("⚠️ Column 'created_at' not found in otp_verifications. Applying migrations...")
                otp_cols = [
                    ("created_at", "DATETIME"),
                    ("name", "VARCHAR(100)"),
                    ("password_hash", "VARCHAR(200)")
                ]
                for col_name, col_type in otp_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE otp_verifications ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name} to otp_verifications")
                    except Exception:
                        pass
                connection.commit()

            # 8. Fix Activity Logs Table
            try:
                connection.execute(text("SELECT module FROM activity_logs LIMIT 1"))
            except Exception:
                print("⚠️ Column 'module' not found in activity_logs. Applying migrations...")
                log_cols = [
                    ("module", "VARCHAR(50)"),
                    ("description", "TEXT"),
                    ("related_id", "INTEGER"),
                    ("company_id", "INTEGER"),
                    ("created_at", "DATETIME")
                ]
                for col_name, col_type in log_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE activity_logs ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name} to activity_logs")
                    except Exception:
                        # Column might already exist if a previous migration was partial
                        pass
                connection.commit()

            print("✅ Database migration complete.")
    except Exception as e:
        print(f"CRM Migration Error: {e}")

    # --- Auto-Migration for Tasks Table ---
    try:
        with db.engine.connect() as connection:
            # Check for 'company_id' (New Schema)
            try:
                connection.execute(text("SELECT company_id FROM tasks LIMIT 1"))
            except Exception:
                print("⚠️ Column 'company_id' not found in tasks. Applying migrations...")
                task_cols = [
                    ("company_id", "INTEGER"),
                    ("priority", "VARCHAR(20) DEFAULT 'Medium'"),
                    ("lead_id", "INTEGER"),
                    ("deal_id", "INTEGER"),
                    ("updated_at", "DATETIME")
                ]
                for col_name, col_type in task_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}"))
                        print(f"✔ Added column: {col_name} to tasks")
                    except Exception:
                        pass
                
                # Migrate data from old 'organization_id' if it exists
                try:
                    connection.execute(text("UPDATE tasks SET company_id = organization_id WHERE company_id IS NULL"))
                    print("✔ Migrated organization_id to company_id for existing tasks")
                except Exception:
                    pass
                connection.commit()
    except Exception as e:
        print(f"Task Migration Error: {e}")

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
    app.run(host="0.0.0.0", port=5000, debug=True)
