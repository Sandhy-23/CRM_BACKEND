from app import app
from extensions import db
from models.crm import Lead
from datetime import datetime

def seed_leads():
    """Seeds the database with the specified sample lead data."""
    
    leads_data = [
        {
            "name": "Riya Sharma",
            "email": "riya@gmail.com",
            "phone": "9876543210",
            "company": "Pixel Labs",
            "source": "Instagram",
            "status": "Hot",
            "score": "High",
            "sla": "On Track",
            "owner": "Varshini",
            "description": "Interested in website redesign",
        },
        {
            "name": "Aman Patel",
            "email": "aman@corp.com",
            "phone": "9876543211",
            "company": "CorpEdge",
            "source": "Campaign",
            "status": "Follow-up",
            "score": "Medium",
            "sla": "Delayed",
            "owner": "Ravi",
            "description": "Needs pricing details",
        },
        {
            "name": "Neha Verma",
            "email": "neha@mail.com",
            "phone": "9876543212",
            "company": "Bloom Co",
            "source": "Website",
            "status": "Converted",
            "score": "High",
            "sla": "On Track",
            "owner": "Anu",
            "description": "Closed premium plan",
        },
        {
            "name": "Rahul Singh",
            "email": "rahul@xyz.com",
            "phone": "9876543213",
            "company": "XYZ Pvt Ltd",
            "source": "Referral",
            "status": "Lost",
            "score": "Low",
            "sla": "Delayed",
            "owner": "Varshini",
            "description": "Budget mismatch",
        },
    ]

    with app.app_context():
        print("🌱 Seeding leads...")
        added_count = 0
        for data in leads_data:
            if Lead.query.filter_by(email=data['email']).first():
                print(f"   - Skipping '{data['email']}', already exists.")
                continue

            new_lead = Lead(**data)
            db.session.add(new_lead)
            added_count += 1
            print(f"   + Adding '{data['email']}'.")
        
        if added_count > 0:
            db.session.commit()
            print(f"✅ Successfully added {added_count} new leads.")
        else:
            print("✅ No new leads to add.")

if __name__ == "__main__":
    seed_leads()