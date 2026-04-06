from extensions import db
from datetime import datetime

class SupportTicket(db.Model):
    __tablename__ = "support_tickets"

    id = db.Column(db.String(10), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column("desc", db.Text)
    status = db.Column(db.String(20), default='Open')
    priority = db.Column(db.String(10), default="Medium")
    category = db.Column(db.String(20), default="Bug")
    assignee = db.Column(db.String(100))
    submitted_by = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    responses = db.Column(db.Integer, default=0)

    sla_status = db.Column(db.String(20), default='On Track')
    time_remaining = db.Column(db.String(20))

    first_response_due_at = db.Column(db.DateTime)
    resolution_due_at = db.Column(db.DateTime)
    first_responded_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    first_response_breached = db.Column(db.Boolean, default=False)
    resolution_breached = db.Column(db.Boolean, default=False)
    
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))

class TicketMessage(db.Model):
    __tablename__ = "ticket_messages"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.String(10), db.ForeignKey('support_tickets.id'))
    type = db.Column(db.String(10)) # customer or agent
    author = db.Column(db.String(100))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TicketNote(db.Model):
    __tablename__ = "ticket_notes"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.String(10), db.ForeignKey('support_tickets.id'))
    author = db.Column(db.String(100))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TicketActivity(db.Model):
    __tablename__ = "ticket_activity"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.String(10), db.ForeignKey('support_tickets.id'))
    action = db.Column(db.String(255))
    color = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)