from extensions import db
from datetime import datetime

class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String(100), nullable=True)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    page_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)