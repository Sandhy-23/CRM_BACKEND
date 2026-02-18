import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, g, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_migrate import Migrate
from extensions import db, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from routes import auth_bp, social_bp, website_bp, dashboard_bp, plan_bp, quick_actions_bp, contact_bp, lead_bp, deal_bp, note_file_bp, calendar_bp, activity_bp, inbox_bp, webhook_bp, channel_bp, message_bp, conversation_bp
from routes.campaign_routes import campaign_bp
from routes.import_export_routes import import_export_bp
from routes.chart_routes import chart_bp
from routes.organization_routes import organization_bp
from routes.analytics_routes import analytics_bp
from routes.pipeline_routes import pipeline_bp
from routes.task_routes import task_bp
from routes.report_routes import report_bp
from routes.team_routes import team_bp
from routes.call_routes import call_bp
from routes.landing_page_routes import landing_page_bp
from routes.marketing_analytics_routes import marketing_analytics_bp
from routes.team_management_routes import team_management_bp
from routes.automation_routes import automation_bp
from drip_routes import drip_bp
from routes.sla_rule_routes import sla_rule_bp
from routes.ticket_routes import ticket_bp
from config import Config
from models.crm import Deal
import models
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from models.calendar_event import CalendarEvent
from models.reminder import Reminder
from dotenv import load_dotenv
from models.team import Team, LocationTeamMapping
from scheduler import process_drip_emails
from services.scheduler_instance import scheduler # Import global scheduler

import models.automation # Register Automation Models
import models.conversation
import models.message
import models.channel_account
import drip_campaign # Register Drip Campaign Models
import models.call # Register Call Model
import models.campaign_log # Register Campaign Log Model
import models.whatsapp_log
import models.landing_page

load_dotenv()


