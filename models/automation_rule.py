from extensions import db
from datetime import datetime
import json

class AutomationRule(db.Model):
    __tablename__ = "automation_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)

    module = db.Column(db.String(50), nullable=False) # lead, deal, task
    trigger_event = db.Column(db.String(50), nullable=False) # lead_created, deal_updated

    # Stored as JSON strings
    conditions = db.Column(db.Text) 
    actions = db.Column(db.Text, nullable=False)

    is_active = db.Column(db.Boolean, default=True)

    company_id = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "module": self.module,
            "trigger_event": self.trigger_event,
            "conditions": json.loads(self.conditions) if self.conditions else None,
            "actions": json.loads(self.actions) if self.actions else [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }