from models.activity_log import ActivityLog
from extensions import db
from flask import g
from datetime import datetime

def log_activity(module, action, description, related_id=None):
    """
    Logs an activity to the database.
    Relies on g.user_id and g.company_id being set by a before_request handler.
    """
    if not hasattr(g, 'user_id') or not g.user_id:
        print("⚠️ Activity log skipped: user_id not found in Flask g object.")
        return

    try:
        log = ActivityLog(
            module=module,
            action=action,
            description=description,
            related_id=related_id,
            user_id=g.user_id,
            company_id=g.company_id
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Activity log failed: {str(e)}")