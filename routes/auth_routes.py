from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models.user import User, LoginHistory
from models.organization import Organization
from models.otp_verification import OtpVerification
from models.password_reset import PasswordResetToken
from models.pipeline import Pipeline, PipelineStage
from flask_jwt_extended import create_access_token, verify_jwt_in_request, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import random
import secrets
import urllib.parse
from functools import wraps
from sqlalchemy import text
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv, find_dotenv
import requests

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.join(basedir, '.env')
env_typo_path = os.path.join(basedir, '.env.') # Handle potential typo

if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    print(f"✅ Loaded .env from: {env_path}")
elif os.path.exists(env_typo_path):
    load_dotenv(env_typo_path, override=True)
    print(f"⚠️ Loaded .env from typo path: {env_typo_path}. Please rename to .env")
else:
    load_dotenv(find_dotenv(), override=True)

auth_bp = Blueprint('auth', __name__)
social_bp = Blueprint('social_auth', __name__)

# --- Helper Functions ---

def generate_otp():
    """Generates a 6-digit OTP."""
    return str(random.randint(100000, 999999))

def validate_email_format(email):
    """Validates email format using Regex."""
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None

def send_email(to_email, subject, body):
    """
    Sends an email using SMTP if configured, otherwise logs to console.
    """
    # 1. Try Real Email (if env vars are set)
    smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('MAIL_PORT', 587))
    smtp_user = os.environ.get('MAIL_USERNAME')
    smtp_password = os.environ.get('MAIL_PASSWORD')

    if smtp_user and smtp_password:
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            print(f"✅ Email sent to {to_email} via SMTP")
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            if "535" in str(e):
                print(f"💡 HINT: Error 535 means 'Bad Credentials'.")
                print(f"   -> System attempted to login as: '{smtp_user}'")
                print("   1. RESTART your Flask server to load .env changes.")
                print("   2. Check if MAIL_PASSWORD is your 16-char Google App Password (NOT login password).")
                print("   3. Remove spaces from the password in .env.")
            return False

    # 2. Dev Mode Output (Print to Console)
    print(f"⚠️ SMTP not configured. Email to {to_email} was NOT sent via SMTP.")
    print(f"   -> MAIL_USERNAME present: {bool(smtp_user)}")
    print(f"   -> MAIL_PASSWORD present: {bool(smtp_password)}")
    print(f"👇 EMAIL CONTENT (DEV MODE) 👇")
    print(f"Subject: {subject}")
    print(f"{body}")
    print("--------------------------------------------------")
    return False

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            current_user = User.query.get(int(user_id))
            if not current_user:
                print(f"❌ Auth Error: User ID {user_id} not found in database.")
                return jsonify({'message': 'User not found!'}), 401
        except Exception as e:
            print(f"❌ Auth Error: Token verification failed. {str(e)}")
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

def construct_dashboard_url(user):
    """
    Generates the dashboard URL with subdomain based on organization name.
    - Local Dev: http://<org-slug>.<product>.lvh.me:3000/t/home
    - Production: https://<org-slug>.<domain>/t/home
    """
    base_url = os.environ.get('FRONTEND_BASE_URL', 'http://localhost:3000')
    product_name = os.environ.get('PRODUCT_NAME', 'rvhcrm') # e.g., 'rvhcrm'

    parsed = urllib.parse.urlparse(base_url)
    scheme = parsed.scheme or 'http'
    netloc = parsed.netloc # e.g., localhost:3000 or graphy.com

    # Use email username (part before @) as the subdomain
    email_part = user.email.split('@')[0]
    safe_name = email_part.lower().strip()
    safe_name = re.sub(r'\s+', '-', safe_name) # Replace spaces with hyphens
    safe_name = re.sub(r'[^a-z-]', '', safe_name) # Remove special chars and numbers
    safe_name = re.sub(r'-+', '-', safe_name) # Remove duplicate hyphens
    safe_name = safe_name.strip('-')
    org_slug = safe_name or "app"

    # Check if we are in a local development environment
    if 'localhost' in netloc or '127.0.0.1' in netloc:
        # Use lvh.me format for local dev, as it resolves all subdomains to 127.0.0.1
        # e.g., http://my-org.graphy.lvh.me:3000/t/home
        return f"{scheme}://{org_slug}.{product_name}.com/dashboard"
    else:
        # Production format
        # e.g., https://my-org.graphy.com/t/home
        return f"{scheme}://{org_slug}.{netloc}/dashboard"

