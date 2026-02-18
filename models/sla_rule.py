from extensions import db

class SLARule(db.Model):
    __tablename__ = "sla_rules"

    id = db.Column(db.Integer, primary_key=True)
    priority = db.Column(db.String(50), nullable=False)
    response_time_hours = db.Column(db.Integer, nullable=False)
    resolution_time_hours = db.Column(db.Integer, nullable=False)