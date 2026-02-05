from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    # Per user request, roles are 'admin', 'agent'
    role = db.Column(db.String(50), default='agent')
    status = db.Column(db.String(20), default='Active')
    date_of_joining = db.Column(db.DateTime)
    is_approved = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    provider = db.Column(db.String(20), default='email')
    provider_id = db.Column(db.String(100))

    # New field from user request
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    team = db.relationship('Team', back_populates='users')

class LoginHistory(db.Model):
    __tablename__ = 'login_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    status = db.Column(db.String(20))
    user = db.relationship('User')