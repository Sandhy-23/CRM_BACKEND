import jwt
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

# --- Signup & Login ---

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'message': 'Name, email, and password are required'}), 400

    # Enforce Super Admin creation only for the first user
    # Check if users table is empty (First User Logic)
    user_count = User.query.count()
    if user_count > 0:
        return jsonify({'message': 'Public registration is disabled. Users must be created by an administrator.'}), 403

    # First user becomes Super Admin in a new organization
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    
    # Create a default organization for the Super Admin
    new_org = Organization(name=f"{data.get('name')}'s Company")
    db.session.add(new_org)
    db.session.flush()  # Flush to get the new_org.id

    new_user = User(
        name=data.get('name'),
        email=data.get('email'),
        password=hashed_password,
        role='Super Admin',
        status='Active',
        organization_id=new_org.id
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Super Admin created successfully', 'role': 'Super Admin'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Email and password are required'}), 401

    user = User.query.filter_by(email=data.get('email')).first()

    if not user or not check_password_hash(user.password, data.get('password')):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    if user.status != 'Active':
        return jsonify({'message': f'Account is not active. Current status: {user.status}'}), 403

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")

    log_activity(user.id, "User logged in", "User", user.id)
    
    # Determine redirect URL based on role
    redirect_url = "/user/dashboard"
    if user.role == "Super Admin":
        redirect_url = "/super-admin/dashboard"
    elif user.role == "Admin":
        redirect_url = "/admin/dashboard"
    elif user.role == "HR":
        redirect_url = "/hr/dashboard"

    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role
        },
        'redirect_url': redirect_url
    })

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

    requested_role = data.get('role')
    organization_id = None
    allowed_roles_to_create = []

    if current_user.role == 'Super Admin':
        allowed_roles_to_create = ['Admin']
        organization_id = data.get('organization_id')
        if not organization_id:
            return jsonify({'message': 'organization_id is required to create an Admin'}), 400
        if not Organization.query.get(organization_id):
            return jsonify({'message': 'Organization not found'}), 404
    
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
        status='Active'
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