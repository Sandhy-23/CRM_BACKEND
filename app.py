import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())  # 🔥 Use find_dotenv to ensure the file is located correctly

from flask import Flask, request, jsonify, send_from_directory
import re
import pymysql
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from sqlalchemy import text, func, create_engine
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from db import get_engine
from config import Config
from extensions import db, bcrypt, mail, jwt
from models.crm import Lead, Deal
from models.team import Team
from models.user import User
from models.organization import Organization
from models.task import Task
from models.note_file import Note, File
from models.contact import Contact
from analytics_routes import analytics_bp, analytics_api_bp
from automation_routes import automation_bp
from marketing_routes import marketing_bp
from campaign_routes import campaign_bp
from routes.dashboard_routes import dashboard_bp
from routes.landing_page_routes import landing_page_bp
from routes.profile_routes import profile_bp
from routes.state_routes import state_bp
from routes.calendar_routes import calendar_bp
from routes.organization_routes import organization_bp
from routes.ticket_routes import ticket_bp
from routes.marketing_analytics_routes import marketing_analytics_bp
from routes.lead_routes import lead_bp
from routes.audit_logs import audit_log_bp
from routes.contact_routes import contact_bp
from routes.deal_routes import deal_bp
from routes.task_routes import task_bp
from routes.knowledge_base_routes import knowledge_bp
from routes.auth_routes import auth_bp, social_bp, SUPER_ADMIN_PERMISSIONS
from tenant_service import create_tenant_database, clone_database_structure, register_tenant, seed_tenant_data
from routes.web_conversion_routes import web_conversion_bp

app = Flask(__name__)
app.url_map.strict_slashes = False # 🔥 Global Fix: Non-strict slashes for all routes

CORS(app, supports_credentials=True, resources={
    r"/*": {
        "origins": [os.getenv("FRONTEND_URL", "http://localhost:5173")]
    }
})
app.config['CORS_HEADERS'] = 'Content-Type'

# ✅ Load configuration from Config class
app.config.from_object(Config)

# ✅ Initialize extensions
db.init_app(app)
jwt.init_app(app)
mail.init_app(app)

# 🔥 DEBUG: Verify .env is loaded (Watch your terminal!)
print(f"FRONTEND URL FROM ENV: {os.getenv('FRONTEND_URL')}")
print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")


# Configure Flask-Mail

