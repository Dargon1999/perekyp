import logging

class FishingPlugin:
    def __init__(self, context):
        self.db = context.get("db")
        self.data = context.get("data")
        self.event_bus = context.get("event_bus")
        
        # Subscribe to UI events
        self.event_bus.event_emitted.connect(self.on_event)

    def on_event(self, event_name, data):
        if event_name == "catch_button_clicked":
            self.catch_fish(data.get("name"), data.get("profit"))

    def catch_fish(self, fish_name, profit):
        logging.info(f"Fishing: Caught {fish_name} for {profit}$")
        
        # Add to ledger
        tx_id = self.db.add_transaction(
            type="income",
            amount=profit,
            module="fishing",
            category="Catch",
            note=f"Caught {fish_name}"
        )
        
        # Emit event
        self.event_bus.emit("transaction_added", {
            "id": tx_id,
            "amount": profit,
            "module": "fishing",
            "note": f"Caught {fish_name}"
        })
        self.event_bus.emit("fish_caught", {"name": fish_name, "profit": profit})

def initialize(context):
    return FishingPlugin(context)
