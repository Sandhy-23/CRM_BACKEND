import os

def fix_migration_file():
    # Define the directory
    migration_dir = os.path.join(os.getcwd(), 'migrations', 'versions')
    target_filename = '0cf92ae6d9bd_a_descriptive_message_e_g_add_status_to_.py'
    file_path = os.path.join(migration_dir, target_filename)

    # Check if file exists, if not search for it
    if not os.path.exists(file_path):
        print(f"🔍 Specific file not found. Searching all migration files in {migration_dir}...")
        if os.path.exists(migration_dir):
            for fname in os.listdir(migration_dir):
                if fname.endswith(".py"):
                    fpath = os.path.join(migration_dir, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        if "op.drop_table('whatsapp_accounts')" in f.read():
                            file_path = fpath
                            print(f"✅ Found file: {fname}")
                            break
    
    if not os.path.exists(file_path):
        print("❌ Could not find the migration file. Please check manually.")
        return

    # Read and Modify
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    with open(file_path, 'w', encoding='utf-8') as f:
        for line in lines:
            if "op.drop_table('whatsapp_accounts')" in line and not line.strip().startswith("#"):
                f.write(f"# {line.lstrip()}") # Comment out the line
                print("✅ Commented out: op.drop_table('whatsapp_accounts')")
            else:
                f.write(line)
    print("🚀 Fix applied successfully.")

if __name__ == "__main__":
    fix_migration_file()