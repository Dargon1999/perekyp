import os
import sys
import subprocess
import logging

def run():
    print("Starting MoneyTracker...")
    try:
        # Check if python is available
        subprocess.check_call([sys.executable, "--version"])
        
        # Run main.py
        subprocess.Popen([sys.executable, "main.py"], 
                         creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
        print("MoneyTracker started successfully.")
    except Exception as e:
        print(f"Error starting MoneyTracker: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    run()