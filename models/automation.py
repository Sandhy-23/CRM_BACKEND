from extensions import db
from datetime import datetime

class AutomationRule(db.Model):
    __tablename__ = 'automation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    trigger_type = db.Column(db.String(50), nullable=False) # lead_created, lead_updated, status_changed
    trigger_from = db.Column(db.String(50)) # nullable
    trigger_to = db.Column(db.String(50))   # nullable
    condition_logic = db.Column(db.String(10), default='AND') # AND / OR
    priority = db.Column(db.Integer, default=1)
    stop_processing = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_id = db.Column(db.Integer) # For multi-tenancy

    # Relationships
    conditions = db.relationship('AutomationCondition', backref='rule', cascade="all, delete-orphan")
    actions = db.relationship('AutomationAction', backref='rule', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "trigger_from": self.trigger_from,
            "trigger_to": self.trigger_to,
            "condition_logic": self.condition_logic,
            "priority": self.priority,
            "stop_processing": self.stop_processing,
            "is_active": self.is_active,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions]
        }

class AutomationCondition(db.Model):
    __tablename__ = 'automation_conditions'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id'), nullable=False)
    field = db.Column(db.String(50), nullable=False)
    operator = db.Column(db.String(20), nullable=False) # equals, contains, greater_than
    value = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {"field": self.field, "operator": self.operator, "value": self.value}

class AutomationAction(db.Model):
    __tablename__ = 'automation_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False) # assign_team, assign_user, archive, send_email
    action_value = db.Column(db.String(255)) # team_id / user_id / template_id

    def to_dict(self):
        return {"action_type": self.action_type, "action_value": self.action_value}

class AutomationLog(db.Model):
    __tablename__ = 'automation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id'))
    lead_id = db.Column(db.Integer)
    action_executed = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "lead_id": self.lead_id,
            "action_executed": self.action_executed,
            "executed_at": self.executed_at.isoformat()
        }