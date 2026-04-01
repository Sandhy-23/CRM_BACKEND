from app import app
from extensions import db
from models.enterprise_rule import EnterpriseRule

def seed_rules():
    with app.app_context():
        print("🌱 Seeding Enterprise Rules...")
        
        # Clear existing rules
        db.create_all()
        EnterpriseRule.query.delete()
        
        rules_data = [
            {
                "title": "Deal Approval",
                "icon_key": "ShieldCheck",
                "description": "Deals over ₹10 Lakh require approval",
                "theme": "blue",
                "rules": [
                    {"key": "Min Value", "value": "₹10,00,000"},
                    {"key": "Action", "value": "Set Status: Pending"}
                ]
            },
            {
                "title": "Stage Lock",
                "icon_key": "Lock",
                "description": "Cannot move to 'Won' without contract",
                "theme": "red",
                "rules": [
                    {"key": "Target Stage", "value": "Closed Won"},
                    {"key": "Requirement", "value": "File: Signed Contract"}
                ]
            },
            {
                "title": "Lead Scoring",
                "icon_key": "TrendingUp",
                "description": "Auto-score corporate emails",
                "theme": "green",
                "rules": [
                    {"key": "Condition", "value": "Email domain != gmail/yahoo"},
                    {"key": "Action", "value": "+15 Points"}
                ]
            }
        ]
        
        for data in rules_data:
            rule = EnterpriseRule(**data)
            db.session.add(rule)
            
        db.session.commit()
        print("✅ Enterprise Rules seeded successfully.")

if __name__ == "__main__":
    seed_rules()