from extensions import db
from datetime import datetime

class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('User', back_populates='team')