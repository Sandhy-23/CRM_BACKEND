from extensions import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    razorpay_payment_link_id = db.Column(db.String(200))
    razorpay_payment_link_url = db.Column(db.String(500))
    amount = db.Column(db.Integer)
    status = db.Column(db.String(50), default="created")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)