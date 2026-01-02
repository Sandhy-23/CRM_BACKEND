from flask import Blueprint, jsonify, request
from routes.auth_routes import token_required
from models.user import User, LoginHistory
from models.organization import Organization
from models.crm import Lead, Deal, Activity, Task
from extensions import db
from sqlalchemy import func
from datetime import datetime
from werkzeug.security import generate_password_hash
from models.employee_models import Attendance, ActivityLog

dashboard_bp = Blueprint("dashboard", __name__)

# --- SUPER ADMIN DASHBOARD ---
@dashboard_bp.route("/<org_name>/superadmin/dashboard", methods=["GET"])
@token_required
def super_admin_dashboard(current_user, org_name):
    if current_user.role != "Super Admin":
        return jsonify({"message": f"Unauthorized. You are logged in as '{current_user.role}', but this route requires 'Super Admin'."}), 403
    
    # 1. Global Metrics (Aggregated from DB)
    total_users = User.query.count()
    total_orgs = Organization.query.count()
    
    # 2. Recent System Activity (From LoginHistory table)
    recent_logins = LoginHistory.query.order_by(LoginHistory.login_time.desc()).limit(5).all()
    activity_log = [{
        "user_id": log.user_id,
        "time": log.login_time.isoformat(),
        "ip": log.ip_address,
        "status": log.status
    } for log in recent_logins]

    # 3. All Users List
    # Optimization: Limit to first 50 users to prevent large payload
    all_users = User.query.limit(50).all()
    users_data = [{
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "organization": user.organization.name if user.organization else "N/A",
        "is_approved": user.is_approved
    } for user in all_users]

    return jsonify({
        "role": "Super Admin",
        "metrics": {
            "total_users": total_users,
            "total_organizations": total_orgs
        },
        "recent_activity": activity_log,
        "users": users_data
    })

# --- ADMIN DASHBOARD ---
@dashboard_bp.route("/<org_name>/admin/dashboard", methods=["GET"])
@token_required
def admin_dashboard(current_user, org_name):
    if current_user.role not in ["Admin", "Super Admin"]:
        return jsonify({"message": "Unauthorized"}), 403
    
    # Admin sees users in their Organization (or all if logic dictates, here we show Org view)
    if current_user.organization:
        org_users = User.query.filter_by(organization_id=current_user.organization_id).all()
        org_name_db = current_user.organization.name
    else:
        org_users = []
        org_name_db = "No Organization"

    employees_data = [{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "status": "Active" if u.is_approved else "Pending"
    } for u in org_users]

    return jsonify({
        "role": current_user.role,
        "organization": org_name_db,
        "employee_count": len(org_users),
        "employees": employees_data,
        "message": "Welcome to the Admin Dashboard"
    })

# --- HR DASHBOARD ---
@dashboard_bp.route("/<org_name>/hr/dashboard", methods=["GET"])
@token_required
def hr_dashboard(current_user, org_name):
    if current_user.role not in ["HR", "Admin", "Super Admin"]:
        return jsonify({"message": "Unauthorized"}), 403
    
    # HR sees only users in their own Organization
    if current_user.organization:
        org_users = User.query.filter_by(organization_id=current_user.organization_id).all()
        org_name_db = current_user.organization.name
    else:
        org_users = []
        org_name_db = "No Organization"

    employees_data = [{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "status": "Active" if u.is_approved else "Pending"
    } for u in org_users]

    return jsonify({
        "role": current_user.role,
        "organization": org_name_db,
        "employee_count": len(org_users),
        "employees": employees_data
    })

# --- USER DASHBOARD ---
@dashboard_bp.route("/<org_name>/user/dashboard", methods=["GET"])
@token_required
def user_dashboard(current_user, org_name):
    # 1. My Login History
    my_logs = LoginHistory.query.filter_by(user_id=current_user.id).order_by(LoginHistory.login_time.desc()).limit(5).all()
    logs_data = [{
        "time": log.login_time.isoformat(),
        "ip": log.ip_address,
        "status": log.status
    } for log in my_logs]

    return jsonify({
        "message": f"Welcome back, {current_user.name}",
        "role": current_user.role,
        "profile": {
            "name": current_user.name,
            "email": current_user.email,
            "organization": current_user.organization.name if current_user.organization else "N/A"
        },
        "recent_logins": logs_data
    })

