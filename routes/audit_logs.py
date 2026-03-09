from flask import Blueprint, request, jsonify
from models.audit_log import AuditLog
from extensions import db

audit_log_bp = Blueprint('audit_logs', __name__)

@audit_log_bp.route("/api/audit-logs", methods=["GET"])
def get_audit_logs():
    module = request.args.get("module")

    query = AuditLog.query

    if module and module != "All":
        query = query.filter(AuditLog.module == module)

    logs = query.order_by(AuditLog.created_at.desc()).all()

    result = []

    for log in logs:
        result.append({
            "id": log.id,
            "date_time": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "user": log.user_name,
            "module": log.module,
            "action": log.action,
            "record": log.record_name,
            "ip_address": log.ip_address
        })

    return jsonify(result)