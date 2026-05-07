import hashlib
import subprocess
import os

def get_hwid():
    try:
        # Get Motherboard UUID
        mb = subprocess.check_output('wmic baseboard get serialnumber', shell=True).decode().split('\n')[1].strip()
        # Get CPU ID
        cpu = subprocess.check_output('wmic cpu get processorid', shell=True).decode().split('\n')[1].strip()
        
        combined = f"{mb}_{cpu}"
        return hashlib.sha256(combined.encode()).hexdigest()
    except Exception:
        return "UNKNOWN_HWID"

def get_pc_name():
    return os.environ.get('COMPUTERNAME', 'Unknown')
