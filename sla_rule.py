from extensions import db

class SLARule(db.Model):
    __tablename__ = "sla_rules"

    id = db.Column(db.Integer, primary_key=True)
    priority = db.Column(db.String(50), nullable=False, unique=True)
    response_time_hours = db.Column(db.Integer, nullable=False)
    resolution_time_hours = db.Column(db.Integer, nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "priority": self.priority,
            "response_time_hours": self.response_time_hours,
            "resolution_time_hours": self.resolution_time_hours
        }