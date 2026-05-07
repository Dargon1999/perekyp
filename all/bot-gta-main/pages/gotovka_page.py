from PyQt5 import QtWidgets, QtCore
import pyautogui
import os
from widgets.common import CommonLogger, ScriptController, CommonUI
import threading
from inventory import IngredientInventory, load_cooking_config

BASE_ASSETS_PATH = "assets/cook/"

class GotovkaPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker: GotovkaWorker | None = None
        self.inventory = IngredientInventory()
        self.config = load_cooking_config()
        self._recipes = {r["name"]: [(s["asset"], s["action"]) for s in r.get("steps", [])] for r in self.config.get("recipes", [])}
        self._ingredients = self.config.get("ingredients", [])
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        header, self.switch = CommonUI.create_switch_header("Готовка", "🍜")
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        layout.addLayout(header)

        settings_group, settings_layout = CommonUI.create_settings_group()

        dish_layout, self.dish_combo = CommonUI.create_combo("Выберите блюдо:", list(self._recipes.keys()))
        cycles_layout = QtWidgets.QHBoxLayout()
        cycles_label = QtWidgets.QLabel("Циклов:")
        cycles_label.setStyleSheet("color: white;")
        self.cycles_spin = QtWidgets.QSpinBox()
        self.cycles_spin.setRange(1, 999)
        self.cycles_spin.setValue(1)
        cycles_layout.addWidget(cycles_label)
        cycles_layout.addWidget(self.cycles_spin)

        inv_group, inv_layout = CommonUI.create_settings_group()
        inv_group.setTitle("Инвентарь ингредиентов")
        self._inv_labels = {}
        for ing in self._ingredients:
            row = QtWidgets.QHBoxLayout()
            key = ing["key"]
            name = ing["name"]
            lbl = QtWidgets.QLabel(f"{name}: {self.inventory.get(key)}")
            lbl.setStyleSheet("color: white;")
            self._inv_labels[key] = lbl
            btn_add = QtWidgets.QPushButton("+")
            btn_sub = QtWidgets.QPushButton("–")
            btn_add.clicked.connect(lambda _, k=key: self._change_inv(k, +1))
            btn_sub.clicked.connect(lambda _, k=key: self._change_inv(k, -1))
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(btn_sub)
            row.addWidget(btn_add)
            inv_layout.addLayout(row)
        inv_group.setLayout(inv_layout)
        settings_layout.addLayout(dish_layout)

        settings_layout.addLayout(cycles_layout)
        settings_layout.addWidget(inv_group)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonUI.add_log_field(layout)


    def _change_inv(self, key: str, delta: int):
        if delta > 0:
            self.inventory.add(key, delta)
        else:
            self.inventory.use(key, -delta)
        if key in self._inv_labels:
            self._inv_labels[key].setText(f"{next((i['name'] for i in self._ingredients if i['key']==key), key)}: {self.inventory.get(key)}")
    def handle_toggle(self):
        selected_dish = self.dish_combo.currentText()
        ScriptController.toggle_script(
            widget=self,
            worker_factory=lambda: GotovkaWorker(selected_dish),
            worker_factory=lambda: GotovkaWorker(selected_dish, self._recipes.get(selected_dish, []), cycles=self.cycles_spin.value()),
        )

class GotovkaWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self, dish_name: str):
    def __init__(self, dish_name: str, steps: list[tuple[str, str]], cycles: int = 1):
        self._stop = threading.Event()
        self.running = True
        self.dish_name = dish_name
        self.confidence = 0.85
        self.cycles_count = 0
        self.cycles_count = 0
        self.steps = steps
    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def _find_and_perform_action(self, image_filename: str, click_type: str) -> bool:
        full_image_path = os.path.join(BASE_ASSETS_PATH, image_filename)
        try:
            location = pyautogui.locateCenterOnScreen(full_image_path, confidence=self.confidence)
            if location:
                if click_type == "right":
                    pyautogui.rightClick(location)
                    self.log(f"[✓] Использован/перетащен: {image_filename}.")
                elif click_type == "left":
                    pyautogui.click(location)
                    self.log(f"[✓] Клик по кнопке: {image_filename}.")
                return True
            else:
                self.log(f"[!] Изображение не найдено: {image_filename}.")
                return False
        except Exception as e:
            return False

    def _execute_recipe(self) -> bool:
        recipe_steps = RECIPES.get(self.dish_name)
        recipe_steps = self.steps
        for image_filename, action_type in recipe_steps:
                return False
            if not self._find_and_perform_action(image_filename, action_type):
                return False
            self._stop.wait(0.1)

        self.log(f"[✓] Все шаги для приготовления '{self.dish_name}' выполнены.")
        return True

    def run(self):
        self.log(f"[→] Скрипт готовки запущен для блюда: {self.dish_name}")
        rage_window_missing = True
        waiting_for_recipe_elements = False

        target_cycles = getattr(self, "cycles", 1)
        try:
            target_cycles = int(target_cycles)
        except Exception:
            target_cycles = 1
        try:
            while self.running:
                if not CommonLogger.is_rage_mp_active():
                if target_cycles and self.cycles_count >= target_cycles:
                    break
                    if not rage_window_missing:
                        self.log("[!] Окно RAGE Multiplayer не активно. Ожидание...")
                        rage_window_missing = True
                    self._stop.wait(1)
                    continue
                else:
                    if rage_window_missing:
                        self.log("[✓] Окно RAGE Multiplayer активно.")
                        rage_window_missing = False

                if self._execute_recipe():
                    self.cycles_count += 1
                    self.log(f"[✓] Цикл готовки №{self.cycles_count} для '{self.dish_name}' завершён.")
                    self.log("Ожидание перезарядки (5.5 секунд)...")
                    waiting_for_recipe_elements = False
                    self._stop.wait(5.5)
                else:
                    if not waiting_for_recipe_elements:
                        self.log(f"[!] Ожидание появления всех элементов для '{self.dish_name}'...")
                        waiting_for_recipe_elements = True
                    self._stop.wait(1)

        except Exception as exc:
            self.log(f"[Ошибка потока] {exc}")
        finally:
            if self.running:
                self.log("[■] Скрипт готовки завершён.")