app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)
app.config.from_object(Config)
print("DATABASE URI:", app.config['SQLALCHEMY_DATABASE_URI'])
socketio = SocketIO(app, cors_allowed_origins="*")
print(f"[OK] Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

@app.before_request
def log_request_info():
    """Log incoming JSON requests for debugging."""
    if request.method in ["POST", "PUT", "PATCH"] and request.is_json:
        print(f"[DEBUG] {request.path} Body: {request.get_json(silent=True)}")

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
migrate = Migrate(app, db)

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
app.register_blueprint(automation_bp, url_prefix="/api")
app.register_blueprint(report_bp)
app.register_blueprint(inbox_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(channel_bp)
app.register_blueprint(team_bp)
app.register_blueprint(message_bp)
app.register_blueprint(conversation_bp)
app.register_blueprint(campaign_bp)
app.register_blueprint(drip_bp)
app.register_blueprint(call_bp)
app.register_blueprint(landing_page_bp)
app.register_blueprint(marketing_analytics_bp)
app.register_blueprint(team_management_bp)
app.register_blueprint(sla_rule_bp)
app.register_blueprint(ticket_bp, url_prefix="/api/tickets")

@app.errorhandler(IntegrityError)
def handle_integrity_error(e):
    db.session.rollback()
    print(f"[FAIL] Database Integrity Error: {e.orig}")
    return jsonify({"error": "Database integrity error", "message": str(e.orig)}), 400

@app.errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify({"error": "Method not allowed", "message": "The method is not allowed for the requested URL."}), 405

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found"}), 404

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

with app.app_context():
    # db.drop_all() # Uncomment this ONLY if you need to reset the DB completely
    # db.create_all() # Removed in favor of Flask-Migrate
    
    # --- Auto-Migration for Users Table (Fix for missing columns) ---
    """
    try:
        with db.engine.connect() as connection:
            # Check if is_verified column exists
            try:
                connection.execute(text("SELECT is_verified FROM users LIMIT 1"))
            except Exception:
                print("[WARN] Column 'is_verified' not found. Applying migration...")
                # This part is now simplified as other columns are removed from the model
                try:
                    connection.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0"))
                    print("[OK] Added column: is_verified")
                    connection.commit()
                except Exception:
                    pass # Column might already exist

            # Check if provider column exists (Social Auth)
            try:
                connection.execute(text("SELECT provider FROM users LIMIT 1"))
            except Exception:
                print("[WARN] Column 'provider' not found. Applying migrations...")
                provider_cols = [
                    ("provider", "VARCHAR(20) DEFAULT 'email'"),
                    ("provider_id", "VARCHAR(100)")
                ]
                for col_name, col_type in provider_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                        print(f"[OK] Added column: {col_name}")
                    except Exception:
                        pass
                connection.commit()

            # Check if team_id column exists
            try:
                connection.execute(text("SELECT team_id FROM users LIMIT 1"))
            except Exception:
                print("[WARN] Column 'team_id' not found. Applying migration...")
                try:
                    connection.execute(text("ALTER TABLE users ADD COLUMN team_id INTEGER"))
                    print("[OK] Added column: team_id")
                    connection.commit()
                except Exception as e:
                    print(f"[FAIL] Error adding team_id: {e}")

                print("[OK] User table migration complete.")
            
            # Check if branch_id column exists (Team Management)
            try:
                connection.execute(text("SELECT branch_id FROM users LIMIT 1"))
            except Exception:
                print("[WARN] Column 'branch_id' not found in users. Adding...")
                try:
                    connection.execute(text("ALTER TABLE users ADD COLUMN branch_id INTEGER"))
                    print("[OK] Added column: branch_id")
                    connection.commit()
                except Exception as e:
                    print(f"[FAIL] Error adding branch_id: {e}")

            # Check if last_active column exists (Heartbeat)
            try:
                connection.execute(text("SELECT last_active FROM users LIMIT 1"))
            except Exception:
                print("[WARN] Column 'last_active' not found in users. Adding...")
                try:
                    connection.execute(text("ALTER TABLE users ADD COLUMN last_active DATETIME"))
                    print("[OK] Added column: last_active")
                    connection.commit()
                except Exception as e:
                    print(f"[FAIL] Error adding last_active: {e}")

    except Exception as e:
        print(f"Migration Error: {e}")
    """
    
    # --- Fix Users with NULL Organization ID ---
    """
    try:
        with db.engine.connect() as connection:
            # If users exist with NULL org_id, assign them to the first organization found (Dev Fix)
            connection.execute(text("UPDATE users SET organization_id = (SELECT id FROM organizations LIMIT 1) WHERE organization_id IS NULL"))
            connection.commit()
            # print("✔ Fixed users with missing organization_id")
    except Exception as e:
        print(f"Data Fix Error: {e}")
    """
    # -------------------------------------------

    # --- Auto-Migration for Leads & Deals (Fix for missing columns) ---
    '''
    try:
        with db.engine.connect() as connection:
            # 1. Clean up Leads Table (Drop unwanted columns)
            # Attempt to drop Foreign Key first (MySQL specific)
            try:
                connection.execute(text("ALTER TABLE leads DROP FOREIGN KEY leads_ibfk_1"))
                print("[OK] Dropped FK: leads_ibfk_1 from leads")
            except Exception:
                pass

            cols_to_drop = [
                "company_id", "mobile", 
                "lead_source", "lead_status", "assigned_id", "owner_id",
                "first_name", "last_name", "assigned_to"
            ]
            for col in cols_to_drop:
                try:
                    # Attempt to drop column (Works in SQLite 3.35+ and most SQL DBs)
                    connection.execute(text(f"ALTER TABLE leads DROP COLUMN {col}"))
                    print(f"[OK] Dropped column: {col} from leads")
                except Exception as e:
                    # Ignore if column doesn't exist or DB doesn't support DROP
                    pass
            connection.commit()

            # 2. Add New Columns to Leads Table
            lead_new_cols = [
                ("name", "VARCHAR(100)"),
                ("source", "VARCHAR(50)"),
                ("status", "VARCHAR(50)"),
                ("score", "VARCHAR(20)"),
                ("sla", "VARCHAR(20)"),
                ("owner", "VARCHAR(50)"),
                ("description", "TEXT"),
                ("updated_at", "DATETIME"),
                ("is_deleted", "BOOLEAN DEFAULT 0"),
                ("deleted_at", "DATETIME"),
                ("organization_id", "INTEGER"),
                ("city", "VARCHAR(100)"),
                ("state", "VARCHAR(100)"),
                ("country", "VARCHAR(100)"),
                ("ip_address", "VARCHAR(50)"),
                ("assigned_team_id", "INTEGER"),
                ("assigned_user_id", "INTEGER")
            ]
            for col_name, col_type in lead_new_cols:
                try:
                    connection.execute(text(f"SELECT {col_name} FROM leads LIMIT 1"))
                except Exception:
                    print(f"[WARN] Column '{col_name}' not found in leads. Adding...")
                    try:
                        connection.execute(text(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}"))
                        print(f"[OK] Added column: {col_name}")
                    except Exception as e:
                        print(f"[FAIL] Error adding {col_name}: {e}")
            connection.commit()

            # Check if branch_id column exists in leads (Landing Pages)
            try:
                connection.execute(text("SELECT branch_id FROM leads LIMIT 1"))
            except Exception:
                print("[WARN] Column 'branch_id' not found in leads. Adding...")
                try:
                    connection.execute(text("ALTER TABLE leads ADD COLUMN branch_id INTEGER"))
                    print("[OK] Added column: branch_id to leads")
                    connection.commit()
                except Exception as e:
                    print(f"[FAIL] Error adding branch_id to leads: {e}")

            # 3. Strict Schema Enforcement for Deals Table
            try:
                # Check if table exists and has the correct schema to avoid wiping data
                try:
                    connection.execute(text("SELECT pipeline FROM deals LIMIT 1"))
                except Exception:
                    # If fails (table missing or column missing), recreate it
                    print("[WARN] Enforcing strict schema for 'deals' table...")
                    connection.execute(text("DROP TABLE IF EXISTS deals"))
                    connection.execute(text("""
                        CREATE TABLE deals (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          lead_id INTEGER,
                          title VARCHAR(100) NOT NULL,
                          company VARCHAR(100),
                          pipeline VARCHAR(50) NOT NULL,
                          stage VARCHAR(50) NOT NULL,
                          value INTEGER DEFAULT 0,
                          owner VARCHAR(50),
                          close_date DATE,
                          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                          organization_id INTEGER,
                          win_reason VARCHAR(255),
                          loss_reason VARCHAR(255),
                          closed_at DATETIME
                        )
                    """))
                    connection.commit()
                    print("[OK] Deals table recreated with strict schema.")
            except Exception as e:
                print(f"[FAIL] Deals Migration Error: {e}")

            # 3.1 Ensure organization_id exists in deals (Fix for existing tables)
            try:
                connection.execute(text("SELECT organization_id FROM deals LIMIT 1"))
            except Exception:
                print("[WARN] Column 'organization_id' not found in deals. Adding...")
                try:
                    connection.execute(text("ALTER TABLE deals ADD COLUMN organization_id INTEGER"))
                    print("[OK] Added column: organization_id to deals")
                    connection.commit()
                except Exception as e:
                    print(f"[FAIL] Error adding organization_id to deals: {e}")

            # 4. Deprecated Analytics Columns (Cleanup)
            try:
                connection.execute(text("SELECT outcome FROM deals LIMIT 1"))
            except Exception:
                print("[WARN] Column 'outcome' not found in deals. Applying analytics migrations...")
                analytics_cols = [
                    ("outcome", "VARCHAR(10)"),
                    ("win_reason", "VARCHAR(100)"),
                    ("loss_reason", "VARCHAR(100)"),
                    ("closed_at", "DATETIME")
                ]
                for col_name, col_type in analytics_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE deals ADD COLUMN {col_name} {col_type}"))
                        print(f"[OK] Added column: {col_name} to deals")
                    except Exception:
                        pass
                connection.commit()

            # 5. Fix Contacts Table (New Requirements)
            try:
                connection.execute(text("SELECT first_name FROM contacts LIMIT 1"))
            except Exception:
                print("[WARN] Column 'first_name' not found in contacts. Applying migrations...")
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
                        print(f"[OK] Added column: {col_name} to contacts")
                    except Exception:
                        pass
                connection.commit()

            # 5.1 Strict Schema Enforcement for Contacts (Re-creation)
            try:
                with db.engine.connect() as connection:
                    # Check if migration is needed by looking for an old, removed column
                    try:
                        connection.execute(text("SELECT organization_id FROM contacts LIMIT 1"))
                        needs_migration = True
                    except Exception:
                        needs_migration = False

                    if needs_migration:
                        print("[WARN] Old 'contacts' schema detected. Applying safe migration...")
                        # Step 1: Create new clean table
                        connection.execute(text("""
                            CREATE TABLE contacts_new (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name VARCHAR(100) NOT NULL,
                                company VARCHAR(120),
                                email VARCHAR(120) NOT NULL,
                                phone VARCHAR(20),
                                owner VARCHAR(50),
                                last_contact VARCHAR(50),
                                status VARCHAR(20)
                            )
                        """))
                        print("[OK] Created temporary table 'contacts_new'.")

                        # Step 2: Copy data (only matching columns)
                        connection.execute(text("""
                            INSERT INTO contacts_new (id, name, company, email, phone, owner, last_contact, status)
                            SELECT id, name, company, email, phone, owner, last_contact, status
                            FROM contacts
                        """))
                        print("[OK] Copied data to 'contacts_new'.")

                        # Step 3: Drop old table
                        connection.execute(text("DROP TABLE contacts"))
                        print("[OK] Dropped old 'contacts' table.")

                        # Step 4: Rename new table
                        connection.execute(text("ALTER TABLE contacts_new RENAME TO contacts"))
                        print("[OK] Renamed 'contacts_new' to 'contacts'.")
                        connection.commit()
                        print("[OK] Contacts table migration complete.")
            except Exception as e:
                print(f"[FAIL] Contacts table migration failed: {e}")
            
            # 6. Fix Organizations Table (Setup Flow Requirements)
            try:
                connection.execute(text("SELECT name FROM organizations LIMIT 1"))
            except Exception:
                print("[WARN] Column 'name' not found in organizations. Adding...")
                try:
                    connection.execute(text("ALTER TABLE organizations ADD COLUMN name VARCHAR(100)"))
                    connection.commit()
                    print("[OK] Added column: name")
                except Exception:
                    pass

            try:
                connection.execute(text("SELECT organization_name FROM organizations LIMIT 1"))
            except Exception:
                print("[WARN] Column 'organization_name' not found in organizations. Adding...")
                try:
                    connection.execute(text("ALTER TABLE organizations ADD COLUMN organization_name VARCHAR(100)"))
                    connection.commit()
                    print("[OK] Added column: organization_name")
                except Exception:
                    pass

            try:
                connection.execute(text("SELECT company_size FROM organizations LIMIT 1"))
            except Exception:
                print("[WARN] Column 'company_size' not found in organizations. Applying migrations...")
                org_cols = [
                    ("name", "VARCHAR(100)"),
                    ("organization_name", "VARCHAR(100)"),
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
                        print(f"[OK] Added column: {col_name} to organizations")
                    except Exception:
                        pass
                connection.commit()

            # 7. Fix OTP Verifications Table (New Signup Flow Requirements)
            try:
                connection.execute(text("SELECT created_at FROM otp_verifications LIMIT 1"))
            except Exception:
                print("[WARN] Column 'created_at' not found in otp_verifications. Applying migrations...")
                otp_cols = [
                    ("created_at", "DATETIME"),
                    ("name", "VARCHAR(100)"),
                    ("password_hash", "VARCHAR(200)")
                ]
                for col_name, col_type in otp_cols:
                    try:
                        connection.execute(text(f"ALTER TABLE otp_verifications ADD COLUMN {col_name} {col_type}"))
                        print(f"[OK] Added column: {col_name} to otp_verifications")
                    except Exception:
                        pass
                connection.commit()

            # 8. Fix Activity Logs Table
            try:
                connection.execute(text("SELECT module FROM activity_logs LIMIT 1"))
            except Exception:
                print("[WARN] Column 'module' not found in activity_logs. Applying migrations...")
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
                        print(f"[OK] Added column: {col_name} to activity_logs")
                    except Exception:
                        # Column might already exist if a previous migration was partial
                        pass
                connection.commit()

            # 9. Strict Schema Enforcement for Leads (Enterprise Standard)
            if db.engine.name == 'sqlite':
                print("[INFO] Skipping strict schema enforcement (ALTER TABLE MODIFY not supported in SQLite). Application-layer validation is active.")
            else:
                try:
                    # Applying strict NOT NULL constraints
                    connection.execute(text("""
                        ALTER TABLE leads
                        MODIFY name VARCHAR(100) NOT NULL,
                        MODIFY email VARCHAR(120) NOT NULL,
                        MODIFY company VARCHAR(120) NOT NULL,
                        MODIFY source VARCHAR(50) NOT NULL,
                        MODIFY status VARCHAR(50) NOT NULL,
                        MODIFY score VARCHAR(20) NOT NULL,
                        MODIFY sla VARCHAR(20) NOT NULL,
                        MODIFY owner VARCHAR(50) NOT NULL,
                        MODIFY description TEXT NOT NULL,
                        MODIFY created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        MODIFY updated_at DATETIME,
                        MODIFY is_deleted BOOLEAN DEFAULT 0
                    """))
                    print("[OK] Applied strict NOT NULL constraints to leads table")
                    connection.commit()
                except Exception as e:
                    # This may fail if the DB is SQLite (which doesn't support MODIFY), but works for MySQL
                    print(f"[WARN] Could not apply strict schema constraints (likely SQLite/Syntax): {e}")

            print("[OK] Database migration complete.")
    except Exception as e:
        print(f"CRM Migration Error: {e}")
    '''

    # --- Auto-Migration for Tasks Table ---
    """
    try:
        with db.engine.connect() as connection:
            # Check for 'company_id' (New Schema)
            try:
                connection.execute(text("SELECT company_id FROM tasks LIMIT 1"))
            except Exception:
                print("[WARN] Column 'company_id' not found in tasks. Applying migrations...")
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
                        print(f"[OK] Added column: {col_name} to tasks")
                    except Exception:
                        pass
                
                # Migrate data from old 'organization_id' if it exists
                try:
                    connection.execute(text("UPDATE tasks SET company_id = organization_id WHERE company_id IS NULL"))
                    print("[OK] Migrated organization_id to company_id for existing tasks")
                except Exception:
                    pass
                connection.commit()
    except Exception as e:
        print(f"Task Migration Error: {e}")
    """

    # --- Auto-Migration for Tasks Table (Calendar Support) ---
    """
    try:
        with db.engine.connect() as connection:
            # Check for 'task_date'
            try:
                connection.execute(text("SELECT task_date FROM tasks LIMIT 1"))
            except Exception:
                print("[WARN] Column 'task_date' not found in tasks. Adding...")
                try:
                    connection.execute(text("ALTER TABLE tasks ADD COLUMN task_date DATE"))
                    print("[OK] Added column: task_date")
                except Exception as e:
                    print(f"[FAIL] Error adding task_date: {e}")

            # Check for 'task_time'
            try:
                connection.execute(text("SELECT task_time FROM tasks LIMIT 1"))
            except Exception:
                print("[WARN] Column 'task_time' not found in tasks. Adding...")
                try:
                    connection.execute(text("ALTER TABLE tasks ADD COLUMN task_time VARCHAR(10)"))
                    print("[OK] Added column: task_time")
                except Exception as e:
                    print(f"[FAIL] Error adding task_time: {e}")
            
            # Check for 'source_type' (For Calendar Sync)
            try:
                connection.execute(text("SELECT source_type FROM tasks LIMIT 1"))
            except Exception:
                print("[WARN] Column 'source_type' not found in tasks. Adding...")
                try:
                    connection.execute(text("ALTER TABLE tasks ADD COLUMN source_type VARCHAR(50)"))
                    print("[OK] Added column: source_type")
                except Exception as e:
                    print(f"[FAIL] Error adding source_type: {e}")

            # Check for 'source_id' (For Calendar Sync)
            try:
                connection.execute(text("SELECT source_id FROM tasks LIMIT 1"))
            except Exception:
                print("[WARN] Column 'source_id' not found in tasks. Adding...")
                try:
                    connection.execute(text("ALTER TABLE tasks ADD COLUMN source_id INTEGER"))
                    print("[OK] Added column: source_id")
                except Exception as e:
                    print(f"[FAIL] Error adding source_id: {e}")

            connection.commit()
    except Exception as e:
        print(f"Task Calendar Migration Error: {e}")
    """

    # --- Auto-Migration for Password Resets Table ---
    """
    try:
        with db.engine.connect() as connection:
            # Check for 'reset_token'
            try:
                connection.execute(text("SELECT reset_token FROM password_resets LIMIT 1"))
            except Exception:
                print("[WARN] Column 'reset_token' not found in password_resets. Applying migration...")
                try:
                    connection.execute(text("ALTER TABLE password_resets ADD COLUMN reset_token VARCHAR(100)"))
                    print("[OK] Added column: reset_token to password_resets")
                    connection.commit()
                except Exception as e:
                    print(f"[FAIL] Error adding reset_token column: {e}")
    except Exception as e:
        print(f"Password Reset Migration Error: {e}")
    """

    # --- Auto-Migration for Notes Table (Simplify Schema) ---
    """
    try:
        with db.engine.connect() as connection:
            # Check if old columns exist (e.g., entity_type)
            # We force migration to ensure schema is EXACTLY as requested
            try:
                connection.execute(text("SELECT entity_type FROM notes LIMIT 1"))
                needs_migration = True
            except Exception:
                # Even if entity_type is gone, we check if 'note' column exists. 
                # If not, we migrate.
                try:
                    connection.execute(text("SELECT note FROM notes LIMIT 1"))
                    needs_migration = False
                except:
                    needs_migration = True

            if needs_migration:
                print("[WARN] Enforcing strict schema for 'notes' table...")
                
                # 1. Create new table
                connection.execute(text("CREATE TABLE notes_new (id INTEGER PRIMARY KEY AUTOINCREMENT, note TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
                
                # 2. Copy data (Handle note_text vs note column name from old schema)
                # We try to select 'note' first, if fails (likely 'note_text' in old DB), we map it.
                try:
                    connection.execute(text("INSERT INTO notes_new (id, note, created_at) SELECT id, note, created_at FROM notes"))
                except Exception:
                    connection.execute(text("INSERT INTO notes_new (id, note, created_at) SELECT id, note_text, created_at FROM notes"))
                
                # 3. Drop old and rename
                connection.execute(text("DROP TABLE notes"))
                connection.execute(text("ALTER TABLE notes_new RENAME TO notes"))
                connection.commit()
                print("[OK] Notes table migration complete.")
    except Exception as e:
        print(f"Notes Migration Error: {e}")
    """

    # --- Auto-Migration for Contacts Table (Org Isolation & Soft Delete) ---
    '''
    try:
        with db.engine.connect() as connection:
            contact_new_cols = [
                ("organization_id", "INTEGER"),
                ("is_deleted", "BOOLEAN DEFAULT 0"),
                ("deleted_at", "DATETIME")
            ]
            for col_name, col_type in contact_new_cols:
                try:
                    connection.execute(text(f"ALTER TABLE contacts ADD COLUMN {col_name} {col_type}"))
                    print(f"[OK] Added column: {col_name} to contacts")
                except Exception:
                    pass
            connection.commit()
    except Exception as e:
        print(f"Contacts Migration Error: {e}")
    '''

    # --- Auto-Migration for Automation Tables (New Schema) ---
    '''
    try:
        with db.engine.connect() as connection:
            # Check if 'automation_conditions' table exists (Indicator of New Schema)
            try:
                connection.execute(text("SELECT field FROM automation_conditions LIMIT 1"))
            except Exception:
                print("[WARN] Automation schema mismatch. Recreating automation tables for Professional Structure...")
                # Drop old tables if they exist
                connection.execute(text("DROP TABLE IF EXISTS automation_logs"))
                connection.execute(text("DROP TABLE IF EXISTS automation_actions"))
                connection.execute(text("DROP TABLE IF EXISTS automation_conditions"))
                connection.execute(text("DROP TABLE IF EXISTS automation_rules"))
                connection.execute(text("DROP TABLE IF EXISTS automations"))
                connection.execute(text("DROP TABLE IF EXISTS workflow_logs"))
                
                connection.execute(text("""
                    CREATE TABLE automations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255),
                        trigger_event VARCHAR(100),
                        status VARCHAR(50) DEFAULT 'active',
                        branch_id INTEGER,
                        organization_id INTEGER NOT NULL,
                        created_by INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                connection.execute(text("""
                    CREATE TABLE automation_conditions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        automation_id INTEGER NOT NULL,
                        field VARCHAR(100),
                        operator VARCHAR(50),
                        value VARCHAR(255),
                        FOREIGN KEY(automation_id) REFERENCES automations(id)
                    )
                """))
                connection.execute(text("""
                    CREATE TABLE automation_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        automation_id INTEGER NOT NULL,
                        type VARCHAR(100) NOT NULL,
                        template_id INTEGER,
                        delay_minutes INTEGER DEFAULT 0,
                        FOREIGN KEY(automation_id) REFERENCES automations(id)
                    )
                """))
                connection.execute(text("""
                    CREATE TABLE workflow_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        automation_id INTEGER,
                        deal_id INTEGER,
                        status VARCHAR(20),
                        executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(automation_id) REFERENCES automations(id)
                    )
                """))
                connection.commit()
                print("[OK] Automation tables recreated with Production schema.")
    except Exception as e:
        print(f"Automation Migration Error: {e}")
    '''

    # --- Auto-Migration for Inbox Tables ---
    '''
    try:
        with db.engine.connect() as connection:
            try:
                connection.execute(text("SELECT channel FROM conversations LIMIT 1"))
            except Exception:
                print("[WARN] Inbox tables not found. Creating...")
                # Drop old whatsapp tables if they exist to avoid confusion
                connection.execute(text("DROP TABLE IF EXISTS whatsapp_accounts"))
                connection.execute(text("DROP TABLE IF EXISTS conversations")) # Recreate with new schema
                connection.execute(text("DROP TABLE IF EXISTS messages"))      # Recreate with new schema
                
                connection.execute(text("""
                    CREATE TABLE conversations (
                        id VARCHAR(36) PRIMARY KEY,
                        channel VARCHAR(50) NOT NULL,
                        lead_id INTEGER,
                        assigned_to INTEGER,
                        status VARCHAR(20) DEFAULT 'open',
                        last_message_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        organization_id INTEGER
                    )
                """))
                connection.execute(text("""
                    CREATE TABLE messages (
                        id VARCHAR(36) PRIMARY KEY,
                        conversation_id VARCHAR(36) NOT NULL,
                        channel VARCHAR(50) NOT NULL,
                        sender_type VARCHAR(20),
                        content TEXT,
                        status VARCHAR(20),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                connection.execute(text("""
                    CREATE TABLE channel_accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel VARCHAR(50) NOT NULL,
                        account_name VARCHAR(100),
                        access_token TEXT,
                        credentials JSON,
                        status VARCHAR(20) DEFAULT 'connected',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        organization_id INTEGER
                    )
                """))
                print("[OK] Inbox tables created.")
    except Exception as e:
        print(f"Inbox Migration Error: {e}")
    '''

    # --- Seeding Script ---
    # Note: Seeding requires tables to exist. Run 'flask db upgrade' before starting app.
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
        
    # --- Seeding Teams (For Auto-Assignment Testing) ---
    if not Team.query.first():
        print("Seeding Teams and Location Mappings...")
        # 1. Create Team
        team = Team(name="Hyderabad Sales", city="Hyderabad", country="India")
        db.session.add(team)
        db.session.commit()
        
        # 2. Create Mapping
        mapping = LocationTeamMapping(city="Hyderabad", country="India", team_id=team.id)
        db.session.add(mapping)
        db.session.commit()
        
        # 3. Assign First Agent to Team (if exists)
        agent = models.User.query.filter_by(role='agent').first()
        if agent:
            agent.team_id = team.id
            db.session.commit()
        print("✅ Teams seeded for testing.")

if __name__ == "__main__":
    # --- Background Scheduler for Drip Campaigns ---
    def job_function():
        with app.app_context():
            process_drip_emails()

    # Add Drip Campaign Job
    scheduler.add_job(func=job_function, trigger="interval", minutes=1, id="drip_email_job")
    
    # Start the global scheduler
    scheduler.start()
    print("[OK] Background scheduler started (Campaigns + Drip).")

    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
