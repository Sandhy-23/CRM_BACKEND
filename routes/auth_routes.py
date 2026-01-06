import jwt
import random
import string
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from flask import request, jsonify, Blueprint, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, ActivityLog
from models.crm import Lead # Assuming Lead is in crm
from models.organization import Organization
from extensions import db
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

# --- Helpers ---

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Bearer token malformed'}), 401
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def log_activity(user_id, action, entity_type=None, entity_id=None):
    """Helper to log activity to the database."""
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging activity: {e}")
        db.session.rollback()

def user_to_dict(user):
    """Safely convert a User object to a dictionary."""
    if not user:
        return None
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'status': user.status,
        'organization_id': user.organization_id,
        'department': user.department,
        'designation': user.designation,
        'created_at': user.created_at.isoformat() if user.created_at else None
    }

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_email(to_email, subject, body):
    """Sends an email using SMTP."""
    # Configuration - Use Environment Variables for Security
    sender_email = os.environ.get("MAIL_USERNAME")
    sender_password = os.environ.get("MAIL_PASSWORD")
    smtp_server = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("MAIL_PORT", 587))

    if not sender_email or not sender_password:
        print(f"⚠️ Email credentials missing in environment variables. Mock email to {to_email}:\n{body}")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- Signup & Login ---

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'message': 'Name, email, and password are required'}), 400

    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User with this email already exists'}), 409

    # Public Signup -> New Company -> Super Admin
    role = 'Super Admin'
    status = 'Active' # Active but needs OTP verification
    
    # Create a new organization for the new Super Admin
    new_org = Organization(name=f"{data.get('name')}'s Company")
    db.session.add(new_org)
    db.session.flush()
    organization_id = new_org.id
    
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    otp = generate_otp()

    new_user = User(
        name=data.get('name'),
        email=data.get('email'),
        password=hashed_password,
        role=role,
        status=status,
        organization_id=organization_id,
        is_verified=False, # Must verify OTP
        otp=otp,
        otp_expiry=datetime.utcnow() + timedelta(minutes=2)
    )
    db.session.add(new_user)
    db.session.commit()

    # Send OTP Email
    send_email(data.get('email'), "Your CRM OTP Code", f"Your OTP code is: {otp}. It expires in 2 minutes.")

    return jsonify({
        'message': 'Signup successful. Please verify the OTP sent to your email.',
        'role': role,
        'email': data.get('email')
    }), 201

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    if not email or not otp:
        return jsonify({'message': 'Email and OTP are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Check if already verified
    if getattr(user, 'is_verified', False):
        return jsonify({'message': 'User already verified'}), 200

    # Verify OTP
    # Note: Using otp_code from model update
    stored_otp = user.otp
    expiry = getattr(user, 'otp_expiry', None)

    if stored_otp != otp:
        return jsonify({'message': 'Invalid OTP'}), 400

    if expiry and datetime.utcnow() > expiry:
        return jsonify({'message': 'OTP has expired'}), 400

    # Success
    user.is_verified = True
    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({'message': 'Email verified successfully. You can now login.'}), 200

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Email and password are required'}), 401

    user = User.query.filter_by(email=data.get('email')).first()

    if not user or not check_password_hash(user.password, data.get('password')):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # Login Rule: Email Verified
    if not getattr(user, 'is_verified', True): # Default True for legacy users
        return jsonify({'message': 'Email not verified. Please verify your OTP.'}), 403

    if user.status != 'Active':
        return jsonify({'message': f'Account is not active. Current status: {user.status}'}), 403

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")

    log_activity(user.id, "User logged in", "User", user.id)
    
    # Determine redirect URL based on role
    base_url = request.host_url.rstrip('/')
    redirect_path = "/user/dashboard"

    if user.role == "Super Admin":
        redirect_path = "/super-admin/dashboard"
    elif user.role == "Admin":
        redirect_path = "/admin/dashboard"
    elif user.role == "HR":
        redirect_path = "/hr/dashboard"

    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role
        },
        'redirect_url': f"{base_url}{redirect_path}"
    })

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'If this email exists, a reset link has been sent.'}), 200

    # Generate Reset Token
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    reset_link = f"{request.host_url.rstrip('/')}/reset-password?token={token}"
    
    # Send Reset Email
    send_email(email, "Password Reset Request", f"Click the link to reset your password: {reset_link}\nThis link expires in 1 hour.")

    return jsonify({'message': 'Password reset link sent to your email.'}), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({'message': 'Token and new password are required'}), 400

    user = User.query.filter_by(reset_token=token).first()
    if not user:
        return jsonify({'message': 'Invalid or expired token'}), 400

    if user.reset_token_expiry and datetime.utcnow() > user.reset_token_expiry:
        return jsonify({'message': 'Token has expired'}), 400

    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()

    return jsonify({'message': 'Password updated successfully. You can now login.'}), 200

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_me(current_user):
    return jsonify(user_to_dict(current_user))

