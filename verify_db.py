from app import app
from models.user import User
from models.organization import Organization
from models.contact import Contact
from models.crm import Lead

def verify_data():
    with app.app_context():
        print("--- 🔍 Database Verification Tool ---")

        # 1. Organizations
        orgs = Organization.query.all()
        print(f"\n🏢 Organizations ({len(orgs)} found):")
        for o in orgs:
            print(f"   [ID: {o.id}] {o.name} | Plan: {o.subscription_plan}")

        # 2. Users
        users = User.query.all()
        print(f"\n👤 Users ({len(users)} found):")
        for u in users:
            org_name = u.organization.name if u.organization else "None"
            print(f"   [ID: {u.id}] {u.name} ({u.email}) | Role: {u.role} | Org ID: {u.organization_id} ({org_name})")

        # 3. Contacts
        contacts = Contact.query.all()
        print(f"\n📇 Contacts ({len(contacts)} found):")
        for c in contacts:
            print(f"   [ID: {c.id}] {c.first_name} {c.last_name} | Email: {c.email} | Mobile: {c.mobile}")

        # 4. Leads
        leads = Lead.query.all()
        print(f"\n💼 Leads ({len(leads)} found):")
        for l in leads:
            print(f"   [ID: {l.id}] {l.first_name} {l.last_name} | Org ID: {l.company_id} | Status: {l.status}")

        print("\n✅ Verification Complete.")

if __name__ == "__main__":
    verify_data()