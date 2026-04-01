from app import app
from extensions import db
from models.user import User

def fix_typos():
    with app.app_context():
        print("\n--- 🔧 FIXING EMAIL TYPOS ---")
        
        # Find users with 'gamil.com'
        typo_users = User.query.filter(User.email.like("%@gamil.com%")).all()
        
        if not typo_users:
            print("✅ No 'gamil.com' typos found.")
            return

        for user in typo_users:
            old_email = user.email
            new_email = old_email.replace("@gamil.com", "@gmail.com")
            print(f"   👉 Fixing: {old_email}  -->  {new_email}")
            user.email = new_email
        
        db.session.commit()
        print(f"✅ Fixed {len(typo_users)} records.")

if __name__ == "__main__":
    fix_typos()