from extensions import db
from datetime import datetime

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending') # Pending, In Progress, Completed
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # New Fields
    priority = db.Column(db.String(20), default="Medium")
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True)
    deal_id = db.Column(db.Integer, db.ForeignKey("deals.id"), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)

    # Relationships
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tasks')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_tasks')
    organization = db.relationship('Organization', backref='tasks')

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "lead_id": self.lead_id,
            "deal_id": self.deal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None
        }