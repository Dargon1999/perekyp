import sys
import os
from datetime import datetime

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # Use the directory of the current script (utils.py) as base to ensure assets are found
    # regardless of where the script is launched from (CWD).
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def format_license_date(date_str):
    """
    Format license date to strict 'DD.MM.YYYY HH:MM'.
    Handles timestamps, ISO strings, and various separators.
    Returns 'Дата не указана' on failure/empty.
    """
    if not date_str or date_str == "Lifetime":
        return "Навсегда" if date_str == "Lifetime" else "Дата не указана"
    
    try:
        # 0. Try numeric timestamp (int or float, string or number)
        # Check if it looks like a number
        str_val = str(date_str)
        if str_val.replace(".", "", 1).isdigit():
            ts = float(str_val)
            # Check if milliseconds (13 digits) or seconds (10 digits)
            # 3000-01-01 is roughly 32503680000 (11 digits), so > 100000000000 is definitely ms
            if ts > 32503680000: 
                ts = ts / 1000.0
            dt = datetime.fromtimestamp(ts)
            return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError, OverflowError):
        pass

    try:
        # 1. Try ISO format (with T and Z)
        clean_str = str(date_str).replace("T", " ").replace("Z", "").split(".")[0].split("+")[0]
        dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, AttributeError):
        pass
        
    try:
        # 2. Try YYYY-MM-DD
        dt = datetime.strptime(str(date_str), "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y 00:00")
    except (ValueError, AttributeError):
        pass
        
    try:
        # 3. Try DD.MM.YYYY
        dt = datetime.strptime(str(date_str), "%d.%m.%Y")
        return dt.strftime("%d.%m.%Y 00:00")
    except (ValueError, AttributeError):
        pass
        
    # Fallback: manual parsing for edge cases
    try:
        normalized = str(date_str).replace(" ", "-").replace(".", "-").replace("/", "-")
        parts = normalized.split("-")
        if len(parts) >= 3:
            # Assume YYYY-MM-DD if first part is 4 digits
            if len(parts[0]) == 4:
                return f"{parts[2]}.{parts[1]}.{parts[0]} 00:00"
            # Assume DD-MM-YYYY if last part is 4 digits
            elif len(parts[2]) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]} 00:00"
    except:
        pass

    return "Неверный формат"
