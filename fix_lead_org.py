from app import app
from extensions import db
from models.crm import Lead
from models.user import User

def fix_lead():
    with app.app_context():
        print("--- 🔧 Fix Lead Organization Mismatch ---")
        
        lead_id = input("Enter Lead ID to fix (e.g., 1): ").strip()
        user_email = input("Enter your User Email (to match Org): ").strip()
        
        try:
            lead = db.session.get(Lead, int(lead_id))
        except ValueError:
            print("❌ Invalid Lead ID.")
            return

        user = User.query.filter_by(email=user_email).first()
        
        if not lead:
            print("❌ Lead not found.")
            return
        if not user:
            print(f"❌ User '{user_email}' not found.")
            print("👉 Available Users:")
            for u in User.query.all():
                print(f"   - {u.email} (Org ID: {u.organization_id})")
            return
            
        print(f"Current Lead Org ID: {lead.company_id}")
        print(f"Target User Org ID: {user.organization_id}")
        
        if lead.company_id == user.organization_id:
            print("✅ IDs already match! No changes needed.")
        else:
            lead.company_id = user.organization_id
            lead.owner_id = user.id # Assign to user to ensure visibility
            db.session.commit()
            print(f"✅ Updated Lead {lead.id} to belong to Org {user.organization_id} (User: {user.email})")

if __name__ == "__main__":
    fix_lead()