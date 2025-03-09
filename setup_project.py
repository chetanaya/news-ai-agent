import os
import shutil
import argparse

def setup_project():
    """Set up the Brand News Analyzer project structure"""
    print("Setting up Brand News Analyzer...")
    
    # Create necessary directories
    directories = [
        "data",
        "data/raw",
        "data/processed",
        "data/archive",
        "logs",
        "config"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Check if .env file exists, if not create from example
    if not os.path.exists(".env") and os.path.exists(".env.example"):
        shutil.copy(".env.example", ".env")
        print("Created .env file from .env.example - please edit it with your API keys")
    
    # Create empty __init__.py files in directories if they don't exist
    init_dirs = [".", "app", "app/pages", "app/components", "agents", "utils"]
    for directory in init_dirs:
        os.makedirs(directory, exist_ok=True)
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# Auto-generated init file\n")
            print(f"Created {init_file}")
    
    print("\nSetup complete! Next steps:")
    print("1. Edit the .env file with your API keys")
    print("2. Install requirements: pip install -r requirements.txt")
    print("3. Run the app: streamlit run app/app.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up the Brand News Analyzer project")
    args = parser.parse_args()
    setup_project()