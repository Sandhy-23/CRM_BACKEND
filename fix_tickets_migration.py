import os

def fix_tickets_migration():
    """
    Finds the migration file 'ff9b1a2eed45_...' and deletes the
    offending 'batch_alter_table' block for the 'tickets' table
    to prevent duplicate column errors.
    """
    migration_dir = r'C:\projects\crm_backend\migrations\versions'
    target_file = 'ff9b1a2eed45_add_team_user_and_permissions.py'
    file_path = os.path.join(migration_dir, target_file)

    if not os.path.exists(file_path):
        print(f"❌ ERROR: Migration file not found at {file_path}")
        print("👉 Please ensure the file name is correct and the migration has been generated.")
        return

    print(f"✅ Found migration file: {file_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    in_block_to_delete = False
    block_deleted = False

    for line in lines:
        stripped_line = line.strip()

        if "with op.batch_alter_table('tickets', schema=None) as batch_op:" in stripped_line:
            in_block_to_delete = True
            block_deleted = True
            continue
        
        if in_block_to_delete:
            if line.startswith(' ') and stripped_line != "":
                continue
            else:
                in_block_to_delete = False
        
        new_lines.append(line)

    if block_deleted:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        print("🚀 Fix applied successfully. The 'tickets' batch alter block has been deleted.")
    else:
        print("✅ No 'tickets' batch alter block found to delete.")

if __name__ == "__main__":
    fix_tickets_migration()