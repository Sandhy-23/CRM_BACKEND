from extensions import db

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    users = db.relationship('User', back_populates='team')

class LocationTeamMapping(db.Model):
    __tablename__ = 'location_team_mapping'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team = db.relationship('Team')