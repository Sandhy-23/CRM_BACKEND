from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from extensions import db
from models.user import User, LoginHistory
from models.organization import Organization
import random
import jwt
import datetime

auth_bp = Blueprint("auth", __name__)

# Decorator to verify JWT token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                parts = auth_header.split() # Splits on any whitespace
                if len(parts) > 1:
                    token = parts[1]
                    # Handle double 'Bearer' (common Postman mistake)
                    if token.lower() == 'bearer' and len(parts) > 2:
                        token = parts[2]
                    # Strip quotes (common copy-paste mistake)
                    token = token.strip('"').strip("'")
            else:
                # Fallback: Allow token even if 'Bearer' prefix is missing
                token = auth_header.strip().strip('"').strip("'")
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# ---------------- SIGNUP ----------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON or Content-Type not set to application/json"}), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "User already exists"}), 400

    # Logic: First user is Super Admin and Approved. Others are regular users and must be approved.
    if User.query.count() == 0:
        role = "Super Admin"
        is_approved = True
        # Create default organization for Super Admin
        default_org = Organization.query.filter_by(id=1).first()
        if not default_org:
            default_org = Organization(name="MyCompany")
            db.session.add(default_org)
            db.session.commit()
        org_id = default_org.id
    else:
        # New users are assigned the 'User' role.
        # Auto-approve is set to True to allow immediate login testing as per requirements.
        role = "User"
        is_approved = True
        org_id = 1 # Default to the first organization for public signups.

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role=role,
        is_approved=is_approved,
        organization_id=org_id
    )
    db.session.add(user)
    db.session.commit()
    
    if role == "Super Admin":
        return jsonify({"message": "Signup success. You are the Super Admin and can now login."}), 201
    else:
        return jsonify({"message": "Signup success. You can now login as a User."}), 201


# ---------------- LOGIN ----------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON or Content-Type not set to application/json"}), 400

    email = data.get("email")
    password = data.get("password")
    ip_address = request.remote_addr

    user = User.query.filter(User.email.ilike(email)).first()

    if not user or not check_password_hash(user.password, password):
        # Log failed attempt
        if user:
            log = LoginHistory(user_id=user.id, ip_address=ip_address, status="Failed")
            db.session.add(log)
            db.session.commit()
        return jsonify({"message": "Invalid credentials"}), 401

    # Check Account Status (Active/Inactive)
    if user.status == 'Inactive':
        return jsonify({"message": "Account is Inactive. Please contact HR/Admin."}), 403

    # Check Approval (Legacy check, can be synced with Status if needed)
    if user.role not in ['Super Admin', 'Admin'] and not user.is_approved and user.status == 'Active':
        return jsonify({"message": "Account pending admin approval"}), 403

    # Log success
    log = LoginHistory(user_id=user.id, ip_address=ip_address, status="Success")
    db.session.add(log)
    db.session.commit()

    token = jwt.encode({
        "user_id": user.id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")

    # Ensure token is a string (PyJWT versions < 2.0 return bytes)
    if isinstance(token, bytes):
        token = token.decode("utf-8")

    # Generate Dynamic URL based on Organization and Role
    # Format: http://<domain>/<org_name>/<role_dashboard>
    org_name = user.organization.name.lower().replace(" ", "") if user.organization else "crm"
    
    # Determine dashboard path based on role
    if user.role == "Super Admin":
        dashboard_path = "superadmin"
    elif user.role == "HR":
        dashboard_path = "hr"
    elif user.role == "Admin":
        dashboard_path = "admin"
    else:
        dashboard_path = "user"

    redirect_url = f"http://127.0.0.1:5000/api/{org_name}/{dashboard_path}/dashboard"

    return jsonify({
        "token": token,
        "message": f"Hello {user.name}, Login successful",
        "role": user.role,
        "redirect_url": redirect_url
    }), 200


# ---------------- DASHBOARD (GET ME) ----------------
@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user(current_user):
    return jsonify({
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "organization_id": current_user.organization_id
    })

# ---------------- APPROVE USER (ADMIN ONLY) ----------------
@auth_bp.route("/approve/<int:user_id>", methods=["PUT"])
@token_required
def approve_user(current_user, user_id):
    if current_user.role not in ["Admin", "Super Admin"]:
        return jsonify({"message": "Admin access required"}), 403
    
    user_to_approve = User.query.get(user_id)
    if not user_to_approve:
        return jsonify({"message": "User not found"}), 404
        
    user_to_approve.is_approved = True
    db.session.commit()
    
    return jsonify({"message": f"User {user_to_approve.name} approved"}), 200

# ---------------- LOGIN HISTORY (ADMIN ONLY) ----------------
@auth_bp.route("/login-history/<int:user_id>", methods=["GET"])
@token_required
def get_login_history(current_user, user_id):
    if current_user.role not in ["Admin", "Super Admin"]:
        return jsonify({"message": "Admin access required"}), 403
    
    history = LoginHistory.query.filter_by(user_id=user_id).order_by(LoginHistory.login_time.desc()).all()
    
    history_data = []
    for log in history:
        history_data.append({
            "login_time": log.login_time.isoformat(),
            "ip_address": log.ip_address,
            "status": log.status
        })
        
    return jsonify(history_data), 200

# ---------------- SEND OTP ----------------
@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    email = data.get("email")

    user = User.query.filter(User.email.ilike(email)).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    otp = str(random.randint(100000, 999999))
    user.otp = otp
    db.session.commit()

    # Email logic later (for now print)
    print("OTP:", otp)

    return jsonify({"message": "OTP sent"}), 200


# ---------------- RESET PASSWORD ----------------
@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()

    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("new_password")

    if not email or not otp or not new_password:
        return jsonify({"message": "Email, OTP, and new password required"}), 400

    user = User.query.filter(User.email.ilike(email)).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    if user.otp != otp:
        return jsonify({"message": "Invalid OTP"}), 400

    user.password = generate_password_hash(new_password)
    user.otp = None # Clear OTP after successful reset
    db.session.commit()

    return jsonify({"message": "Password reset successful"}), 200

# ---------------- CHANGE PASSWORD (LOGGED IN) ----------------
@auth_bp.route("/change-password", methods=["POST"])
@token_required
def change_password(current_user):
    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"message": "Old and new passwords required"}), 400

    if not check_password_hash(current_user.password, old_password):
        return jsonify({"message": "Incorrect old password"}), 401

    current_user.password = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"message": "Password changed successfully"}), 200

