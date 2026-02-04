from flask import Blueprint, jsonify, request
from routes.auth_routes import token_required, send_email
from models.user import User, LoginHistory
from models.organization import Organization
from models.crm import Lead, Deal, Activity
from models.task import Task
from extensions import db
from sqlalchemy import func, case, text
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from models.attendance import Attendance
from models.activity_log import ActivityLog
from models.activity_logger import log_activity
from sqlalchemy import extract
import calendar

dashboard_bp = Blueprint("dashboard", __name__)

# --- SUPER ADMIN DASHBOARD ---
@dashboard_bp.route("/<org_name>/superadmin/dashboard", methods=["GET"])
@token_required
def super_admin_dashboard(current_user, org_name):
    if current_user.role != "SUPER_ADMIN":
        return jsonify({"message": f"Unauthorized. You are logged in as '{current_user.role}', but this route requires 'Super Admin'."}), 403
    
    # 1. Global Metrics (Aggregated from DB)
    # Filter by Organization for isolation
    total_users = User.query.filter_by(organization_id=current_user.organization_id).count()
    
    # 2. Recent System Activity (From LoginHistory table)
    recent_logins = LoginHistory.query.join(User).filter(User.organization_id == current_user.organization_id).order_by(LoginHistory.login_time.desc()).limit(5).all()
    activity_log = [{
        "user_id": log.user_id,
        "time": log.login_time.isoformat(),
        "ip": log.ip_address,
        "status": log.status
    } for log in recent_logins]

    # 3. All Users List
    # Optimization: Limit to first 50 users to prevent large payload
    all_users = User.query.filter_by(organization_id=current_user.organization_id).limit(50).all()
    users_data = [{
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "organization": user.organization.name if user.organization else "N/A",
        "is_approved": user.is_approved
    } for user in all_users]

    return jsonify({
        "role": "SUPER_ADMIN",
        "metrics": {
            "total_users": total_users,
            "organization": current_user.organization.name if current_user.organization else "N/A"
        },
        "recent_activity": activity_log,
        "users": users_data
    })

# --- ADMIN DASHBOARD ---
@dashboard_bp.route("/<org_name>/admin/dashboard", methods=["GET"])
@token_required
def admin_dashboard(current_user, org_name):
    if current_user.role not in ["ADMIN", "SUPER_ADMIN"]:
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
    if current_user.role not in ["HR", "ADMIN", "SUPER_ADMIN"]:
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

# --- MANAGER DASHBOARD ---
@dashboard_bp.route("/<org_name>/manager/dashboard", methods=["GET"])
@token_required
def manager_dashboard(current_user, org_name):
    if current_user.role not in ["MANAGER", "ADMIN", "SUPER_ADMIN"]:
        return jsonify({"message": "Unauthorized"}), 403
    
    # Manager sees employees in their own department within the org
    if current_user.organization:
        org_users = User.query.filter_by(
            organization_id=current_user.organization_id, 
            department=current_user.department
        ).all()
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
        try:
            current_user.name = new_name
            db.session.commit()
            return jsonify({"message": "Profile updated successfully", "name": current_user.name}), 200
        except Exception as e:
            db.session.rollback()
            print(f"[FAIL] DB ERROR in update_profile: {str(e)}")
            return jsonify({"error": "Database error", "message": str(e)}), 500
    
    return jsonify({"message": "No changes provided"}), 400

# --- KPI DASHBOARD (Super Admin Only) ---
@dashboard_bp.route("/dashboard/kpis", methods=["GET"])
@token_required
def get_kpis(current_user):
    """
    Returns KPI metrics for the dashboard.
    Query Param: ?period=today|month|year (default: all)
    """
    if current_user.role != "SUPER_ADMIN":
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
        deals_query = deals_query.filter(Deal.created_at >= start_date, Deal.organization_id == current_user.organization_id)
        activities_query = activities_query.filter(Activity.created_at >= start_date, Activity.organization_id == current_user.organization_id)

    # 3. Calculate Metrics
    total_leads = leads_query.count()
    converted_leads = leads_query.filter_by(status='Converted').count()
    conversion_rate = round((converted_leads / total_leads * 100), 2) if total_leads > 0 else 0

    total_deals = deals_query.count()
    won_deals = deals_query.filter_by(stage='Won').count()
    lost_deals = deals_query.filter_by(stage='Lost').count()
    
    # Revenue (Sum of value of Won deals)
    revenue = deals_query.filter(Deal.stage == 'Won').with_entities(func.sum(Deal.value)).scalar() or 0.0

    tasks_completed = activities_query.filter_by(status='Completed').count()

    return jsonify({
        "period": period,
        "leads": {"total": total_leads, "converted": converted_leads, "conversion_rate": conversion_rate},
        "deals": {"total": total_deals, "won": won_deals, "lost": lost_deals, "revenue": revenue},
        "activities": {"tasks_completed": tasks_completed}
    })

