from extensions import db

class State(db.Model):
    __tablename__ = "states"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(150))
    theme = db.Column(db.String(50))

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id"),
        nullable=False
    )

    branches = db.relationship("Branch", backref="state", lazy=True)