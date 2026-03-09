from extensions import db
from datetime import datetime

class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(50), unique=True)
    subject = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Foreign Keys
    contact_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # The creator (User/Contact)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # The employee
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)

    priority = db.Column(db.String(20), default='Medium') # Low, Medium, High
    status = db.Column(db.String(20), default='Open') # Open, In Progress, Resolved, Closed
    category = db.Column(db.String(50)) # Billing, Technical, etc.
    
    sla_due_at = db.Column(db.DateTime, nullable=True)
    first_response_time = db.Column(db.DateTime, nullable=True) # Added for Health Score
    sla_breached = db.Column(db.Boolean, default=False) # Added for Health Score
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    creator = db.relationship('User', foreign_keys=[contact_id], backref='created_tickets')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tickets')

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_number": self.ticket_number,
            "subject": self.subject,
            "description": self.description,
            "contact_id": self.contact_id,
            "contact_name": self.creator.name if self.creator else "Unknown",
            "assigned_to": self.assigned_to,
            "assigned_name": self.assignee.name if self.assignee else "Unassigned",
            "priority": self.priority,
            "status": self.status,
            "category": self.category,
            "sla_due_at": self.sla_due_at.isoformat() if self.sla_due_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None
        }

class TicketComment(db.Model):
    __tablename__ = 'ticket_comments'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User')
    
    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "user_name": self.user.name if self.user else "Unknown",
            "comment": self.comment,
            "is_internal": self.is_internal,
            "created_at": self.created_at.isoformat()
        }