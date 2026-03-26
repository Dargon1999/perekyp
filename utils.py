import sys
import os
from datetime import datetime
import logging

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def _is_valid_number(s):
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False

def format_license_date(date_str):
    if not date_str or date_str == "Lifetime":
        return "Навсегда" if date_str == "Lifetime" else "Дата не указана"
    
    try:
        str_val = str(date_str).strip()
        if _is_valid_number(str_val):
            ts = float(str_val)
            MIN_TIMESTAMP = 1577836800
            MAX_TIMESTAMP = 4102444800
            if ts > 32503680000: 
                ts = ts / 1000.0
            if MIN_TIMESTAMP < ts < MAX_TIMESTAMP:
                dt = datetime.fromtimestamp(ts)
                return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError, OverflowError):
        pass

    try:
        clean_str = str(date_str).replace("T", " ").replace("Z", "").split(".")[0].split("+")[0]
        dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, AttributeError):
        pass
        
    try:
        dt = datetime.strptime(str(date_str), "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y 00:00")
    except (ValueError, AttributeError):
        pass
        
    try:
        dt = datetime.strptime(str(date_str), "%d.%m.%Y")
        return dt.strftime("%d.%m.%Y 00:00")
    except (ValueError, AttributeError):
        pass
        
    try:
        normalized = str(date_str).replace(" ", "-").replace(".", "-").replace("/", "-")
        parts = normalized.split("-")
        if len(parts) >= 3:
            if len(parts[0]) == 4:
                return f"{parts[2]}.{parts[1]}.{parts[0]} 00:00"
            elif len(parts[2]) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]} 00:00"
    except Exception as e:
        logging.warning(f"Manual date parsing failed for '{date_str}': {e}")

    return "Неверный формат"

class Money:
    """Handles monetary values in minor units (cents/kopecks)."""
    def __init__(self, amount_in_minor=0):
        self.amount = int(round(amount_in_minor))

    @classmethod
    def from_major(cls, amount_in_major):
        """Creates Money from major unit (float/int dollars)."""
        try:
            return cls(round(float(amount_in_major) * 100))
        except (ValueError, TypeError):
            return cls(0)

    def to_major(self):
        """Returns value in major unit (float dollars)."""
        return self.amount / 100.0

    def format(self, symbol="$"):
        """Formats for display."""
        return f"{symbol}{self.to_major():,.2f}"

    def __add__(self, other):
        if isinstance(other, Money):
            return Money(self.amount + other.amount)
        return Money(self.amount + round(other * 100))

    def __sub__(self, other):
        if isinstance(other, Money):
            return Money(self.amount - other.amount)
        return Money(self.amount - round(other * 100))
    
    def __mul__(self, other):
        return Money(round(self.amount * other))
    
    def __truediv__(self, other):
        return Money(round(self.amount / other))

    def __abs__(self):
        return Money(abs(self.amount))

    def __lt__(self, other):
        if isinstance(other, Money): return self.amount < other.amount
        return self.to_major() < other

    def __le__(self, other):
        if isinstance(other, Money): return self.amount <= other.amount
        return self.to_major() <= other

    def __gt__(self, other):
        if isinstance(other, Money): return self.amount > other.amount
        return self.to_major() > other

    def __ge__(self, other):
        if isinstance(other, Money): return self.amount >= other.amount
        return self.to_major() >= other

    def __eq__(self, other):
        if isinstance(other, Money): return self.amount == other.amount
        return self.to_major() == other

