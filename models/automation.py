from extensions import db
from datetime import datetime

class Automation(db.Model):
    __tablename__ = 'automations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    trigger_event = db.Column(db.String(100), nullable=False)   # deal_created | deal_updated
    status = db.Column(db.String(50), default='active') # active | paused
    branch_id = db.Column(db.Integer, nullable=False)
    organization_id = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    conditions = db.relationship('AutomationCondition', backref='automation', cascade="all, delete-orphan")
    actions = db.relationship('AutomationAction', backref='automation', cascade="all, delete-orphan")
    logs = db.relationship('WorkflowLog', backref='automation', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "trigger_event": self.trigger_event,
            "status": self.status,
            "branch_id": self.branch_id,
            "organization_id": self.organization_id,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions]
        }

class AutomationCondition(db.Model):
    __tablename__ = 'automation_conditions'
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey('automations.id'), nullable=False)
    field = db.Column(db.String(100), nullable=False)           # stage | pipeline
    operator = db.Column(db.String(50), nullable=False)        # equals
    value = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {"field": self.field, "operator": self.operator, "value": self.value}

class AutomationAction(db.Model):
    __tablename__ = 'automation_actions'
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey('automations.id'), nullable=False)
    type = db.Column(db.String(100), nullable=False)     # update_stage | notify
    template_id = db.Column(db.Integer, nullable=True)
    delay_minutes = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "type": self.type, 
            "template_id": self.template_id, 
            "delay_minutes": self.delay_minutes
        }

class WorkflowLog(db.Model):
    __tablename__ = 'workflow_logs'
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey('automations.id'))
    deal_id = db.Column(db.Integer)
    status = db.Column(db.String(20))          # success / failed
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)