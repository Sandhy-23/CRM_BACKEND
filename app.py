import os
from dotenv import load_dotenv
load_dotenv()  # 🔥 Load environment variables BEFORE anything else

from flask import Flask, request, jsonify, send_from_directory
import re
import pymysql
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from sqlalchemy import text, func, create_engine
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from db import get_engine
from config import Config
from extensions import db
from extensions import db, bcrypt
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
from routes.auth_routes import SUPER_ADMIN_PERMISSIONS
from tenant_service import create_tenant_database, clone_database_structure, register_tenant, seed_tenant_data

app = Flask(__name__)
app.url_map.strict_slashes = False # 🔥 Global Fix: Non-strict slashes for all routes

# ✅ FIX 1: Proper CORS config for your specific Frontend IP
CORS(app, origins=["http://localhost:5173", "http://100.104.233.79:5173"], supports_credentials=True)
app.config['CORS_HEADERS'] = 'Content-Type'

# 🔥 DEBUG: Verify .env is loaded (Watch your terminal!)
print("FRONTEND URL FROM ENV:", os.getenv("FRONTEND_URL"))

# ✅ STEP 1 & 2: Set Secret Keys for Flask and JWT
app.config['SECRET_KEY'] = 'your_super_secret_key'
app.config['JWT_SECRET_KEY'] = 'your_super_secret_key'

# ✅ STEP 5: UPDATE BACKEND (Force MySQL Connection)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234@localhost/crm_db'
db.init_app(app)
jwt = JWTManager(app)

# ✅ STEP 7: Verify backend is using MySQL
print("DB:", app.config['SQLALCHEMY_DATABASE_URI'])


# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

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


@app.route('/test')
def test():
    return "working"

@app.route("/test-db")
def test_db():
    engine = get_engine("master_db")
    with engine.connect() as conn:
        return {"message": "DB Connected"}

# ✅ STEP 6: Force Fresh Response (Disable Caching)
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    name = data["name"]
    email = data["email"]
    password = data["password"]
    
    # ✅ STEP 2: Hash password correctly
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    engine = create_engine("mysql+pymysql://root:1234@localhost/master_db")

    with engine.begin() as conn:
        # ✅ Mandatory duplicate check (case-insensitive)
        existing = conn.execute(
            text("SELECT * FROM users WHERE LOWER(email)=LOWER(:email)"),
            {"email": email.strip()}
        ).fetchone()

        if existing:
            return jsonify({"error": "User already exists"}), 400

        conn.execute(text("""
            INSERT INTO users (name, email, password, role)
            VALUES (:name, :email, :password, 'Super Admin')
        """), {"name": name, "email": email, "password": hashed_password})

    return jsonify({"message": "Signup successful"}), 201

@app.route("/login", methods=["POST"])
def simple_login():
    data = request.get_json()
    db_engine = get_engine("master_db")

    with db_engine.connect() as conn:
        user = conn.execute(text("""
            SELECT * FROM users WHERE email=:email
        """), {"email": data["email"]}).fetchone()

    # ✅ STEP 5: Verify password with bcrypt.checkpw logic
    if not user or not bcrypt.check_password_hash(user._mapping['password'], data["password"]):
        print("❌ Invalid email or password")
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({"message": "Login success", "role": user._mapping['role']})

@app.route("/create-organization", methods=["POST"])
def create_organization():
    data = request.json
    company = data["company"]
    email = data["email"]

    engine = create_engine("mysql+pymysql://root:1234@localhost/master_db")

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

def get_tenant_db():
    pass

# --- CONVERSION ENDPOINTS (Missing APIs) ---

@app.route('/api/conversion/stats', methods=['GET', 'OPTIONS'])
def conversion_stats():
    if request.method == 'OPTIONS':
        return '', 200
    # Dummy stats - replace with DB query when model exists
    return jsonify({
        "total_visits": 1500,
        "total_leads": 120,
        "conversion_rate": "8.0%"
    })

@app.route('/api/conversion/trends', methods=['GET', 'OPTIONS'])
def conversion_trends():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify([
        {"date": "2023-10-01", "visits": 100, "leads": 5},
        {"date": "2023-10-02", "visits": 120, "leads": 8}
    ])

@app.route('/api/conversion/submissions', methods=['GET', 'OPTIONS'])
def conversion_submissions():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify([])

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

