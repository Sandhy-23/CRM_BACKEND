from extensions import db
from datetime import datetime

class OtpVerification(db.Model):
    __tablename__ = 'otp_verifications'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    name = db.Column(db.String(100)) # Store temp data
    password_hash = db.Column(db.String(200)) # Store temp data
    expiry = db.Column(db.DateTime, nullable=False)