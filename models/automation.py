from extensions import db
from datetime import datetime

class Automation(db.Model):
    __tablename__ = 'automations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    trigger_event = db.Column(db.String(50))   # deal_created | deal_updated
    is_active = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer)         # Multi-tenancy support

    rules = db.relationship('AutomationRule', backref='automation', cascade="all, delete-orphan")
    actions = db.relationship('AutomationAction', backref='automation', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "trigger_event": self.trigger_event,
            "is_active": self.is_active,
            "rules": [r.to_dict() for r in self.rules],
            "actions": [a.to_dict() for a in self.actions]
        }

class AutomationRule(db.Model):
    __tablename__ = 'automation_rules'
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey('automations.id'))
    field = db.Column(db.String(50))           # stage | pipeline
    operator = db.Column(db.String(10))        # equals
    value = db.Column(db.String(50))

    def to_dict(self):
        return {"field": self.field, "operator": self.operator, "value": self.value}

class AutomationAction(db.Model):
    __tablename__ = 'automation_actions'
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey('automations.id'))
    action_type = db.Column(db.String(50))     # update_stage | notify
    action_value = db.Column(db.String(100))

    def to_dict(self):
        return {"action_type": self.action_type, "action_value": self.action_value}

class WorkflowLog(db.Model):
    __tablename__ = 'workflow_logs'
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey('automations.id'))
    deal_id = db.Column(db.Integer)
    status = db.Column(db.String(20))          # success / failed
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)