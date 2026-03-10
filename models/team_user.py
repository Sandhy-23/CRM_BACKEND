from extensions import db

class TeamUser(db.Model):
    """Represents a user account with specific roles and permissions."""
    __tablename__ = "team_users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50))
    web_address = db.Column(db.String(255))

class Permission(db.Model):
    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True)
    permission_name = db.Column(db.String(100), unique=True)

class UserPermission(db.Model):
    __tablename__ = "user_permissions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('team_users.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)