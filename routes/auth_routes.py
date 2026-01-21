from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models.user import User, LoginHistory
from models.organization import Organization
from models.otp_verification import OtpVerification
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
    print(f"⚠️ SMTP not configured. OTP for {to_email} was NOT sent via email.")
    print(f"   -> For development, the OTP is contained in the email body: {body}")
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
    db.session.add(verification_entry)
    db.session.commit()
    
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
    record = OtpVerification.query.filter_by(email=email).first()
    
    if not record:
        # UX Improvement: Check if user is already in DB to give better error
        if User.query.filter_by(email=email).first():
             return jsonify({"error": "User already registered. Please use the Login endpoint."}), 400
        return jsonify({"error": "No pending signup found or OTP expired."}), 400

    # 2. Validate OTP and Expiry
    if record.otp != otp:
        return jsonify({"error": "Invalid OTP"}), 400
    
    if datetime.datetime.utcnow() > record.expiry:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"error": "OTP has expired"}), 400

    # 3. Create User in Database
    if User.query.filter_by(email=email).first():
        db.session.delete(record)
        db.session.commit()
        return jsonify({"message": "User already verified. Please login."}), 200

    # Determine Role: First user is SUPER_ADMIN. Subsequent public signups create new orgs.
    role = "SUPER_ADMIN"

    # Create a new Organization for this new user.
    org_name = f"{record.name}'s Organization" if record.name else f"{email.split('@')[0]}'s Org"
    new_org = Organization(
        name=org_name,
        created_by=None # Will be set after user is created
    )
    db.session.add(new_org)
    db.session.flush() # This is needed to get the ID for the user object.

    new_user = User(
        name=record.name,
        email=email,
        password=record.password_hash,
        role=role,
        is_verified=True,
        status="Active",
        organization_id=new_org.id
    )

    try:
        db.session.add(new_user)
        db.session.delete(record) # Remove OTP record
        db.session.commit()
        
        # Now that user exists, link them as the creator of the org
        new_org.created_by = new_user.id
        db.session.commit()

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
    db.session.add(log)
    db.session.commit()

    # 3. Determine Full Redirect URL
    full_url = construct_dashboard_url(user)
    print(f"✅ Login Successful for {user.email}. URL generated: {full_url}")

    # 4. Return the mandatory response
    return jsonify({
        "token": access_token,
        "role": user.role,
        "url": full_url
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
        # Determine Role: Public OAuth is always SUPER_ADMIN (New Organization Owner)
        role = "SUPER_ADMIN"
        
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

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        # Security: Do not reveal if email exists
        return jsonify({"message": "If this email is registered, an OTP has been sent."}), 200
    
    otp = generate_otp()
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    
    # Use OtpVerification table for password reset OTPs as well
    OtpVerification.query.filter_by(email=email).delete()
    reset_token_entry = OtpVerification(
        email=email,
        otp=otp,
        expiry=expiry
    )
    db.session.add(reset_token_entry)
    db.session.commit()
    
    if send_email(email, "Reset Password OTP", f"Your password reset OTP is {otp}"):
        return jsonify({"message": "If this email is registered, an OTP has been sent."}), 200
    else:
        # In a real app, you might not want to expose this failure.
        return jsonify({"error": "Failed to send password reset email."}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not all([email, otp, new_password, confirm_password]):
        return jsonify({"error": "All fields (email, otp, new_password, confirm_password) are required"}), 400

    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Invalid request"}), 400
        
    # Check OtpVerification table for the reset OTP
    record = OtpVerification.query.filter_by(email=email).first()

    if not record:
        return jsonify({"error": "No pending password reset found or OTP expired."}), 400

    if record.otp != otp or datetime.datetime.utcnow() > record.expiry:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"error": "Invalid or expired OTP"}), 400

    # OTP is valid, update the password
    user.password = generate_password_hash(new_password)
    db.session.delete(record) # Clear the used OTP from DB
    db.session.commit()
    
    return jsonify({"message": "Password reset successfully"}), 200