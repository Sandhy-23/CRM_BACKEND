from datetime import datetime
from extensions import db

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100))
    module = db.Column(db.String(100))
    action = db.Column(db.String(50))
    record_name = db.Column(db.String(255))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)