# --- UPDATE PROFILE (Data Storage) ---
@dashboard_bp.route("/<org_name>/user/update-profile", methods=["POST"])
@token_required
def update_profile(current_user, org_name):
    """
    Allows any user to update their name.
    Changes are stored in the 'users' table in crm.db.
    """
    data = request.get_json()
    new_name = data.get("name")

    if new_name:
        current_user.name = new_name
        db.session.commit()
        return jsonify({"message": "Profile updated successfully", "name": current_user.name}), 200
    
    return jsonify({"message": "No changes provided"}), 400

# --- KPI DASHBOARD (Super Admin Only) ---
@dashboard_bp.route("/dashboard/kpis", methods=["GET"])
@token_required
def get_kpis(current_user):
    """
    Returns KPI metrics for the dashboard.
    Query Param: ?period=today|month|year (default: all)
    """
    if current_user.role != "Super Admin":
        return jsonify({"message": "Unauthorized. KPI data is visible only to Super Admin."}), 403

    # 1. Determine Date Range
    period = request.args.get('period', 'all')
    now = datetime.utcnow()
    start_date = None

    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # 2. Base Queries
    leads_query = Lead.query
    deals_query = Deal.query
    activities_query = Activity.query

    if start_date:
        leads_query = leads_query.filter(Lead.created_at >= start_date)
        deals_query = deals_query.filter(Deal.created_at >= start_date)
        activities_query = activities_query.filter(Activity.created_at >= start_date)

    # 3. Calculate Metrics
    total_leads = leads_query.count()
    converted_leads = leads_query.filter_by(status='Converted').count()
    conversion_rate = round((converted_leads / total_leads * 100), 2) if total_leads > 0 else 0

    total_deals = deals_query.count()
    won_deals = deals_query.filter_by(status='Won').count()
    lost_deals = deals_query.filter_by(status='Lost').count()
    
    # Revenue (Sum of value of Won deals)
    revenue = deals_query.filter_by(status='Won').with_entities(func.sum(Deal.value)).scalar() or 0.0

    tasks_completed = activities_query.filter_by(status='Completed').count()

    return jsonify({
        "period": period,
        "leads": {"total": total_leads, "converted": converted_leads, "conversion_rate": conversion_rate},
        "deals": {"total": total_deals, "won": won_deals, "lost": lost_deals, "revenue": revenue},
        "activities": {"tasks_completed": tasks_completed}
    })

# --- EMPLOYEE MANAGEMENT (CRUD) ---

