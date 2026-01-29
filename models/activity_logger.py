from flask import g
from extensions import db
from models.activity_log import ActivityLog


def log_activity(module, action, description, related_id=None):
    """
    Logs an activity to the database.
    Relies on g.user_id and g.company_id from the request context.
    """
    try:
        # Defensive check for context variables
        if not hasattr(g, 'user_id') or not hasattr(g, 'company_id') or g.user_id is None or g.company_id is None:
            print(f"⚠️ Activity log skipped. User/Company context not available in 'g'. Module: {module}, Action: {action}")
            return

        log = ActivityLog(
            module=module, action=action, description=description,
            related_id=related_id, user_id=g.user_id, company_id=g.company_id
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Activity log failed for module '{module}': {str(e)}")