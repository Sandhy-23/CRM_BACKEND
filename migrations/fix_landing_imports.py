import os

def fix_landing_page_imports():
    # Try to locate models/__init__.py relative to this script or absolute path
    possible_paths = [
        os.path.join("..", "models", "__init__.py"), # If running from migrations/
        os.path.join("models", "__init__.py"),       # If running from root
        r"c:\projects\crm_backend\models\__init__.py" # Absolute path
    ]
    
    target_path = None
    for p in possible_paths:
        if os.path.exists(p):
            target_path = p
            break
            
    if not target_path:
        print("❌ Could not find models/__init__.py")
        return

    print(f"🔍 Checking {target_path}...")
    
    with open(target_path, 'r') as f:
        content = f.read()
        
    # Replace the problematic line
    if "from .landing_page import LandingPage, LandingPageForm" in content or "LandingPageForm" in content:
        new_content = content.replace("from .landing_page import LandingPage, LandingPageForm, FormSubmission, LandingPageEvent", "from .landing_page import LandingPage")
        # Fallback for partial matches or different formatting
        if "LandingPageForm" in new_content:
             # Regex or simple line replacement would be safer, but for this specific error:
             lines = content.splitlines()
             new_lines = []
             for line in lines:
                 if "from .landing_page import" in line:
                     new_lines.append("from .landing_page import LandingPage")
                 else:
                     new_lines.append(line)
             new_content = "\n".join(new_lines)

        with open(target_path, 'w') as f:
            f.write(new_content)
        print("✅ Fixed models/__init__.py: Removed LandingPageForm and other deleted classes.")
    else:
        print("✅ models/__init__.py is already correct.")

if __name__ == "__main__":
    fix_landing_page_imports()