# --- Routes ---

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({"error": "Email and Password are required"}), 400

    # Default name to email prefix if not provided
    name = data.get('name', '').strip() or email.split('@')[0]

    # 2. Validate Email Format
    if not validate_email_format(email):
        return jsonify({"error": "Invalid email format"}), 400

    # Check if email already exists in DB
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already registered. Please use the Login endpoint."}), 409

    # --- OTP SIGNUP FLOW ---
    otp = generate_otp()
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    
    # Store OTP in DB (Persistence)
    # Remove old OTPs for this email if any
    OtpVerification.query.filter_by(email=email).delete()
    
    verification_entry = OtpVerification(
        email=email,
        otp=otp,
        name=name,
        password_hash=generate_password_hash(password),
        expiry=expiry
    )
    try:
        db.session.add(verification_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB ERROR in signup: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500
    
    # Send OTP (Logs to console if SMTP not set)
    send_email(email, "Signup OTP", f"Your OTP is: {otp}")
    
    return jsonify({"message": "OTP sent successfully"}), 200

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    otp = data.get('otp', '').strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    # 1. Check DB Storage
    print(f"🔍 Verifying OTP for: '{email}'")
    record = OtpVerification.query.filter_by(email=email).first()
    
    if not record:
        # UX Improvement: Check if user is already in DB to give better error
        if User.query.filter_by(email=email).first():
             return jsonify({"error": "User already registered. Please use the Login endpoint."}), 400
        return jsonify({"error": "No pending signup found. Check for typos or sign up again."}), 400

    # 2. Validate OTP and Expiry
    if record.otp != otp:
        return jsonify({"error": "Invalid OTP"}), 400
    
    if datetime.datetime.utcnow() > record.expiry:
        try:
            db.session.delete(record)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"❌ DB ERROR in verify_otp (expiry cleanup): {str(e)}")
        return jsonify({"error": "OTP has expired"}), 400

    # 3. Create User in Database
    if User.query.filter_by(email=email).first():
        try:
            db.session.delete(record)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"❌ DB ERROR in verify_otp (cleanup existing): {str(e)}")
        return jsonify({"message": "User already verified. Please login."}), 200

    # Every new signup is a SUPER_ADMIN with their own organization.
    role = "SUPER_ADMIN"
    org_name = f"{record.name}'s Organization" if record.name else f"{email.split('@')[0]}'s Org"
    new_org = Organization(
        name=org_name,
        created_by=None # Will be set after user is created
    )
    db.session.add(new_org)
    db.session.flush() # This is needed to get the ID for the user object.
    org_id = new_org.id

    new_user = User(
        name=record.name,
        email=email,
        password=record.password_hash,
        role=role,
        is_verified=True,
        status="Active",
        organization_id=org_id
    )

    try:
        db.session.add(new_user)
        db.session.delete(record) # Remove OTP record
        db.session.commit()
        
        # Now that user exists, link them as the creator of the org
        if new_org:
            new_org.created_by = new_user.id
            db.session.commit()

            # --- Auto-Create Default Pipeline ---
            default_pipeline = Pipeline(name="Standard Pipeline", company_id=new_org.id, is_default=True)
            db.session.add(default_pipeline)
            db.session.flush()
            
            stages = ["New", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]
            for idx, s_name in enumerate(stages):
                db.session.add(PipelineStage(pipeline_id=default_pipeline.id, name=s_name, stage_order=idx+1))
            db.session.commit()
        # ------------------------------------

        print(f"✅ User created successfully: {email} (Role: {role})")
        return jsonify({"message": "Signup successful"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Database Error in verify-otp: {e}")
        return jsonify({"error": str(e)}), 500
    

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    user = User.query.filter_by(email=email).first()

    # --- DEBUG START (Requested for troubleshooting) ---
    print(f"--- LOGIN DEBUG ---")
    print(f"LOGIN EMAIL: {email}")
    print(f"DB EMAIL: {user.email if user else 'User Not Found'}")
    print(f"HASH IN DB: {user.password if user else 'N/A'}")
    # --- DEBUG END ---

    # 1. Verify credentials
    if not user:
        print(f"❌ Login Failed: User '{email}' not found in DB.")
        return jsonify({"error": "Invalid email or password"}), 401

    if not check_password_hash(user.password, password):
        print(f"❌ Login Failed: Password mismatch for '{email}'.")
        return jsonify({"error": "Invalid email or password"}), 401

    # 1.1 Check if user is verified from signup
    if not user.is_verified:
        return jsonify({"error": "Account not verified. Please complete the signup OTP verification first."}), 403

    # 2. Success - Generate Token & URL directly
    # Generate Token (Include email and role as requested)
    access_token = create_access_token(
        identity=str(user.id), 
        additional_claims={
            "email": user.email, 
            "role": user.role,
            "organization_id": user.organization_id
        }
    )
    
    # Log Activity
    log = LoginHistory(user_id=user.id, login_time=datetime.datetime.utcnow(), ip_address=request.remote_addr, status="Success")
    try:
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB ERROR in login (history): {str(e)}")
        return jsonify({"error": "Database error logging login", "message": str(e)}), 500

    # 3. Determine Full Redirect URL
    full_url = construct_dashboard_url(user)
    print(f"✅ Login Successful for {user.email}. URL generated: {full_url}")

    # 4. Return the mandatory response
    return jsonify({
        "token": access_token,
        "role": user.role,
        "redirect_url": full_url
    }), 200

@social_bp.route('/google', methods=['POST'])
def google_login():
    data = request.get_json()
    token = data.get('google_token')
    
    if not token:
        return jsonify({"message": "Google token is required"}), 400
        
    # 1. Verify Token with Google
    google_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
    response = requests.get(google_url)
    
    if response.status_code != 200:
        return jsonify({"message": "Invalid Google Token"}), 401
        
    google_data = response.json()
    email = google_data.get('email')
    name = google_data.get('name')
    provider_id = google_data.get('sub')
    
    return handle_oauth_login(email, name, 'google', provider_id)

@social_bp.route('/facebook', methods=['POST'])
def facebook_login():
    data = request.get_json()
    token = data.get('facebook_token')
    
    if not token:
        return jsonify({"message": "Facebook token is required"}), 400
        
    # 1. Verify Token with Facebook
    # Note: Frontend usually sends Access Token
    fb_url = f"https://graph.facebook.com/me?access_token={token}&fields=id,name,email"
    response = requests.get(fb_url)
    
    if response.status_code != 200:
        return jsonify({"message": "Invalid Facebook Token"}), 401
        
    fb_data = response.json()
    email = fb_data.get('email')
    name = fb_data.get('name')
    provider_id = fb_data.get('id')
    
    # Fallback if email is missing (Facebook sometimes doesn't return it)
    if not email:
        email = f"{provider_id}@facebook.com"
        
    return handle_oauth_login(email, name, 'facebook', provider_id)

def handle_oauth_login(email, name, provider, provider_id):
    """Shared logic for OAuth providers"""
    
    try:
        # 1. Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Update provider info if not set
            if not user.provider or user.provider == 'email':
                user.provider = provider
                user.provider_id = provider_id
                db.session.commit()
        else:
            # 2. Create New User
            # --- UNIFIED ROLE & ORG LOGIC ---
            # Every new signup is a SUPER_ADMIN with their own organization.
            role = "SUPER_ADMIN"
            org_name = f"{name}'s Organization" if name else f"{email.split('@')[0]}'s Org"
            new_org = Organization(name=org_name)
            db.session.add(new_org)
            db.session.flush() # Get ID
            org_id = new_org.id
            # --- END UNIFIED LOGIC ---
            
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(generate_otp()), # Random password
                role=role,
                is_verified=True,
                status="Active",
                provider=provider,
                provider_id=provider_id,
                organization_id=org_id
            )
            db.session.add(user)
            db.session.flush() # Get user ID before commit

            # Link user to the new org and create default pipeline if it's the first user
            if new_org:
                new_org.created_by = user.id
                db.session.commit() # Commit to save user and org creator link

                # --- Auto-Create Default Pipeline (Consistent with OTP flow) ---
                default_pipeline = Pipeline(name="Standard Pipeline", company_id=new_org.id, is_default=True)
                db.session.add(default_pipeline)
                db.session.flush()
                
                stages = ["New", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]
                for idx, s_name in enumerate(stages):
                    db.session.add(PipelineStage(pipeline_id=default_pipeline.id, name=s_name, stage_order=idx+1))
                db.session.commit()
            else:
                db.session.commit() # Commit to save user if no org was created

        # 3. Generate Token
        access_token = create_access_token(
            identity=str(user.id), 
            additional_claims={
                "email": user.email, 
                "role": user.role,
                "organization_id": user.organization_id
            }
        )
        
        # 4. Log Activity
        log = LoginHistory(
            user_id=user.id, 
            login_time=datetime.datetime.utcnow(), 
            ip_address=request.remote_addr, 
            status="Success"
        )
        db.session.add(log)
        db.session.commit()
        
        # 5. Generate Redirect URL
        redirect_url = construct_dashboard_url(user)
        
        return jsonify({
            "message": "Login successful",
            "token": access_token,
            "role": user.role,
            "redirect_url": redirect_url
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB ERROR in handle_oauth_login: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    user = User.query.filter_by(email=email).first()
    if not user:
        # Security: Do not reveal if email exists
        return jsonify({"message": "If this email is registered, an OTP has been sent."}), 200
    
    otp = generate_otp()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    
    # Use the new PasswordResetToken table
    PasswordResetToken.query.filter_by(email=email).delete()
    reset_token_entry = PasswordResetToken(
        email=email,
        otp=otp,
        expires_at=expires_at
    )
    try:
        db.session.add(reset_token_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB ERROR in forgot_password: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500
    
    if send_email(email, "Reset Password OTP", f"Your password reset OTP is {otp}"):
        # Create a temporary token that holds the email identity for the next step
        otp_verify_token = create_access_token(identity=email, expires_delta=datetime.timedelta(minutes=10))
        return jsonify({
            "message": "If this email is registered, an OTP has been sent.",
            "otp_verify_token": otp_verify_token
        }), 200
    else:
        # In a real app, you might not want to expose this failure.
        return jsonify({"error": "Failed to send password reset email."}), 500

@auth_bp.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp():
    try:
        verify_jwt_in_request()
        email = get_jwt_identity()
    except Exception as e:
        return jsonify({'message': 'Missing or invalid otp_verify_token', 'error': str(e)}), 401

    data = request.get_json()
    otp = data.get('otp', '').strip()

    if not otp:
        return jsonify({"error": "OTP is required"}), 400

    record = PasswordResetToken.query.filter_by(email=email).first()

    if not record:
        return jsonify({"error": "No pending password reset found for this user."}), 404

    if record.otp != otp:
        return jsonify({"error": "Invalid OTP"}), 400
    
    if datetime.datetime.utcnow() > record.expires_at:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"error": "OTP has expired"}), 400
    
    try:
        reset_token = secrets.token_urlsafe(32)
        record.verified = True
        record.reset_token = reset_token
        # Extend expiry slightly to give user time to enter new password
        record.expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        db.session.commit()

        response = jsonify({"message": "OTP verified successfully"})
        response.set_cookie(
            'reset_token',
            value=reset_token,
            httponly=True,
            secure=request.is_secure,
            samesite='Lax',
            max_age=300 # 5 minutes
        )
        return response
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB ERROR in verify_reset_otp: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    reset_token = request.cookies.get('reset_token')
    if not reset_token:
        return jsonify({"error": "Reset token not found. Please verify your OTP first."}), 401

    data = request.get_json() or {}

    # Handle both snake_case and camelCase from frontend
    new_password = data.get("new_password") or data.get("newPassword")
    confirm_password = data.get("confirm_password") or data.get("confirmPassword")

    if not all([new_password, confirm_password]):
        print(f"❌ Reset Password Failed: Missing password fields. Data received: {list(data.keys())}")
        return jsonify({"error": "All fields (new_password/newPassword, confirm_password/confirmPassword) are required"}), 400

    if new_password != confirm_password:
        print("❌ Reset Password Failed: Passwords do not match.")
        return jsonify({"error": "Passwords do not match"}), 400

    record = PasswordResetToken.query.filter_by(reset_token=reset_token).first()

    if not record:
        return jsonify({"error": "Invalid or expired reset token. Please start over."}), 400

    if not record.verified or datetime.datetime.utcnow() > record.expires_at:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"error": "OTP not verified or session expired. Please start over."}), 400

    user = User.query.filter_by(email=record.email).first()
    if not user:
        print(f"❌ Reset Password Failed: User '{record.email}' not found.")
        return jsonify({"error": "Invalid request"}), 400

    try:
        user.password = generate_password_hash(new_password)
        db.session.delete(record)
        db.session.commit()
        print("✅ Password reset successful.")
        response = jsonify({"message": "Password reset successfully"})
        response.delete_cookie('reset_token')
        return response
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB ERROR in reset_password: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500