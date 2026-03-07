from PyQt5 import QtWidgets, QtCore
import time
import keyboard
import cv2
import numpy as np
import mss
import os
from pynput.keyboard import Controller
from widgets.common import CommonLogger, ScriptController, HotkeyManager, SettingsManager, auto_detect_region, load_images, CommonUI, CheckWithTooltip
import threading

class CowPage(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.worker: CowWorker | None = None
        self.settings = SettingsManager()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        header, self.switch = CommonUI.create_switch_header("Коровы", "🐄")
        self.switch.clicked.connect(self.handle_toggle)
        self.switch.clicked.connect(self.statusChanged.emit)
        layout.addLayout(header)

        settings_group, settings_layout = CommonUI.create_settings_group()

        hotkey_layout, self.hotkey_input = CommonUI.create_hotkey_input(default="f5", description="— вкл/выкл автонажатие E")
        pause_layout, self.pause_slider, self.get_pause_slider = CommonUI.create_slider_row("Пауза между действиями:", minimum=0.05, maximum=2.0, default=0.07, suffix="сек", step=0.01)
        self.autosearch = CheckWithTooltip("Автопоиск коров", tooltip_text="Искать коров в зоне и автоматически начинать взаимодействие (E)")
        self.autoretry = CheckWithTooltip("Автоповтор", tooltip_text="После завершения доения вернуться к поиску коровы")

        self.counter_label = CommonUI.create_counter()

        settings_layout.addLayout(hotkey_layout)
        settings_layout.addLayout(pause_layout)
        settings_layout.addWidget(self.autosearch)
        settings_layout.addWidget(self.autoretry)
        settings_layout.addWidget(self.counter_label)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        self.log_output = CommonUI.add_log_field(layout)
        
    def _load_settings(self):
        self.hotkey_input.setText(self.settings.get("cow", "hotkey_port", "f5"))
        self.pause_slider.setValue(self.settings.get("cow", "pause", 0.07))
        self.autosearch.setChecked(self.settings.get("cow", "autosearch", True))
        self.autoretry.setChecked(self.settings.get("cow", "autoretry", True))

    def _save_settings(self):
        self.settings.save_group("cow", {
            "pause": self.pause_slider.value(),
            "hotkey_port": self.hotkey_input.text(),
            "autosearch": self.autosearch.isChecked(),
            "autoretry": self.autoretry.isChecked()
        })

    def handle_toggle(self):
        self._save_settings()
        ScriptController.toggle_script(
            widget=self,
            worker_factory=CowWorker,
            log_output=self.log_output,
            extra_signals={"counter_signal": self._update_counter},
            worker_kwargs={
                "hotkey": self.hotkey_input.text().strip() or 'f5',
                "pause_delay": self.pause_slider.value(),
                "autosearch": self.autosearch.isChecked(),
                "autoretry": self.autoretry.isChecked()
            }
        )

    def _update_counter(self, value: int):
        self.counter_label.setText(f"Счётчик: {value}")

class CowWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    counter_signal = QtCore.pyqtSignal(int)

    def __init__(self, hotkey: str = 'f5', pause_delay: float = 0.07, autosearch: bool = True, autoretry: bool = True):
        super().__init__()
        self.running = True
        self._count = 0
        try:
            cv2.setUseOptimized(True)
            cv2.setNumThreads(max(1, os.cpu_count() - 1))
        except Exception:
            pass
        self.templates = load_images(
            "cow",
            mapping={
                "1.png": "1",
                "2.png": "2",
                "3.png": "3",
                "cow.png": "cow"
            },
            as_cv2=True
        )
        self.monitor = auto_detect_region(width_ratio=1.0, height_ratio=0.65, top_ratio=0.35)
        self.pause_delay = pause_delay
        self._stop = threading.Event()
        self._auto_e_enabled = False
        self.min_press_interval = 0
        self._last_press_time = 0.0
        self.ui_update_every = 5
        self.keyboard_controller = Controller()
        self.hotkey_manager = HotkeyManager(
            hotkey=hotkey,
            toggle_callback=self._on_toggle_auto_e,
            log_signal=self.log_signal
        )
        self.autosearch = autosearch
        self.autoretry = autoretry
        self._in_minigame = False
        self._last_found_time = 0.0

    def _on_toggle_auto_e(self, enabled: bool):
        self._auto_e_enabled = enabled

    def log(self, message: str):
        CommonLogger.log(message, self.log_signal)

    def run(self):
        self.hotkey_manager.register()
        with mss.mss() as sct:
            self.log("Скрипт коровы запущен.")
            self.log(f"Область поиска: {self.monitor}")

            try:
                while self.running and not self._stop.is_set():
                    frame = np.array(sct.grab(self.monitor))
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                    scores = {}
                    for key, template in self.templates.items():
                        res = cv2.matchTemplate(frame_rgb, template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        if max_val >= 0.91:
                            scores[key] = max_val

                    found = bool(scores)

                    if found:
                        now = time.time()
                        self._last_found_time = now
                        if "cow" in scores and self.autosearch and not self._in_minigame:
                            self.keyboard_controller.tap('e')
                            self.keyboard_controller.tap('у')
                            self._in_minigame = True
                            self.log("Обнаружена корова — начинаем взаимодействие (E)")
                        else:
                            if now - self._last_press_time >= self.min_press_interval:
                                if scores.get("1", -1) >= max(scores.get("2", -1), scores.get("3", -1)):
                                    self.keyboard_controller.tap('a')
                                    self.keyboard_controller.tap('ф')
                                elif scores.get("2", -1) >= max(scores.get("1", -1), scores.get("3", -1)):
                                    self.keyboard_controller.tap('d')
                                    self.keyboard_controller.tap('в')
                                else:
                                    self.keyboard_controller.tap('s')
                                    self.keyboard_controller.tap('ы')

                                self._last_press_time = now
                                self._count += 1
                                if self._count % self.ui_update_every == 0:
                                    self.counter_signal.emit(self._count)

                    elif self._auto_e_enabled:
                        self.keyboard_controller.tap('e')
                        self.keyboard_controller.tap('у')

                    # Если долго ничего не найдено и мы были в мини-игре — считаем цикл завершён
                    if self._in_minigame and (time.time() - self._last_found_time) > 3.0:
                        self._in_minigame = False
                        self.log("Процесс доения завершён")
                        self.counter_signal.emit(self._count)
                        if self.autoretry and self.autosearch:
                            self.log("Возврат к поиску следующей коровы")

                    if self.pause_delay > 0:
                        if self._stop.wait(self.pause_delay):
                            break

            except Exception as exc:
                self.log(f"[Ошибка потока] {str(exc)}")
            finally:
                self.hotkey_manager.unregister()
                self.stop()
