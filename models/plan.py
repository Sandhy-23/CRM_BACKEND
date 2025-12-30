from extensions import db

# Association table for Many-to-Many relationship between Plan and Feature
plan_features = db.Table('plan_features',
    db.Column('plan_id', db.Integer, db.ForeignKey('plans.id'), primary_key=True),
    db.Column('feature_id', db.Integer, db.ForeignKey('features.id'), primary_key=True)
)

class Plan(db.Model):
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # Free, Basic, Pro
    price = db.Column(db.String(20), nullable=False)
    user_limit = db.Column(db.Integer, nullable=True) # None (NULL) represents Unlimited
    description = db.Column(db.String(200))
    
    features = db.relationship('Feature', secondary=plan_features, lazy='subquery',
        backref=db.backref('plans', lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "user_limit": self.user_limit,
            "features": [f.key for f in self.features]
        }

class Feature(db.Model):
    __tablename__ = 'features'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(50), unique=True, nullable=False) # e.g. 'analytics', 'user_management'