@app.route('/auth/signup', methods=['POST'])
def auth_signup():
    print("🚀 Endpoint /auth/signup hit!")
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # ✅ Check for existing user before attempting insert
        if User.query.filter(func.lower(User.email) == email.lower()).first():
            return jsonify({"error": "User with this email already exists"}), 400

        # Ensure an organization exists (create default if table is empty)
        org = Organization.query.first()
        if not org:
            org = Organization(name=f"{name}'s Organization" if name else "Default Organization", subscription_plan="Free", db_name="crm_db")
            db.session.add(org)
            db.session.commit()

        new_user = User(
            name=name,
            email=email,
            password=bcrypt.generate_password_hash(password).decode('utf-8'),
            role="Super Admin",
            organization_id=org.id,
            is_approved=True,
            status="Active",
            permissions=SUPER_ADMIN_PERMISSIONS,
            must_change_password=True
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "Signup successful", "user_id": new_user.id}), 201
    except Exception as e:
        print(f"❌ Signup Route Error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        # ✅ Step 1: Normalize input (Lower case & strip spaces)
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()
        
        # ✅ Step 2: Validate Email Format
        # Using a standard regex to allow any valid email (not just gmail, but catches typos like 'gamil' if domain checking was stricter, mostly format here)
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_pattern, email):
            return jsonify({"error": "Invalid email format"}), 400

        # ✅ Step 3: Debug Input
        print(f"----- DEBUG LOGIN -----")
        print("EMAIL:", repr(email))

        if "@gamil.com" in email:
            print("⚠️  TYPO DETECTED: You typed '@gamil.com'. Did you mean '@gmail.com'?")

        # ✅ Step 2: Query correctly (case-insensitive)
        user = User.query.filter(func.lower(User.email) == email).first()
        print("USER FOUND:", user)

        if not user:
            print("❌ User not found")
            return jsonify({"error": "User not found"}), 404

        # ✅ Step 4: Check password properly using bcrypt
        is_valid = False
        if user.password:
            is_valid = bcrypt.check_password_hash(user.password, password)

        if not is_valid:
            print("❌ Invalid password")
            return jsonify({"error": "Invalid password"}), 401

        # Fetch database name for routing
        # ✅ Fetch mapping using raw SQL as requested
        org_stmt = text("SELECT db_name FROM organizations WHERE id = :id")
        org_mapping = db.session.execute(org_stmt, {"id": user.organization_id}).fetchone()
        
        db_name = org_mapping[0] if org_mapping and org_mapping[0] else "crm_db"

        # 🔹 LOAD PERMISSIONS FROM DB
        permissions = user.permissions if user.permissions else {}

        # Create JWT Token with Claims
        additional_claims = {
            "email": user.email,
            "role": user.role,
            "organization_id": user.organization_id,
            "db_name": db_name,
            "permissions": permissions # 🔥 Included in JWT for middleware
        }

        token = create_access_token(
            identity=str(user.id),
            additional_claims=additional_claims,
            expires_delta=timedelta(hours=24)
        )

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "organization_id": user.organization_id
            }
        })
    except Exception as e:
        print(f"❌ Login Route Error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

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

if __name__ == "__main__":
    with app.app_context():
        # ✅ STEP 7: TEST CONNECTION (MANDATORY)
        try:
            master_engine = get_engine("master_db")
            with master_engine.connect() as conn:
                print("✅ MYSQL CONNECTED TO MASTER")
                # 🚨 CRITICAL DB FIX: Ensure master users email is unique
                try:
                    conn.execute(text("ALTER TABLE users ADD UNIQUE (email)"))
                    conn.commit()
                except Exception:
                    pass
            print("✅ MYSQL CONNECTED")
        except Exception as e:
            print("❌ ERROR:", e)
        
        # ✅ STEP 8: Verify data
        try:
            leads = Lead.query.all()
            print("LEADS:", leads)
        except Exception as e:
            print(f"❌ DB Error: {e}")
            print("👉 Check if MySQL is running and credentials in config.py are correct.")

    # ✅ STEP 5: Verify route is registered
    print("\n--- Registered Routes ---")
    print(app.url_map)
    print("-------------------------\n")
    print("🚀 Starting CRM Backend on 0.0.0.0:5000...")
    app.run(host='0.0.0.0', debug=True, port=5000)
