from flask import request
from extensions import db
from models.audit_log import AuditLog

def create_audit_log(user_name, module, action, record_name):
    try:
        # Attempt to get IP from request, fallback if outside request context
        ip_address = request.remote_addr if request else "System"
    except RuntimeError:
        ip_address = "System"

    log = AuditLog(
        user_name=user_name,
        module=module,
        action=action,
        record_name=record_name,
        ip_address=ip_address
    )

    db.session.add(log)
    db.session.commit()