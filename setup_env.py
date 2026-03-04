import os

def create_env():
    print("--- 🛠️ CRM Backend Setup ---")
    print("This script will create a .env file with dedicated database credentials.")
    
    # Switching to root user as requested for troubleshooting.
    db_user = "root"
    db_pass = "root"
    
    env_content = f'DATABASE_URL=mysql+pymysql://{db_user}:{db_pass}@localhost/crm_db\n'
    env_content += 'FLASK_APP=app.py\n'
    env_content += 'FLASK_ENV=development\n'
    env_content += 'SECRET_KEY=dev-secret-key\n'
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\n✅ .env file created successfully with 'root' credentials!")
    print(f"   Database URI set to: mysql+pymysql://{db_user}:{'*'*len(db_pass)}@localhost/crm_db")
    print("👉 Now run: python app.py")

if __name__ == "__main__":
    create_env()