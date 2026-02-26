from extensions import db

class Branch(db.Model):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    manager_name = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)

    state_id = db.Column(
        db.Integer,
        db.ForeignKey("states.id"),
        nullable=False
    )

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id"),
        nullable=False
    )