@dashboard_bp.route("/employees", methods=["POST"])
@token_required
def create_employee(current_user):
    """
    Create Employee.
    Allowed roles: Super Admin, Admin, HR.
    """
    if current_user.role not in ["Super Admin", "Admin", "HR"]:
        return jsonify({"message": "Unauthorized. Only Admin/HR can create employees."}), 403

    data = request.get_json()
    email = data.get("email")
    
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists"}), 400

    # Parse Date of Joining
    doj = None
    if data.get("date_of_joining"):
        try:
            doj = datetime.fromisoformat(data.get("date_of_joining").replace("Z", "+00:00"))
        except ValueError:
            pass

    new_user = User(
        name=data.get("name"),
        email=email,
        password=generate_password_hash(data.get("password", "Password@123")), # Default password
        phone=data.get("phone"),
        department=data.get("department"),
        designation=data.get("designation"),
        role=data.get("role", "User"),
        status=data.get("status", "Active"),
        date_of_joining=doj,
        is_approved=True, # Admin created users are auto-approved
        organization_id=current_user.organization_id if current_user.role != "Super Admin" else data.get("organization_id")
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Employee created successfully", "id": new_user.id}), 201

@dashboard_bp.route("/employees", methods=["GET"])
@token_required
def get_employees(current_user):
    """
    View Employee Data.
    Super Admin: All companies.
    Admin / HR: All employees in their company.
    Manager: Team-level employees (Same Department).
    Employee: Only own data.
    """
    query = User.query

    if current_user.role in ["Super Admin", "Admin"]:
        pass # No filter
    elif current_user.role == "HR":
        query = query.filter_by(organization_id=current_user.organization_id)
    elif current_user.role == "Manager":
        # Manager sees employees in their own department within the org
        query = query.filter_by(organization_id=current_user.organization_id, department=current_user.department)
    else:
        # Employee sees only themselves
        query = query.filter_by(id=current_user.id)

    employees = query.all()
    
    result = [{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "phone": u.phone,
        "department": u.department,
        "designation": u.designation,
        "role": u.role,
        "status": u.status,
        "date_of_joining": u.date_of_joining.isoformat() if u.date_of_joining else None,
        "organization_id": u.organization_id
    } for u in employees]

    return jsonify(result), 200

@dashboard_bp.route("/employees/<int:user_id>", methods=["PUT"])
@token_required
def update_employee(current_user, user_id):
    """
    Update Employee.
    Employee: Can update own profile only.
    HR / Admin: Can update any employee in their org.
    Super Admin: Can update anyone.
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Authorization Check
    is_self = (current_user.id == user_id)
    is_admin_hr = (current_user.role in ["Admin", "HR"] and current_user.organization_id == user.organization_id)
    is_super = (current_user.role == "Super Admin")

    if not (is_self or is_admin_hr or is_super): 
        return jsonify({"message": "Unauthorized to update this record"}), 403

    data = request.get_json()

    # Fields anyone can update for themselves (or admins can update)
    if "name" in data: user.name = data["name"]
    if "phone" in data: user.phone = data["phone"]
    
    # Fields only Admins/HR/Super Admin can update
    if is_admin_hr or is_super:
        if "department" in data: user.department = data["department"]
        if "designation" in data: user.designation = data["designation"]
        if "role" in data: user.role = data["role"]
        if "status" in data: user.status = data["status"]
        if "date_of_joining" in data and data["date_of_joining"]:
             user.date_of_joining = datetime.fromisoformat(data["date_of_joining"].replace("Z", "+00:00"))

    db.session.commit()
    return jsonify({"message": "Employee updated successfully"}), 200

@dashboard_bp.route("/employees/<int:user_id>", methods=["DELETE"])
@token_required
def delete_employee(current_user, user_id):
    """
    Delete Employee.
    Allowed roles: Super Admin, Admin, HR.
    """
    if current_user.role not in ["Super Admin", "Admin", "HR"]:
        return jsonify({"message": "Unauthorized. Only Super Admin/Admin/HR can delete employees."}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Prevent deleting users from other organizations (unless Super Admin)
    if current_user.role != "Super Admin" and user.organization_id != current_user.organization_id:
        return jsonify({"message": "Unauthorized to delete user from another organization"}), 403

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Employee deleted successfully"}), 200

# --- ROLE SPECIFIC ENDPOINTS ---

@dashboard_bp.route('/team', methods=['GET'])
@token_required
def get_team_data(current_user):
    """
    Get Team Data.
    Access: HR, Manager
    """
    if current_user.role not in ['HR', 'Manager', 'Admin', 'Super Admin']:
        return jsonify({'message': 'Permission denied'}), 403

    # Fetch users (excluding self)
    team_members = User.query.filter(User.id != current_user.id).all()
    
    data = [{
        'id': member.id,
        'name': member.name,
        'email': member.email,
        'role': member.role,
        'department': getattr(member, 'department', 'N/A')
    } for member in team_members]

    return jsonify({"message": "Team data fetched successfully", "data": data}), 200

@dashboard_bp.route('/attendance', methods=['GET'])
@token_required
def get_attendance(current_user):
    if current_user.role not in ['HR', 'Manager', 'Admin', 'Super Admin']:
        return jsonify({'message': 'Permission denied'}), 403
    
    records = Attendance.query.order_by(Attendance.date.desc()).all()
    data = [{
        'id': r.id,
        'user_id': r.user_id,
        'date': str(r.date),
        'status': r.status,
        'check_in': str(r.check_in) if r.check_in else None
    } for r in records]
    return jsonify({"attendance": data}), 200

@dashboard_bp.route('/activity-logs', methods=['GET'])
@token_required
def get_activity_logs(current_user):
    if current_user.role not in ['HR', 'Manager', 'Admin', 'Super Admin']:
        return jsonify({'message': 'Permission denied'}), 403
        
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(50).all()
    data = [{
        'id': l.id,
        'user_id': l.user_id,
        'action': l.action,
        'timestamp': str(l.timestamp)
    } for l in logs]
    return jsonify({"activity_logs": data}), 200

@dashboard_bp.route('/tasks', methods=['GET'])
@token_required
def get_my_tasks(current_user):
    tasks = Task.query.filter_by(assigned_to=current_user.id).all()
    data = [{'id': t.id, 'title': t.title, 'status': t.status, 'due_date': str(t.due_date) if t.due_date else None} for t in tasks]
    return jsonify({"tasks": data}), 200