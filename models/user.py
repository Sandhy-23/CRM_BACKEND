from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    otp = db.Column(db.String(6))
    role = db.Column(db.String(20), default="User") # Admin, Manager, Sales, Support
    is_approved = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(50))
    designation = db.Column(db.String(50))
    status = db.Column(db.String(20), default="Active") # Active, Inactive
    date_of_joining = db.Column(db.DateTime)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)

    is_verified = db.Column(db.Boolean, default=False)
    otp_expiry = db.Column(db.DateTime)
    reset_token = db.Column(db.String(100))
    reset_token_expiry = db.Column(db.DateTime)

class LoginHistory(db.Model):
    __tablename__ = "login_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20)) # Success, Failed
