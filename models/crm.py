from extensions import db
from datetime import datetime

class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    source = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    score = db.Column(db.String(20), nullable=False)
    sla = db.Column(db.String(20), nullable=False)
    owner = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

class Deal(db.Model):
    __tablename__ = 'deals'
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100))
    pipeline = db.Column(db.String(50), nullable=False)
    stage = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Integer, default=0)
    owner = db.Column(db.String(50))
    close_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    status = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    id = db.Column(db.Integer, primary_key=True)