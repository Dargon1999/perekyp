import os
import sys
import subprocess
import logging

def run():
    print("Starting MoneyTracker...")
    try:
        # Check if python is available
        subprocess.check_call([sys.executable, "--version"])
        
        # Run main.py without console window
        flags = 0
        if os.name == 'nt':
            flags = subprocess.CREATE_NO_WINDOW
            
        subprocess.Popen([sys.executable, "main.py"], 
                         creationflags=flags)
        print("MoneyTracker started successfully.")
    except Exception as e:
        print(f"Error starting MoneyTracker: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    run()