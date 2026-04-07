from extensions import db
from datetime import datetime

class SupportTicket(db.Model):
    __tablename__ = "support_tickets"

    id = db.Column(db.String(10), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    priority = db.Column(db.String(50))
    status = db.Column(db.String(50), default="open")
    sla_status = db.Column(db.String(50))
    assignee = db.Column(db.String(100))
    submitted_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
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