# --- EMPLOYEE MANAGEMENT (CRUD) ---

@dashboard_bp.route("/users", methods=["POST"])
@dashboard_bp.route("/employees", methods=["POST"])
@token_required
def create_employee(current_user):
    """
    Create Employee.
    Allowed roles: Super Admin, Admin, HR, Manager.
    """
    if current_user.role not in ["SUPER_ADMIN", "ADMIN", "HR", "MANAGER"]:
        return jsonify({"message": "Unauthorized. Only Super Admin, Admin, HR, or Manager can create users."}), 403

    data = request.get_json()
    email = data.get("email", "").strip().lower()
    
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists"}), 400

    # Parse Date of Joining
    doj = None
    if data.get("date_of_joining"):
        try:
            doj = datetime.fromisoformat(data.get("date_of_joining").replace("Z", "+00:00"))
        except ValueError:
            pass

    # Normalize Role
    role = data.get("role", "USER")
    if role.upper() == 'SUPER ADMIN': role = 'SUPER_ADMIN'
    if role.upper() == 'ADMIN': role = 'ADMIN'
    if role.upper() == 'HR': role = 'HR'
    if role.upper() == 'MANAGER': role = 'MANAGER'
    if role.upper() == 'EMPLOYEE': role = 'EMPLOYEE'

    # Role Hierarchy Check
    role_levels = {"SUPER_ADMIN": 4, "ADMIN": 3, "MANAGER": 2, "HR": 2, "EMPLOYEE": 1, "USER": 1}
    
    creator_level = role_levels.get(current_user.role, 0)
    target_level = role_levels.get(role, 0)

    # Prevent creation of users with equal or higher privileges (except Super Admin)
    if current_user.role != "SUPER_ADMIN" and target_level >= creator_level:
        return jsonify({"message": f"Unauthorized. You cannot create a user with role '{role}'."}), 403

    # Organization Logic
    org_id = current_user.organization_id
    if current_user.role == "SUPER_ADMIN":
        org_id = data.get("organization_id") or current_user.organization_id

    # Auto-verify users created via Dashboard/API (Trusted internal creation)
    is_verified = True

    # Capture raw password for email notification
    raw_password = data.get("password", "Password@123")

    new_user = User(
        name=data.get("name"),
        email=email,
        password=generate_password_hash(raw_password),
        phone=data.get("phone"),
        department=data.get("department"),
        designation=data.get("designation"),
        role=role,
        status=data.get("status", "Active"),
        date_of_joining=doj,
        is_approved=True, # Admin created users are auto-approved
        is_verified=is_verified,
        organization_id=org_id
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        log_activity(
            module="user",
            action="created",
            description=f"User '{new_user.name}' ({new_user.email}) created with role '{new_user.role}'.",
            related_id=new_user.id
        )
    except Exception as e:
        db.session.rollback()
        print(f"[FAIL] DB ERROR in create_employee: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500

    # Email Notification with Credentials
    subject = "Your CRM Login Credentials"
    creator_title = "Super Admin" if current_user.role == "SUPER_ADMIN" else "Administrator"
    
    body = f"""Hello {new_user.name},

Your CRM account has been created by the {creator_title}.

Here are your login details:

Login URL: http://localhost:3000/login
Email: {email}
Password: {raw_password}
Role: {role}

Please change your password after your first login.

Regards,
CRM Team"""

    send_email(email, subject, body)

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

    if current_user.role in ["SUPER_ADMIN", "ADMIN"]:
        pass # No filter
    elif current_user.role == "HR":
        query = query.filter_by(organization_id=current_user.organization_id)
    elif current_user.role == "MANAGER":
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
    is_admin_hr = (current_user.role in ["ADMIN", "HR"] and current_user.organization_id == user.organization_id)
    is_super = (current_user.role == "SUPER_ADMIN")

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

    try:
        db.session.commit()
        log_activity(
            module="user",
            action="updated",
            description=f"User '{user.name}' (ID: {user.id}) profile was updated.",
            related_id=user.id
        )
        return jsonify({"message": "Employee updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"[FAIL] DB ERROR in update_employee: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500

@dashboard_bp.route("/employees/<int:user_id>", methods=["DELETE"])
@token_required
def delete_employee(current_user, user_id):
    """
    Delete Employee.
    Allowed roles: Super Admin, Admin, HR.
    """
    if current_user.role not in ["SUPER_ADMIN", "ADMIN", "HR"]:
        return jsonify({"message": "Unauthorized. Only Super Admin/Admin/HR can delete employees."}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Prevent deleting users from other organizations (unless Super Admin)
    if current_user.role != "SUPER_ADMIN" and user.organization_id != current_user.organization_id:
        return jsonify({"message": "Unauthorized to delete user from another organization"}), 403

    try:
        db.session.delete(user)
        db.session.commit()
        log_activity(
            module="user",
            action="deleted",
            description=f"User '{user.name}' (ID: {user.id}) was deleted.",
            related_id=user.id
        )
        return jsonify({"message": "Employee deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"[FAIL] DB ERROR in delete_employee: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500

# --- ROLE SPECIFIC ENDPOINTS ---

@dashboard_bp.route('/team', methods=['GET'])
@token_required
def get_team_data(current_user):
    """
    Get Team Data.
    Access: HR, Manager
    """
    if current_user.role not in ['HR', 'MANAGER', 'ADMIN', 'SUPER_ADMIN']:
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
    if current_user.role not in ['HR', 'MANAGER', 'ADMIN', 'SUPER_ADMIN']:
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
    if current_user.role not in ['HR', 'MANAGER', 'ADMIN', 'SUPER_ADMIN']:
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

@dashboard_bp.route('/dashboard/login-activity', methods=['GET'])
@token_required
def dashboard_login_activity(current_user):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({"error": "Unauthorized"}), 403
        
    # Last 7 days login counts
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    logs = db.session.query(
        func.date(LoginHistory.login_time).label('date'), 
        func.count(LoginHistory.id)
    ).filter(
        LoginHistory.login_time >= seven_days_ago
    ).group_by(func.date(LoginHistory.login_time)).all()
    
    data = {str(day): count for day, count in logs}
    return jsonify(data)

@dashboard_bp.route('/dashboard/task-stats', methods=['GET'])
@token_required
def dashboard_task_stats(current_user):
    query = db.session.query(Task.status, func.count(Task.id)).group_by(Task.status)
    
    # If not admin, only see own tasks
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN', 'HR']:
        query = query.filter(Task.assigned_to == current_user.id)
    elif current_user.role in ['ADMIN', 'HR']:
        # Filter by organization if applicable
        if current_user.organization_id:
            query = query.filter(Task.company_id == current_user.organization_id)
        
    stats = query.all()
    return jsonify({status: count for status, count in stats})

# --- CRM DASHBOARD WIDGETS ---

@dashboard_bp.route('/dashboard/leads-summary', methods=['GET'])
@token_required
def leads_summary(current_user):
    # Reuse the RBAC logic from lead_routes if possible, or replicate simple filter
    query = Lead.query
    if current_user.role != 'SUPER_ADMIN':
        pass
        
    total = query.count()
    today = datetime.utcnow().date()
    new_today = query.filter(func.date(Lead.created_at) == today).count()
    converted = query.filter_by(status='Converted').count()
    
    return jsonify({
        "total_leads": total,
        "new_today": new_today,
        "converted": converted
    })

@dashboard_bp.route('/dashboard/deals-pipeline', methods=['GET'])
@token_required
def deals_pipeline(current_user):
    query = Deal.query
    # RBAC is simplified for now as per instructions
    # Group by Stage
    results = db.session.query(Deal.stage, func.count(Deal.id)).filter(Deal.id.in_([d.id for d in query.with_entities(Deal.id).all()])).group_by(Deal.stage).all()
    return jsonify({r[0]: r[1] for r in results})

# --- NEW DASHBOARD ANALYTICS ENDPOINTS (Final JSON Target) ---

@dashboard_bp.route('/dashboard/summary', methods=['GET'])
@token_required
def dashboard_summary(current_user):
    """
    Returns dashboard summary metrics as per specific frontend requirements.
    """
    # 1. Total Leads
    total_leads = Lead.query.count()

    # 2. Active Deals (Not Won or Lost)
    # Matches: SELECT COUNT(*) FROM deals WHERE status = 'Active' (mapped to stages)
    active_deals = Deal.query.filter(
        func.lower(Deal.stage).notin_(['won', 'closed won', 'lost', 'closed lost'])
    ).count()

    # 3. Revenue (This Quarter)
    # Matches: SELECT SUM(amount) ... WHERE QUARTER(closed_at) = QUARTER(CURDATE())
    today = datetime.utcnow().date()
    current_quarter = (today.month - 1) // 3 + 1
    quarter_start_month = (current_quarter - 1) * 3 + 1
    quarter_start_date = today.replace(month=quarter_start_month, day=1)
    
    # Calculate start of next quarter to define the upper bound
    if quarter_start_month + 3 > 12:
        next_q_start = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_q_start = today.replace(month=quarter_start_month + 3, day=1)

    revenue = db.session.query(func.sum(Deal.value)).filter(
        func.lower(Deal.stage).in_(['won', 'closed won']),
        Deal.close_date >= quarter_start_date,
        Deal.close_date < next_q_start
    ).scalar() or 0

    # 4. Tasks Due (Today or Future)
    tasks_due = Task.query.filter(
        Task.status != 'Completed',
        Task.due_date >= today
    ).count()

    # 5. Overdue Tasks (Past)
    overdue_tasks = Task.query.filter(
        Task.status != 'Completed',
        Task.due_date < today
    ).count()

    result = {
        "total_leads": total_leads,
        "active_deals": active_deals,
        "revenue": int(revenue),
        "tasks_due": tasks_due,
        "overdue_tasks": overdue_tasks
    }

    print(f"[DEBUG] Dashboard summary result: {result}")
    return jsonify(result)

@dashboard_bp.route('/dashboard/win-loss', methods=['GET'])
@token_required
def dashboard_win_loss(current_user):
    won = Deal.query.filter_by(stage='Won').count()
    lost = Deal.query.filter_by(stage='Lost').count()
    in_progress = Deal.query.filter(Deal.stage.notin_(['Won', 'Lost'])).count()

    return jsonify({
        "won": won,
        "lost": lost,
        "in_progress": in_progress
    })

@dashboard_bp.route('/dashboard/win-reasons', methods=['GET'])
@token_required
def dashboard_win_reasons(current_user):
    # Group by win_reason string
    results = db.session.query(Deal.win_reason, func.count(Deal.id))\
        .filter(Deal.stage == 'Won', Deal.win_reason.isnot(None), Deal.win_reason != "")\
        .group_by(Deal.win_reason).all()
    
    return jsonify([{"label": r[0], "value": r[1]} for r in results])

@dashboard_bp.route('/dashboard/loss-reasons', methods=['GET'])
@token_required
def dashboard_loss_reasons(current_user):
    # Group by loss_reason string
    results = db.session.query(Deal.loss_reason, func.count(Deal.id))\
        .filter(Deal.stage == 'Lost', Deal.loss_reason.isnot(None), Deal.loss_reason != "")\
        .group_by(Deal.loss_reason).all()
    
    return jsonify([{"label": r[0], "value": r[1]} for r in results])

@dashboard_bp.route('/dashboard/forecast', methods=['GET'])
@token_required
def dashboard_forecast(current_user):
    today = datetime.utcnow().date()
    current_month = today.month
    current_year = today.year

    # 1. Total Pipeline (Value of Open Deals)
    total_pipeline = db.session.query(func.sum(Deal.value)).filter(Deal.stage.notin_(['Won', 'Lost'])).scalar() or 0

    # 2. Closing This Month (Open deals with close_date in current month)
    # Note: SQLite extract syntax might differ, but SQLAlchemy usually handles it.
    # For SQLite, we might need to filter by date range if extract fails, but let's try standard SA first.
    closing_deals_query = Deal.query.filter(
        Deal.stage.notin_(['Won', 'Lost']),
        extract('month', Deal.close_date) == current_month,
        extract('year', Deal.close_date) == current_year
    )
    
    closing_this_month = closing_deals_query.count()
    
    # 3. Expected Revenue (Sum of value of deals closing this month)
    # In a real CRM, this would be weighted by probability. Here we sum the value.
    expected_revenue = db.session.query(func.sum(Deal.value)).filter(
        Deal.stage.notin_(['Won', 'Lost']),
        extract('month', Deal.close_date) == current_month,
        extract('year', Deal.close_date) == current_year
    ).scalar() or 0

    return jsonify({
        "total_pipeline": int(total_pipeline),
        "closing_this_month": closing_this_month,
        "expected_revenue": int(expected_revenue)
    })

# --- NEW DASHBOARD WIDGETS (Final JSON Target) ---

@dashboard_bp.route('/dashboard/summary-widgets', methods=['GET'])
@token_required
def get_dashboard_summary_widget(current_user):
    # 1. Total Leads
    total_leads = Lead.query.count()
    
    # 2. Lead Growth (This Month vs Last Month)
    today = datetime.utcnow()
    first_day_this_month = today.replace(day=1)
    last_month_end = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_month_end.replace(day=1)
    
    leads_this_month = Lead.query.filter(Lead.created_at >= first_day_this_month).count()
    leads_last_month = Lead.query.filter(Lead.created_at >= first_day_last_month, Lead.created_at <= last_month_end).count()
    
    lead_growth = 0
    if leads_last_month > 0:
        lead_growth = round(((leads_this_month - leads_last_month) / leads_last_month) * 100)
    
    # 3. Active Deals (Not Won/Lost)
    active_deals = Deal.query.filter(func.lower(Deal.stage).notin_(['won', 'closed won', 'lost', 'closed lost'])).count()
    
    # 4. In-progress Deals (Same as active for now, or specific stages like Negotiation)
    in_progress_deals = Deal.query.filter(Deal.stage.in_(['Negotiation', 'Proposal'])).count()
    
    # 5. Quarter Revenue (Sum of Won deals in current quarter)
    current_quarter = (today.month - 1) // 3 + 1
    quarter_start_month = (current_quarter - 1) * 3 + 1
    quarter_start_date = today.replace(month=quarter_start_month, day=1)
    
    quarter_revenue = db.session.query(func.sum(Deal.value)).filter(
        func.lower(Deal.stage).in_(['won', 'closed won']),
        Deal.created_at >= quarter_start_date # Using created_at as proxy for close_date if close_date is string/null
    ).scalar() or 0
    
    # 6. Tasks Due (Pending tasks due today or in future)
    tasks_due = Task.query.filter(Task.status != 'Completed', Task.due_date >= today.date()).count()
    # For overdue, we need to check due_date < today. 
    # Assuming due_date is stored as string YYYY-MM-DD or Date object.
    # If string, comparison might be tricky in SQL directly without cast, doing python side check for safety or simple string compare if format ISO.
    # Let's assume standard ISO string or Date type.
    tasks_overdue = Task.query.filter(Task.status != 'Completed', Task.due_date < today.date()).count()

    return jsonify({
        "total_leads": total_leads,
        "lead_growth": lead_growth,
        "active_deals": active_deals,
        "in_progress_deals": in_progress_deals,
        "quarter_revenue": int(quarter_revenue),
        "tasks_due": tasks_due,
        "tasks_overdue": tasks_overdue
    })

@dashboard_bp.route('/dashboard/revenue-growth', methods=['GET'])
@token_required
def get_revenue_growth(current_user):
    # Revenue Growth Chart
    # Matches: SELECT MONTHNAME(closed_at), SUM(amount) ... GROUP BY MONTH(closed_at)
    results = db.session.query(
        func.strftime('%m', Deal.close_date).label('month_num'),
        func.sum(Deal.value)
    ).filter(
        func.lower(Deal.stage).in_(['won', 'closed won']),
        Deal.close_date.isnot(None)
    ).group_by('month_num').order_by('month_num').all()
    
    data = []
    for r in results:
        # Map month number '01' to 'Jan'
        month_idx = int(r[0])
        month_name = calendar.month_abbr[month_idx]
        data.append({"month": month_name, "revenue": int(r[1])})
        
    return jsonify(data)

@dashboard_bp.route('/dashboard/today-tasks', methods=['GET'])
@token_required
def get_today_tasks(current_user):
    """
    Returns tasks for the current day using the specific task_date and task_time columns.
    """
    # Handle SQLite vs MySQL date function difference
    if 'sqlite' in db.engine.name:
        date_func = "DATE('now')"
    else:
        date_func = "CURDATE()"
        
    sql = text(f"""
        SELECT id, title, task_time 
        FROM tasks 
        WHERE task_date = {date_func} 
        AND company_id = :company_id
        ORDER BY task_time ASC
    """)
    
    try:
        results = db.session.execute(sql, {'company_id': current_user.organization_id}).fetchall()
        data = []
        for row in results:
            # row is (id, title, task_time)
            # Ensure time is formatted as HH:MM (truncate seconds if present)
            t_str = str(row[2])[:5] if row[2] else "09:00"
            data.append({"time": t_str, "title": row[1]})
            
        return jsonify(data)
    except Exception as e:
        print(f"[FAIL] Get Today Tasks Error: {e}")
        return jsonify([])