# ---------------- VERIFY PASSWORD (SECURITY CHECK) ----------------
@auth_bp.route("/verify-password", methods=["POST"])
@token_required
def verify_password(current_user):
    data = request.get_json()
    password = data.get("password")

    if not password:
        return jsonify({"message": "Password required"}), 400

    if check_password_hash(current_user.password, password):
        return jsonify({"message": "Password verified"}), 200
    else:
        return jsonify({"message": "Incorrect password"}), 401

# ---------------- USER MANAGEMENT (RBAC) ----------------

@auth_bp.route("/users", methods=["GET"])
@token_required
def get_all_users(current_user):
    """
    Fetch all users.
    Access: Super Admin, Admin, HR
    """
    if current_user.role in ["Super Admin", "Admin"]:
        users = User.query.all()
    elif current_user.role == "HR":
        users = User.query.filter_by(organization_id=current_user.organization_id).all()
    else:
        return jsonify({"message": "Access denied. Admin or HR role required."}), 403

    users_list = []
    for user in users:
        users_list.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "is_approved": user.is_approved,
            "organization_id": user.organization_id
        })
    
    return jsonify(users_list), 200

@auth_bp.route("/users/<int:user_id>", methods=["GET"])
@token_required
def get_user_detail(current_user, user_id):
    """
    Fetch details of a specific user.
    Access: 
    - Users can view ONLY their own details.
    - Super Admin, Admin, HR can view ANY user's details.
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Access Control Logic
    is_self = (current_user.id == user_id)
    is_global_admin = (current_user.role in ["Super Admin", "Admin"])
    is_org_hr = (current_user.role == "HR" and current_user.organization_id == user.organization_id)

    if not (is_self or is_global_admin or is_org_hr):
        return jsonify({"message": "Access denied. You can only view your own details."}), 403
        
    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "is_approved": user.is_approved,
        "organization_id": user.organization_id
    }), 200

@auth_bp.route("/users/<int:user_id>/role", methods=["PUT"])
@token_required
def update_user_role(current_user, user_id):
    """
    Update a user's role.
    Access: Super Admin, Admin
    """
    if current_user.role not in ["Super Admin", "Admin"]:
        return jsonify({"message": "Access denied. Admin privileges required."}), 403
        
    data = request.get_json()
    new_role = data.get("role")
    
    valid_roles = ["Super Admin", "Admin", "HR", "User"]
    if new_role not in valid_roles:
        return jsonify({"message": f"Invalid role. Choose from {valid_roles}"}), 400
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    user.role = new_role
    db.session.commit()
    
    return jsonify({"message": f"User {user.name} role updated to {new_role}"}), 200
