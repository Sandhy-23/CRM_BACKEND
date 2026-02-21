from extensions import db
from datetime import datetime

class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(150))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    source = db.Column(db.String(50)) # website / orbit / whatsapp
    score = db.Column(db.String(20))
    sla = db.Column(db.String(20))
    # description = db.Column(db.Text) # Temporarily disabled
    assigned_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    status = db.Column(db.String(50), default='new') # new, unassigned, assigned
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assigned_team = db.relationship('Team')
    assigned_user = db.relationship('User')

# Keeping other models to avoid breaking imports
class Deal(db.Model):
    __tablename__ = 'deals'
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
    pipeline = db.Column(db.String(50))
    title = db.Column(db.String(100))
    company = db.Column(db.String(100))
    stage = db.Column(db.String(50))
    status = db.Column(db.String(50), default='open')
    value = db.Column(db.Integer)
    owner = db.Column(db.String(100))
    close_date = db.Column(db.Date)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(50))
    user_id = db.Column(db.Integer)
    organization_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)