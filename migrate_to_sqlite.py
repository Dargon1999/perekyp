import json
import os
from datetime import datetime
from database_manager import DatabaseManager, Transaction, Asset, Profile, Base
from sqlalchemy.orm import sessionmaker

def migrate_json_to_sqlite(json_path, db_path="data.db"):
    if not os.path.exists(json_path):
        print(f"JSON file not found: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db_manager = DatabaseManager(db_path)
    session = db_manager.get_session()

    try:
        for p_data in data.get("profiles", []):
            # Create Profile
            profile = Profile(
                name=p_data.get("name", "Unknown"),
                created_at=datetime.strptime(p_data.get("created_at", datetime.now().strftime("%d.%m.%Y")), "%d.%m.%Y") if p_data.get("created_at") else datetime.now(),
                data=json.dumps(p_data.get("settings", {}))
            )
            session.add(profile)
            session.flush() # Get profile ID

            # Migrate Transactions from various categories
            categories = ["car_rental", "mining", "farm_bp", "fishing", "transactions"]
            for cat in categories:
                tx_list = []
                if cat == "transactions":
                    tx_list = p_data.get("transactions", [])
                else:
                    cat_data = p_data.get(cat, {})
                    if isinstance(cat_data, dict):
                        tx_list = cat_data.get("transactions", [])
                    elif isinstance(cat_data, list):
                        tx_list = cat_data

                for tx_item in tx_list:
                    # Parse date
                    date_str = tx_item.get("date") or tx_item.get("timestamp")
                    try:
                        if date_str:
                            if "." in date_str:
                                dt = datetime.strptime(date_str, "%d.%m.%Y")
                            elif "-" in date_str:
                                dt = datetime.strptime(date_str, "%Y-%m-%d")
                            else:
                                dt = datetime.utcnow()
                        else:
                            dt = datetime.utcnow()
                    except ValueError:
                        dt = datetime.utcnow()

                    # Determine type (income/expense)
                    amount = float(tx_item.get("amount", 0) or tx_item.get("profit", 0) or tx_item.get("price", 0))
                    tx_type = "income" if amount >= 0 else "expense"
                    
                    # Create Transaction
                    new_tx = Transaction(
                        timestamp=dt,
                        type=tx_type,
                        module=cat if cat != "transactions" else tx_item.get("module"),
                        amount=abs(amount),
                        category=tx_item.get("category"),
                        note=tx_item.get("note") or tx_item.get("comment") or tx_item.get("name"),
                    )
                    session.add(new_tx)

            # Migrate Assets (from clothes, cars_trade, etc.)
            asset_categories = ["clothes", "clothes_new", "cars_trade"]
            for cat in asset_categories:
                inventory = p_data.get(cat, {}).get("inventory", [])
                for item in inventory:
                    asset = Asset(
                        type=cat,
                        name=item.get("name", "Unknown"),
                        purchase_price=float(item.get("buy_price", 0) or item.get("purchase_price", 0) or 0),
                        purchase_date=datetime.utcnow(), # Default to now if not available
                        current_value=float(item.get("buy_price", 0) or item.get("purchase_price", 0) or 0),
                        is_active=True
                    )
                    session.add(asset)

        session.commit()
        print("Migration completed successfully!")
    except Exception as e:
        session.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    # Get the data.json path from environment or default
    app_data = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
    json_path = os.path.join(app_data, "MoneyTracker", "data.json")
    
    # Check local path first (portable mode)
    if os.path.exists("data.json"):
        json_path = "data.json"
        
    migrate_json_to_sqlite(json_path)
