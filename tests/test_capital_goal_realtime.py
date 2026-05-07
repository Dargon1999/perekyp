import types
from gui.tabs.capital_planning_tab import CapitalPlanningTab

class DummyDM:
    def __init__(self):
        self._stats = {}
        self._tx = {"fishing": []}
        self._planning = {"target_amount": 100000}
    def get_category_stats(self, cat):
        return self._stats.get(cat)
    def get_transactions(self, category):
        return self._tx.get(category, [])
    def get_capital_planning_data(self):
        return self._planning
    def update_capital_planning_data(self, data):
        self._planning = data

def test_compute_tabs_profit_basic(qtbot):
    dm = DummyDM()
    # car rental: income 40k, expense 10k => 30k
    dm._stats["car_rental"] = {"income": 40000, "expenses": 10000}
    # mining: 25k - 5k => 20k
    dm._stats["mining"] = {"income": 25000, "expenses": 5000}
    # clothes: 30k - 12k => 18k
    dm._stats["clothes"] = {"income": 30000, "expenses": 12000}
    # fishing: +7k, -2k => 5k
    dm._tx["fishing"] = [{"amount": 7000}, {"amount": -2000}]
    w = CapitalPlanningTab(dm, None)
    profit = w.compute_tabs_profit()
    assert profit == 30000 + 20000 + 18000 + 5000

def test_update_realtime_goal_reaches_target(qtbot):
    dm = DummyDM()
    dm._planning = {"target_amount": 50000}
    dm._stats["car_rental"] = {"income": 30000, "expenses": 0}
    dm._stats["mining"] = {"income": 25000, "expenses": 0}
    dm._tx["fishing"] = []
    w = CapitalPlanningTab(dm, None)
    w.update_realtime_goal()
    # Remaining should be 0, progress 100
    assert "Осталось: $0" in w.lbl_remaining.text()
    assert w.progress_bar.value() == 100

def test_negative_protection(qtbot):
    dm = DummyDM()
    dm._planning = {"target_amount": 10000}
    dm._stats["car_rental"] = {"income": 50000, "expenses": 0}
    w = CapitalPlanningTab(dm, None)
    w.update_realtime_goal()
    assert "Осталось: $0" in w.lbl_remaining.text()
    assert w.progress_bar.value() == 100
