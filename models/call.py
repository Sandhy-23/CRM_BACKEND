from extensions import db
from datetime import datetime

class Call(db.Model):
    __tablename__ = "calls"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20))
    duration = db.Column(db.Integer)
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    organization_id = db.Column(db.Integer)
