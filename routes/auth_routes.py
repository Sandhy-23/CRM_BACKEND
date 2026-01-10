from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models.user import User, LoginHistory
from models.organization import Organization
from flask_jwt_extended import create_access_token, verify_jwt_in_request, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import random
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

# --- In-Memory Storage (Replaces DB Storage for OTPs) ---
signup_storage = {} # { email: { 'otp': str, 'name': str, 'password_hash': str, 'expiry': datetime } }
password_reset_storage = {} # { email: { 'otp': str, 'expiry': datetime } }

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

    # 2. No Mock Output (Requested for Security)
    print(f"⚠️ SMTP not configured. OTP to {to_email} was NOT sent.\n   -> MAIL_USERNAME present: {bool(smtp_user)}\n   -> MAIL_PASSWORD present: {bool(smtp_password)}")
    return False

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            current_user = User.query.get(int(user_id))
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# --- Routes ---

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and Password are required"}), 400

    # Default name to email prefix if not provided
    name = data.get('name') or email.split('@')[0]

    # 2. Validate Email Format
    if not validate_email_format(email):
        return jsonify({"error": "Invalid email format"}), 400

    # Check if email already exists in DB
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already registered. Please use the Login endpoint."}), 409

    # --- DIRECT SIGNUP (No OTP) ---
    # Determine Role: First user = Super Admin, others = User (default)
    role = "Super Admin" if User.query.count() == 0 else "User"

    new_user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role=role,
        is_verified=True, # Auto-verify
        status="Active"
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully. You can now login."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    # 1. Check In-Memory Storage
    record = signup_storage.get(email)
    
    if not record:
        # UX Improvement: Check if user is already in DB to give better error
        if User.query.filter_by(email=email).first():
             return jsonify({"error": "User already registered. Please use the Login endpoint."}), 400
        return jsonify({"error": "No pending signup found or OTP expired."}), 400

    # 2. Validate OTP and Expiry
    if record['otp'] != otp:
        return jsonify({"error": "Invalid OTP"}), 400
    
    if datetime.datetime.utcnow() > record['expiry']:
        del signup_storage[email]
        return jsonify({"error": "OTP has expired"}), 400

    # 3. Create User in Database (Final Step)
    # Determine Role: First user = Super Admin, others = User (default)
    role = "Super Admin" if User.query.count() == 0 else "User"

    new_user = User(
        name=record['name'],
        email=email,
        password=record['password_hash'],
        role=role,
        is_verified=True,
        status="Active"
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        
        # Clear memory
        del signup_storage[email]

        return jsonify({"message": "Account verified successfully. You can now login."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    # 1. Verify credentials
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401

    # 1.1 Check if user is verified from signup
    if not user.is_verified:
        return jsonify({"error": "Account not verified. Please complete the signup OTP verification first."}), 403

    # 2. Success - Generate Token & URL directly
    # Generate Token (Include email and role as requested)
    access_token = create_access_token(
        identity=str(user.id), 
        additional_claims={"email": user.email, "role": user.role}
    )
    
    # Log Activity
    log = LoginHistory(user_id=user.id, login_time=datetime.datetime.utcnow(), ip_address=request.remote_addr, status="Success")
    db.session.add(log)
    db.session.commit()

    # 3. Determine Full Redirect URL
    base_url = os.environ.get('FRONTEND_BASE_URL', 'https://rvhcrm.com')
    
    # Sanitize username (lowercase, remove special chars)
    username_slug = re.sub(r'[^a-zA-Z0-9]', '', user.email.lower()) if user.email else "user"

    redirect_url = f"{base_url.rstrip('/')}/{username_slug}/dashboard"

    # 4. Return the mandatory response
    return jsonify({
        "token": access_token,
        "role": user.role,
        "redirect_url": redirect_url
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
        # Determine Role: First user = Super Admin
        role = "Super Admin" if User.query.count() == 0 else "User"
        
        # Create Organization for the user (Requirement: Create or attach company_id)
        # For simplicity, we create a new organization for every new OAuth user 
        # unless logic dictates otherwise.
        new_org = Organization(name=f"{name}'s Organization", subscription_plan="Free")
        db.session.add(new_org)
        db.session.flush() # Get ID
        
        user = User(
            name=name,
            email=email,
            password=generate_password_hash(generate_otp()), # Random password
            role=role,
            is_verified=True,
            status="Active",
            provider=provider,
            provider_id=provider_id,
            organization_id=new_org.id
        )
        db.session.add(user)
        db.session.commit()
        
    # 3. Generate Token
    # Requirement: Token must include user_id, role, company_id
    access_token = create_access_token(
        identity=str(user.id), 
        additional_claims={
            "email": user.email, 
            "role": user.role,
            "company_id": user.organization_id
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
    base_url = os.environ.get('FRONTEND_BASE_URL', 'https://rvhcrm.com')
    username_slug = re.sub(r'[^a-zA-Z0-9]', '', user.email.lower()) if user.email else "user"
    redirect_url = f"{base_url.rstrip('/')}/{username_slug}/dashboard"
    
    return jsonify({
        "message": "Login successful",
        "token": access_token,
        "role": user.role,
        "redirect_url": redirect_url
    }), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        # Security: Do not reveal if email exists
        return jsonify({"message": "If this email is registered, an OTP has been sent."}), 200
    
    otp = generate_otp()
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=2)
    
    # Store OTP in-memory for password reset
    password_reset_storage[email] = {'otp': otp, 'expiry': expiry}
    
    if send_email(email, "Reset Password OTP", f"Your password reset OTP is {otp}"):
        return jsonify({"message": "If this email is registered, an OTP has been sent."}), 200
    else:
        return jsonify({"error": "Failed to send password reset email."}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('new_password')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Invalid request"}), 400
        
    # Check in-memory storage for the reset OTP
    record = password_reset_storage.get(email)

    if not record:
        return jsonify({"error": "No pending password reset found or OTP expired."}), 400

    if record['otp'] == otp and datetime.datetime.utcnow() <= record['expiry']:
        # OTP is valid, update the password
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        # Clear the used OTP from memory
        del password_reset_storage[email]
        
        return jsonify({"message": "Password reset successfully"}), 200
        
    return jsonify({"error": "Invalid or expired OTP"}), 400