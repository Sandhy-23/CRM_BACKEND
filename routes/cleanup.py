import os
import shutil

def cleanup():
    """
    Cleans up __pycache__ directories and removes known misplaced files
    that cause ModuleNotFoundError or ImportError.
    """
    root_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"🧹 Starting cleanup in: {root_dir}")

    # 1. Remove __pycache__ folders recursively
    print("\n--- Removing __pycache__ ---")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '__pycache__' in dirnames:
            cache_path = os.path.join(dirpath, '__pycache__')
            try:
                shutil.rmtree(cache_path)
                print(f"✔ Deleted: {cache_path}")
            except Exception as e:
                print(f"❌ Failed to delete {cache_path}: {e}")
            dirnames.remove('__pycache__')

    # 2. Remove misplaced files that conflict with real modules
    print("\n--- Removing misplaced files ---")
    files_to_remove = [
        "call.py",
        "Call.py",
        "call_routes.py",
        "inbox_routes.py",
        os.path.join("models", "call_routes.py"),
        os.path.join("models", "inbox_routes.py"),
        os.path.join("models", "channel_routes.py"),
        os.path.join("routes", "conversation.py"),     # Duplicate Model
        os.path.join("routes", "message.py"),          # Duplicate Model
        os.path.join("routes", "channel_account.py")   # Duplicate Model
    ]

    for rel_path in files_to_remove:
        file_path = os.path.join(root_dir, rel_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✔ Deleted misplaced file: {rel_path}")
            except Exception as e:
                print(f"❌ Failed to delete {rel_path}: {e}")

    print("\n✨ Cleanup complete. Please restart your server now.")

if __name__ == "__main__":
    cleanup()