# --- User Management Hierarchy ---

@auth_bp.route('/users', methods=['POST'])
@token_required
def create_user(current_user):
    data = request.get_json()
    required_fields = ['name', 'email', 'password', 'role']
    if not all(field in data for field in required_fields):
        return jsonify({'message': f'Missing required fields: {", ".join(required_fields)}'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User with this email already exists'}), 409

    # Normalize Role Input (Handle "ADMIN", "Admin", "admin")
    requested_role = data.get('role', 'User')
    if requested_role.upper() == 'SUPER ADMIN':
        requested_role = 'Super Admin'
    elif requested_role.upper() == 'ADMIN':
        requested_role = 'Admin'
    elif requested_role.upper() == 'HR':
        requested_role = 'HR'
    elif requested_role.upper() == 'MANAGER':
        requested_role = 'Manager'
    elif requested_role.upper() == 'EMPLOYEE':
        requested_role = 'Employee'

    organization_id = None
    allowed_roles_to_create = []

    if current_user.role == 'Super Admin':
        allowed_roles_to_create = ['Super Admin', 'Admin']
        organization_id = data.get('organization_id')
        # If Super Admin creates an Admin without an Org ID, create a new Organization automatically
        if not organization_id:
            new_org = Organization(name=f"{data.get('name')}'s Organization")
            db.session.add(new_org)
            db.session.flush()
            organization_id = new_org.id
    
    elif current_user.role == 'Admin':
        allowed_roles_to_create = ['HR', 'Manager', 'Employee']
        organization_id = current_user.organization_id

    else:  # HR, Manager, Employee
        return jsonify({'message': 'Permission denied. You are not authorized to create users.'}), 403

    if requested_role not in allowed_roles_to_create:
        return jsonify({'message': f'As a {current_user.role}, you can only create users with roles: {", ".join(allowed_roles_to_create)}'}), 403

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(
        name=data.get('name'),
        email=data.get('email'),
        password=hashed_password,
        role=requested_role,
        organization_id=organization_id,
        department=data.get('department'),
        designation=data.get('designation'),
        status='Active',
        is_verified=True # Admin created users are trusted
    )
    db.session.add(new_user)
    db.session.commit()

    log_activity(current_user.id, f"Created user '{new_user.name}' with role '{new_user.role}'", 'User', new_user.id)
    return jsonify({'message': f'User ({requested_role}) created successfully', 'user': user_to_dict(new_user)}), 201

@auth_bp.route('/users', methods=['GET'])
@token_required
def get_all_users(current_user):
    if current_user.role not in ['Super Admin', 'Admin', 'HR', 'Manager']:
        return jsonify({'message': 'Permission denied'}), 403
    
    query = User.query
    if current_user.role == 'Super Admin':
        pass  # No filter, sees all
    elif current_user.role == 'Admin':
        query = query.filter_by(organization_id=current_user.organization_id)
    elif current_user.role in ['HR', 'Manager']:
        # HR/Manager see users in their own department within the same organization
        if not current_user.department:
             return jsonify([]) # Return empty list if manager has no department
        query = query.filter_by(
            organization_id=current_user.organization_id,
            department=current_user.department
        )
    
    users = query.order_by(User.id).all()
    return jsonify([user_to_dict(u) for u in users])