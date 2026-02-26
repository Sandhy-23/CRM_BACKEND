from extensions import db
from datetime import datetime

class AutomationRule(db.Model):
    __tablename__ = "automation_rules"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer)
    organization_id = db.Column(db.Integer)
    status = db.Column(db.String(20))
    name = db.Column(db.String(255))
    trigger_event = db.Column(db.String(100))
    conditions = db.Column(db.Text)   # store JSON string
    actions = db.Column(db.Text)      # store JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)