from flask import Blueprint, request, jsonify
from extensions import db
from models.user import User, LoginHistory
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import random

auth_bp = Blueprint('auth', __name__)

# --- Helper Functions ---

def generate_otp():
    """Generates a 6-digit OTP."""
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp, subject="Your OTP Code"):
    """
    Simulates sending an email. 
    In production, configure SMTP in config.py and use flask-mail or smtplib.
    CHECK YOUR SERVER CONSOLE FOR THE OTP.
    """
    print(f"\n[EMAIL MOCK] To: {email} | Subject: {subject} | Body: Your OTP is {otp}\n")
    # TODO: Implement actual SMTP sending here
    # Example:
    # msg = Message(subject, recipients=[email])
    # msg.body = f"Your OTP is {otp}"
    # mail.send(msg)

# --- Routes ---

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    # Create new user with hashed password
    new_user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        is_verified=False, # User must verify OTP
        role="Super Admin" if User.query.count() == 0 else "Customer" # First user is Super Admin
    )
    
    # Generate OTP
    otp = generate_otp()
    new_user.otp_code = otp
    new_user.otp_expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

    try:
        db.session.add(new_user)
        db.session.commit()
        
        # Send OTP
        send_otp_email(email, otp, "Verify your account")
        
        return jsonify({
            "message": "User registered successfully. Please verify OTP sent to your email.",
            "email": email
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.otp_code == otp:
        if user.otp_expiry and user.otp_expiry > datetime.datetime.utcnow():
            user.is_verified = True
            user.otp_code = None # Clear OTP after use
            user.otp_expiry = None
            user.status = "Active" # Activate user
            db.session.commit()
            return jsonify({"message": "Account verified successfully. You can now login."}), 200
        else:
            return jsonify({"error": "OTP has expired"}), 400
    
    return jsonify({"error": "Invalid OTP"}), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    # Verify credentials
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401

    if not user.is_verified:
        return jsonify({"error": "Account not verified. Please verify OTP first."}), 403
    
    # --- 2FA Logic ---
    otp = generate_otp()
    user.otp_code = otp
    user.otp_expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    db.session.commit()

    send_otp_email(email, otp, "Login OTP")

    return jsonify({
        "message": "Credentials valid. OTP sent to email.",
        "require_otp": True,
        "email": email
    }), 200

@auth_bp.route('/verify-login-otp', methods=['POST'])
def verify_login_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.otp_code == otp and user.otp_expiry and user.otp_expiry > datetime.datetime.utcnow():
        # Clear OTP
        user.otp_code = None
        user.otp_expiry = None
        db.session.commit()

        # Generate Token
        access_token = create_access_token(identity=user.id)
        return jsonify({"message": "Login successful", "token": access_token}), 200

    return jsonify({"error": "Invalid or expired OTP"}), 400