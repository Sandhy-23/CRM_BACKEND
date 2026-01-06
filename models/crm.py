from extensions import db
from datetime import datetime

class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    company = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    source = db.Column(db.String(50))
    status = db.Column(db.String(50), default='New')
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_to = db.Column(db.Integer)

class Deal(db.Model):
    __tablename__ = 'deals'
    id = db.Column(db.Integer, primary_key=True)
    deal_name = db.Column(db.String(100))
    amount = db.Column(db.Float)
    stage = db.Column(db.String(50))
    probability = db.Column(db.Integer)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    account_id = db.Column(db.Integer)
    contact_id = db.Column(db.Integer)
    status = db.Column(db.String(50))
    closed_at = db.Column(db.DateTime)

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