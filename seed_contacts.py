from app import app
from extensions import db
from models.contact import Contact

def seed_contacts():
    """Seeds the database with the specified sample contact data."""
    
    contacts_data = [
        {
            "name": "Riya Sharma",
            "company": "Acme Corp",
            "email": "riya@acme.com",
            "phone": "+91 98765 43210",
            "owner": "Varshini",
            "lastContact": "2 days ago",
            "status": "Active",
        },
        {
            "name": "Aman Patel",
            "company": "Zeta Labs",
            "email": "aman@zeta.io",
            "phone": "+91 99887 66554",
            "owner": "Ravi",
            "lastContact": "Today",
            "status": "New",
        },
        {
            "name": "Sneha Rao",
            "company": "PixelWorks",
            "email": "sneha@pixel.com",
            "phone": "+91 91234 56789",
            "owner": "Anu",
            "lastContact": "1 week ago",
            "status": "Inactive",
        },
    ]

    with app.app_context():
        print("🌱 Seeding contacts...")
        added_count = 0
        for data in contacts_data:
            if Contact.query.filter_by(email=data['email']).first():
                print(f"   - Skipping '{data['email']}', already exists.")
                continue

            new_contact = Contact(
                name=data['name'], company=data.get('company'), email=data['email'],
                phone=data.get('phone'), owner=data.get('owner'),
                last_contact=data.get('lastContact'), status=data.get('status')
            )
            db.session.add(new_contact)
            added_count += 1
            print(f"   + Adding '{data['email']}'.")
        
        if added_count > 0:
            db.session.commit()
            print(f"✅ Successfully added {added_count} new contacts.")
        else:
            print("✅ No new contacts to add.")

if __name__ == "__main__":
    seed_contacts()