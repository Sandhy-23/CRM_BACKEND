from extensions import db

class EnterpriseRule(db.Model):
    __tablename__ = 'enterprise_rules'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    icon_key = db.Column(db.String(50))
    description = db.Column(db.String(255))
    rules = db.Column(db.JSON) # Stores the list of rules as a JSON array
    theme = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "iconKey": self.icon_key,
            "description": self.description,
            "rules": self.rules,
            "theme": self.theme
        }