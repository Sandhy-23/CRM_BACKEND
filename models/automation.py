from extensions import db
from datetime import datetime
import json

class AutomationRule(db.Model):
    __tablename__ = 'automation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    module = db.Column(db.String(50), nullable=False)  # lead / deal
    trigger_event = db.Column(db.String(50), nullable=False) # lead_created
    priority = db.Column(db.Integer, default=1)
    stop_on_match = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    conditions = db.relationship('AutomationCondition', backref='rule', cascade="all, delete-orphan")
    actions = db.relationship('AutomationAction', backref='rule', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "module": self.module,
            "trigger_event": self.trigger_event,
            "priority": self.priority,
            "stop_on_match": self.stop_on_match,
            "is_active": self.is_active,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions]
        }

class AutomationCondition(db.Model):
    __tablename__ = 'automation_conditions'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id'), nullable=False)
    field_name = db.Column(db.String(50), nullable=False)
    operator = db.Column(db.String(20), nullable=False) # equals, contains
    value = db.Column(db.String(255), nullable=False)
    logical_join = db.Column(db.String(10), default='AND')

    def to_dict(self):
        return {"field_name": self.field_name, "operator": self.operator, "value": self.value, "logical_join": self.logical_join}

class AutomationAction(db.Model):
    __tablename__ = 'automation_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False) # assign_owner, create_task
    action_order = db.Column(db.Integer, default=1)
    config_json = db.Column(db.Text, nullable=False) # Stored as JSON string

    def to_dict(self):
        return {"action_type": self.action_type, "config": json.loads(self.config_json)}

class AutomationLog(db.Model):
    __tablename__ = 'automation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id'))
    module = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    status = db.Column(db.String(20)) # success / failed
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "module": self.module,
            "record_id": self.record_id,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at.isoformat()
        }