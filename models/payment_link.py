from extensions import db
from datetime import datetime

class PaymentLink(db.Model):
    __tablename__ = 'payment_links'

    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.String(100), nullable=False, index=True)
    customer_name = db.Column(db.String(100))
    customer_email = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(200))
    payment_link = db.Column(db.Text)
    qr_code = db.Column(db.Text)
    status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)