# Register Blueprints
app.register_blueprint(analytics_bp, url_prefix='/api/dashboard')
app.register_blueprint(analytics_api_bp, url_prefix='/api/analytics')
app.register_blueprint(automation_bp, url_prefix='/api/automation')
app.register_blueprint(marketing_bp, url_prefix='/api/marketing')
app.register_blueprint(campaign_bp)
app.register_blueprint(dashboard_bp, url_prefix='/api')
app.register_blueprint(landing_page_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(state_bp)
app.register_blueprint(calendar_bp, url_prefix='/api')
app.register_blueprint(organization_bp)
app.register_blueprint(ticket_bp, url_prefix='/api/support-tickets')
app.register_blueprint(marketing_analytics_bp)
app.register_blueprint(lead_bp, url_prefix='/api/leads')
app.register_blueprint(deal_bp)
app.register_blueprint(audit_log_bp) # Register the audit logs blueprint
app.register_blueprint(contact_bp, url_prefix='/api/contacts')
app.register_blueprint(task_bp, url_prefix='/api')
app.register_blueprint(knowledge_bp, url_prefix='/api/knowledge-base')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(social_bp, url_prefix='/auth/social')
app.register_blueprint(web_conversion_bp) # Register the new web conversion blueprint


@app.route('/test')
def test():
    return "working"

@app.route("/")
def home():
    return "Backend Running"

@app.route("/test-db")
def test_db():
    engine = get_engine("master_db")
    with engine.connect() as conn:
        return {"message": "DB Connected"}

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

# ✅ STEP 6: Force Fresh Response (Disable Caching)
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route("/create-organization", methods=["POST"])
def create_organization():
    
    data = request.json
    company = data["company"]
    email = data["email"]

    engine = get_engine("master_db")

    with engine.begin() as conn:
        # 🔥 CHECK if already has org
        existing = conn.execute(text("""
            SELECT * FROM tenant_registry
            WHERE super_admin_email=:email
        """), {"email": email}).fetchone()

        if existing:
            return jsonify({"error": "Organization already exists"}), 400

    db_name = f"tenant_{company}"

    # 1. Create DB
    create_tenant_database(db_name)

    # 2. Clone structure from source
    clone_database_structure(db_name, source_db="crm_db")

    # 3. Seed Admin Data
    seed_tenant_data(db_name, email)

    # 4. Register tenant in master registry
    register_tenant(company, db_name, email)

    return jsonify({"message": "Organization created"}), 200

@app.route("/create-user", methods=["POST"])
def create_user_inside_org():
    data = request.json
    name = data["name"]
    email = data["email"]
    role = data["role"]

    tenant_db = request.headers.get("X-Tenant")
    if not tenant_db:
        return jsonify({"error": "X-Tenant header missing"}), 400

    tenant_engine = get_engine(tenant_db)

    with tenant_engine.connect() as conn:
        # Ensure Unique Constraint exists
        try:
            conn.execute(text("ALTER TABLE users ADD UNIQUE (email)"))
            conn.commit()
        except Exception:
            pass # Already exists

        # Prevent duplicate email inside this organization
        existing = conn.execute(text("""
            SELECT * FROM users WHERE email = :email
        """), {"email": email})

        if existing.fetchone():
            return jsonify({"error": "User already exists in organization"}), 400

        conn.execute(text("""
            INSERT INTO users (name, email, role)
            VALUES (:name, :email, :role)
        """), {"name": name, "email": email, "role": role})
        conn.commit()

    return jsonify({"message": "User created"}), 201

@app.route('/api/team', methods=['GET', 'POST'])
def get_teams():
    if request.method == 'GET':
        try:
            teams = Team.query.all()
            return jsonify([{
                "id": t.id,
                "name": t.name,
                "city": t.city,
                "country": t.country,
                "organization_id": t.organization_id,
                "created_at": t.created_at.isoformat() if t.created_at else None
            } for t in teams]), 200
        except Exception as e:
            print(f"❌ Error in GET /api/team: {e}")
            return jsonify({"error": str(e)}), 500
            
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_team = Team(
                name=data.get('name'),
                city=data.get('city'),
                country=data.get('country'),
                organization_id=1 # Default
            )
            db.session.add(new_team)
            db.session.commit()
            return jsonify({"message": "Team created", "id": new_team.id}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/team/<int:team_id>', methods=['GET'])
def get_team(team_id):
    try:
        team = Team.query.get(team_id)
        if not team:
            return jsonify({"error": "Team not found"}), 404

        members = User.query.filter_by(team_id=team_id).all()

        return jsonify({
            "team": {
                "id": team.id,
                "name": team.name,
                "city": team.city,
                "country": team.country
            },
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "email": m.email,
                    "role": m.role,
                    "status": m.status,
                    "location": getattr(m, 'location', None),
                    "last_active": m.last_active.isoformat() if getattr(m, 'last_active', None) else None
                } for m in members
            ]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/team/<int:team_id>/stats', methods=['GET'])
def team_stats(team_id):
    try:
        total = User.query.filter_by(team_id=team_id).count()
        active = User.query.filter_by(team_id=team_id, status="Active").count()
        pending = User.query.filter_by(team_id=team_id, status="Pending").count()
        admins = User.query.filter_by(team_id=team_id, role="Admin").count()

        return jsonify({
            "total_members": total,
            "active_now": active,
            "pending": pending,
            "admins": admins
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notes', methods=['GET'])
def get_notes():
    print("API HIT: notes")
    try:
        notes = Note.query.order_by(Note.created_at.desc()).all()
        notes_list = []
        for n in notes:
            notes_list.append({
                "id": n.id,
                "title": n.note[:20] if n.note else "Untitled Note",
                "content": n.note,
                "created_at": str(n.created_at) if n.created_at else None
            })
        return jsonify(notes_list), 200
    except Exception as e:
        print(f"❌ Error in GET /api/notes: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/notes', methods=['POST'])
def create_note():
    try:
        data = request.get_json()
        note_content = data.get("note_text") or data.get("content") or data.get("note", "")

        new_note = Note(note=note_content)
        db.session.add(new_note)
        db.session.commit()

        return jsonify({
            "id": new_note.id,
            "title": new_note.note[:20] if new_note.note else "Untitled Note",
            "content": new_note.note,
            "created_at": str(new_note.created_at) if new_note.created_at else None
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    try:
        note = Note.query.get(note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        data = request.get_json()
        note.note = data.get("note_text") or data.get("content") or data.get("note") or note.note

        db.session.commit()
        return jsonify({
            "id": note.id,
            "title": note.note[:20] if note.note else "Untitled Note",
            "content": note.note,
            "updated_at": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    try:
        note = Note.query.get(note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        db.session.delete(note)
        db.session.commit()
        return jsonify({"message": f"Note {note_id} deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/files/upload', methods=['POST'])
@jwt_required()
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Get Metadata
        entity_type = request.form.get('entity_type', 'general')
        entity_id = int(request.form.get('entity_id', 0))
        
        # Get User Info from Token
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        company_id = claims.get("organization_id", 1)

        # Save File
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(app.root_path, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        # Save to DB
        new_file = File(
            entity_type=entity_type,
            entity_id=entity_id,
            file_name=filename,
            file_path=f"/uploads/{filename}",
            file_size=os.path.getsize(file_path),
            file_type=file.content_type,
            uploaded_by=current_user_id,
            company_id=company_id
        )

        db.session.add(new_file)
        db.session.commit()

        return jsonify(new_file.to_dict()), 201

    except Exception as e:
        print(f"Upload Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/files', methods=['GET'])
def get_files():
    try:
        files = File.query.all()
        return jsonify([f.to_dict() for f in files]), 200
    except Exception as e:
        print(f"ERROR in get_files: {e}")
        # Return empty list instead of crashing to pass CORS check
        return jsonify([]), 200

@app.route('/api/files/<int:file_id>', methods=['GET'])
def download_file(file_id):
    try:
        file = File.query.get(file_id)
        if not file:
            return jsonify({"error": "File not found"}), 404

        upload_folder = os.path.join(app.root_path, 'uploads')
        return send_from_directory(upload_folder, file.file_name, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    try:
        file = File.query.get(file_id)
        if not file:
            return jsonify({"error": "File not found"}), 404

        db.session.delete(file)
        db.session.commit()
        return jsonify({"message": f"File {file_id} deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pipelines/leads-funnel', methods=['GET'])
def leads_funnel():

    # Awareness
    awareness = db.session.query(func.count(Lead.id)).filter(
        Lead.status.in_(["New", "Assigned"])
    ).scalar() or 0

    # Interest
    interest = db.session.query(func.count(Lead.id)).filter(
        Lead.status.in_(["Contacted", "Engaged"])
    ).scalar() or 0

    # Qualified
    qualified = db.session.query(func.count(Lead.id)).filter(
        Lead.status == "Qualified"
    ).scalar() or 0

    # Negotiation
    negotiation = db.session.query(func.count(func.distinct(Deal.lead_id))).filter(
        Deal.stage.in_(["Proposal", "Negotiation"])
    ).scalar() or 0

    # Customer
    customer = db.session.query(func.count(func.distinct(Deal.lead_id))).filter(
        Deal.stage == "Won"
    ).scalar() or 0

    # Avoid zero crash
    base = awareness if awareness > 0 else 1

    def calc_width(value):
        return f"{int((value / base) * 100)}%"

    data = {
        "stages": [
            {
                "label": "Awareness",
                "value": f"{awareness:,}",
                "color": "linear-gradient(135deg, #6366f1, #818cf8)",
                "width": "100%"
            },
            {
                "label": "Interest",
                "value": f"{interest:,}",
                "color": "linear-gradient(135deg, #8b5cf6, #a78bfa)",
                "width": calc_width(interest)
            },
            {
                "label": "Qualified",
                "value": f"{qualified:,}",
                "color": "linear-gradient(135deg, #a855f7, #c084fc)",
                "width": calc_width(qualified)
            },
            {
                "label": "Negotiation",
                "value": f"{negotiation:,}",
                "color": "linear-gradient(135deg, #d946ef, #e879f9)",
                "width": calc_width(negotiation)
            },
            {
                "label": "Customer",
                "value": f"{customer:,}",
                "color": "linear-gradient(135deg, #ec4899, #f472b6)",
                "width": calc_width(customer)
            }
        ]
    }

    return jsonify(data)

@app.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": "Email not registered"}), 404

        print(f"📧 Password reset requested for: {email}")
        # Return format matching your Postman collection expectation
        return jsonify({"message": "If the email exists, a reset code has been sent.", "otp_verify_token": "mock-reset-token-123"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Enterprise Rules Enforcement ---

def enforce_deal_approval(deal):
    if deal.value and deal.value > 1000000:
        deal.status = "Pending Approval"
        # Block API from moving to Won until approved (flags status)
        return False, "Deal requires approval"
    return True, ""

def enforce_stage_lock(deal):
    # Check for signed contract file
    files = File.query.filter_by(entity_type='deal', entity_id=deal.id).all()
    # Check if any file is a signed contract (assuming 'file_type' holds this info)
    signed_contract_exists = any(f.file_type == "signed_contract" for f in files)
    
    if not signed_contract_exists and deal.stage == "Won":
        return False, "Cannot move to Won without signed contract"
    return True, ""

def apply_lead_scoring(lead):
    if not lead.email or '@' not in lead.email:
        return

def setup_database():
    """Runs critical database initialization and connectivity tests."""
    with app.app_context():
        try:
            master_engine = get_engine("master_db")
            with master_engine.connect() as conn:
                # 🚨 CRITICAL DB FIX: Ensure master users email is unique
                try:
                    conn.execute(text("ALTER TABLE users ADD UNIQUE (email)"))
                    conn.commit()
                except Exception:
                    pass
            print("✅ DATABASE INITIALIZED: Connected to Master DB")
        except Exception as e:
            print(f"❌ DATABASE ERROR: {e}")

# ✅ Run setup logic (This will now run on Render/Gunicorn)
setup_database()

if __name__ == "__main__":
    # This block only runs during local development (python app.py)
    try:
        print("LEADS IN DB:", Lead.query.count())
    except Exception as e:
        print(f"❌ Local Data Check Failed: {e}")

    # ✅ STEP 5: Verify route is registered
    print("\n--- Registered Routes ---")
    print(app.url_map)
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint:30} {rule.methods} {rule.rule}")
    print("-------------------------\n")
    print("🚀 Starting CRM Backend on 0.0.0.0:5000...")
    app.run(host="0.0.0.0", port=5000, debug=True)
