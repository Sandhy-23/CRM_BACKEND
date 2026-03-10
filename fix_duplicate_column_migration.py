import os
import re

def fix_migration():
    """
    Finds the specific migration file and replaces the content of the
    upgrade and downgrade functions with 'pass' to prevent duplicate column errors.
    """
    migration_dir = r'C:\projects\crm_backend\migrations\versions'
    target_file = '3e58a7764ec4_.py'
    file_path = os.path.join(migration_dir, target_file)

    if not os.path.exists(file_path):
        print(f"❌ ERROR: Migration file not found at {file_path}")
        print("👉 Please ensure the file name '3e58a7764ec4_.py' is correct.")
        return

    print(f"✅ Found migration file: {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()

    # Replace upgrade function body
    content = re.sub(r"(def upgrade\(\):\n)(?:.|\n)*?(?=\ndef|\Z)", r"\1    pass\n\n", content, count=1)
    
    # Replace downgrade function body
    content = re.sub(r"(def downgrade\(\):\n)(?:.|\n)*?(?=\ndef|\Z)", r"\1    pass\n\n", content, count=1)

    with open(file_path, 'w') as f:
        f.write(content)
        
    print("🚀 Fix applied successfully. The 'upgrade' and 'downgrade' functions now contain only 'pass'.")

if __name__ == "__main__":
    fix_migration()