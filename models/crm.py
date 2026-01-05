from extensions import db
from datetime import datetime

class Lead(db.Model):
    __tablename__ = "leads"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    description = db.Column(db.Text) # For contact form messages
    status = db.Column(db.String(50), default="New") # New, Contacted, Qualified, Lost
    score = db.Column(db.Integer, default=0)
    source = db.Column(db.String(50))
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Deal(db.Model):
    __tablename__ = "deals"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, default=0.0)
    stage = db.Column(db.String(50), default="Prospecting")
    status = db.Column(db.String(50), default='Open') # Open, Won, Lost
    pipeline_id = db.Column(db.Integer, nullable=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)

class Ticket(db.Model):
    __tablename__ = "tickets"
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(20), default="Open")
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))

class Campaign(db.Model):
    __tablename__ = "campaigns"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50)) # Email, WhatsApp
    status = db.Column(db.String(20), default="Draft")
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))

class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    status = db.Column(db.String(50), default='Pending') # Pending, Completed
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))