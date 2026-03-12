from extensions import db
from datetime import datetime

class SalesRule(db.Model):
    __tablename__ = "sales_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    module = db.Column(db.String(50), nullable=False)

    condition_field = db.Column(db.String(100))
    condition_operator = db.Column(db.String(50))
    condition_value = db.Column(db.String(255))

    action_type = db.Column(db.String(100))
    action_value = db.Column(db.String(255))

    priority = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)