from flask import Blueprint, jsonify
from extensions import db
from models.user import User, LoginHistory
from sqlalchemy import func
from datetime import datetime, timedelta

chart_bp = Blueprint("charts", __name__)

@chart_bp.route("/charts/user-roles", methods=["GET"])
def user_roles_chart():
    """
    Returns the distribution of users by role.
    Suitable for Pie or Doughnut charts.
    """
    results = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
    
    data = {
        "labels": [r[0] for r in results],
        "datasets": [{
            "label": "User Count by Role",
            "data": [r[1] for r in results]
        }]
    }
    return jsonify(data), 200

@chart_bp.route("/charts/user-status", methods=["GET"])
def user_status_chart():
    """
    Returns the distribution of users by status (Active/Inactive) and Approval.
    Suitable for Bar or Pie charts.
    """
    # Status Distribution
    status_results = db.session.query(User.status, func.count(User.id)).group_by(User.status).all()
    
    # Approval Distribution
    approved_count = User.query.filter_by(is_approved=True).count()
    pending_count = User.query.filter_by(is_approved=False).count()
    
    data = {
        "status_distribution": {
            "labels": [r[0] for r in status_results],
            "data": [r[1] for r in status_results]
        },
        "approval_distribution": {
            "labels": ["Approved", "Pending"],
            "data": [approved_count, pending_count]
        }
    }
    return jsonify(data), 200

@chart_bp.route("/charts/login-activity", methods=["GET"])
def login_activity_chart():
    """
    Returns login attempts over the last 7 days.
    Suitable for Line or Bar charts.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    results = db.session.query(func.date(LoginHistory.login_time), func.count(LoginHistory.id))\
        .filter(LoginHistory.login_time >= start_date)\
        .group_by(func.date(LoginHistory.login_time)).all()
        
    data = {
        "labels": [str(r[0]) for r in results],
        "datasets": [{
            "label": "Login Attempts",
            "data": [r[1] for r in results]
        }]
    }
    return jsonify(data), 200