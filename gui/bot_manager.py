import time
import logging
import threading
import requests
import os
from PyQt6.QtCore import QObject, pyqtSignal

# Lazy imports to prevent startup failure if dependencies are missing
try:
    import mss
    import cv2
    import numpy as np
    import pydirectinput
    import keyboard
    import mouse
    HAS_BOT_DEPS = True
except ImportError as e:
    logging.error(f"Missing automation dependencies: {e}. Some bots will be disabled.")
    HAS_BOT_DEPS = False

# Ensure temp dir exists for downloads
TEMP_DIR = os.path.join(os.getenv("TEMP"), "MoneyTracker_Bots")
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

class BotBase(QObject):
    status_changed = pyqtSignal(bool, str) # is_running, status_text
    log_message = pyqtSignal(str)
    
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.running = False
        self.paused = False
        self.thread = None
        self._stop_event = threading.Event()

    def start(self):
        if not HAS_BOT_DEPS:
            self.log_message.emit(f"Ошибка: Не установлены библиотеки для {self.name} (mss, cv2 и др.)")
            return
            
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.status_changed.emit(True, "РАБОТАЕТ")
        self.log_message.emit(f"{self.name}: Запущен")

    def stop(self):
        if not self.running:
            return
        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        self.status_changed.emit(False, "ОСТАНОВЛЕН")
        self.log_message.emit(f"{self.name}: Остановлен")

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def _run_loop(self):
        raise NotImplementedError

    def download_image(self, url, filename):
        path = os.path.join(TEMP_DIR, filename)
        # Always try to download to ensure fresh file, unless offline
        try:
            self.log_message.emit(f"Проверка {filename}...")
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(response.content)
                # self.log_message.emit(f"Файл {filename} обновлен.")
            else:
                self.log_message.emit(f"Ошибка загрузки {filename}: {response.status_code}")
        except Exception:
            # If offline, use existing if available
            if not os.path.exists(path):
                self.log_message.emit(f"Нет файла {filename} и нет сети.")
        
        return path

    def find_image(self, sct, template_data, confidence=0.8, region=None):
        try:
            # template_data can be path or numpy array (preloaded)
            if isinstance(template_data, str):
                if not os.path.exists(template_data):
                    return False
                template = cv2.imread(template_data, cv2.IMREAD_COLOR)
            else:
                template = template_data
                
            if template is None:
                return False

            # Grab screen
            monitor = sct.monitors[1] # Primary monitor
            if region:
                monitor = region
            
            sct_img = sct.grab(monitor)
            img = np.array(sct_img)
            # Remove alpha channel if present
            img = img[:, :, :3]
            
            # Match
            res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val >= confidence:
                return True
            
            # Fallback: Try Grayscale Match if color match failed
            # This helps if colors are slightly off (e.g. night mode, shading)
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            res_gray = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            min_val_g, max_val_g, min_loc_g, max_loc_g = cv2.minMaxLoc(res_gray)
            
            if max_val_g >= confidence:
                return True
                
            return False
        except Exception as e:
            self.log_message.emit(f"CV Error: {e}")
            return False

# --- Specific Bots ---

class MiningBot(BotBase):
    def __init__(self):
        super().__init__("Шахта")
        self.target_color = (126, 211, 33) # RGB: 0x7ED321
        self.tolerance = 10
        self.search_area = {"top": 486, "left": 965, "width": 5, "height": 5}
        self._last_press_at = 0.0
        self.press_cooldown_s = 0.07
        self.tick_s = 0.01
        self.hold_s = 0.02

    def _run_loop(self):
        import pydirectinput
        pydirectinput.PAUSE = 0.0
        with mss.mss() as sct:
            while not self._stop_event.is_set():
                if self.paused:
                    time.sleep(0.5)
                    continue
                try:
                    img = sct.grab(self.search_area)
                    found = False
                    for y in range(img.height):
                        for x in range(img.width):
                            pixel = img.pixel(x, y) # (r, g, b)
                            if (abs(pixel[0] - self.target_color[0]) <= self.tolerance and
                                abs(pixel[1] - self.target_color[1]) <= self.tolerance and
                                abs(pixel[2] - self.target_color[2]) <= self.tolerance):
                                found = True
                                break
                        if found: break
                    
                    if found:
                        now = time.time()
                        if now - self._last_press_at >= self.press_cooldown_s:
                            self._last_press_at = now
                            self.log_message.emit("Индикатор! -> E")
                            pydirectinput.keyDown("e")
                            time.sleep(self.hold_s)
                            pydirectinput.keyUp("e")
                    time.sleep(self.tick_s)
                except Exception as e:
                    self.log_message.emit(f"Ошибка: {e}")
                    time.sleep(1)

class ConstructionBot(BotBase):
    def __init__(self):
        super().__init__("Стройка")
        self.images = [
            ("1.png", "https://raw.githubusercontent.com/Dargon1999/stroq/main/1.png", 'e'),
            ("2.png", "https://raw.githubusercontent.com/Dargon1999/stroq/main/2.png", 'f'),
            ("3.png", "https://raw.githubusercontent.com/Dargon1999/stroq/main/3.png", 'h'),
            ("4.png", "https://raw.githubusercontent.com/Dargon1999/stroq/main/4.png", 'y')
        ]
        self.templates = {}
        self.templates_gray = {}
        self.key_map = {"1.png": "e", "2.png": "f", "3.png": "h", "4.png": "y"}
        self._last_press_at = {}
        self._last_debug_at = 0.0

    def start(self):
        # Pre-download and load images into memory
        for name, url, key in self.images:
            path = self.download_image(url, name)
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_COLOR)
                if img is not None:
                    self.templates[name] = img
                    self.templates_gray[name] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        super().start()

    def _run_loop(self):
        import pydirectinput
        pydirectinput.PAUSE = 0.01 
        
        region = {"top": 500, "left": 900, "width": 100, "height": 100}
        check_order = ["1.png", "2.png", "3.png", "4.png"]
        threshold = 0.62
        min_gap = 0.03
        cooldown_s = 0.12
        hold_s = 0.05
        
        with mss.mss() as sct:
            while not self._stop_event.is_set():
                try:
                    grab = sct.grab(region)
                    frame_bgr = np.array(grab)[:, :, :3]
                    frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

                    scores = {}
                    for filename in check_order:
                        tpl = self.templates.get(filename)
                        tpl_g = self.templates_gray.get(filename)
                        if tpl is None or tpl_g is None:
                            continue
                        scores[filename] = self._match_score(frame_bgr, frame_gray, tpl, tpl_g)

                    if not scores:
                        time.sleep(0.1)
                        continue

                    best_file, best_score = max(scores.items(), key=lambda kv: kv[1])
                    second_score = sorted(scores.values(), reverse=True)[1] if len(scores) >= 2 else 0.0

                    now = time.time()
                    if now - self._last_debug_at >= 1.0:
                        self._last_debug_at = now
                        score_str = " | ".join(f"{k}:{scores[k]:.2f}" for k in check_order if k in scores)
                        self.log_message.emit(f"Скор: {score_str}")

                    if best_score < threshold or (best_score - second_score) < min_gap:
                        time.sleep(0.1)
                        continue

                    key = self.key_map.get(best_file)
                    if not key:
                        time.sleep(0.1)
                        continue

                    last_at = self._last_press_at.get(key, 0.0)
                    if now - last_at < cooldown_s:
                        time.sleep(0.05)
                        continue

                    self._last_press_at[key] = now
                    self.log_message.emit(f"Найдено {best_file} -> {key.upper()}")

                    pydirectinput.keyDown(key)
                    time.sleep(hold_s)
                    pydirectinput.keyUp(key)

                    time.sleep(0.08)
                except Exception as e:
                    self.log_message.emit(f"Ошибка стройки: {e}")
                    time.sleep(0.5)

    def _match_score(self, frame_bgr, frame_gray, template_bgr, template_gray):
        res = cv2.matchTemplate(frame_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
        _, max_val_c, _, _ = cv2.minMaxLoc(res)
        res_g = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val_g, _, _ = cv2.minMaxLoc(res_g)
        return float(max(max_val_c, max_val_g))

class GymBot(BotBase):
    def __init__(self):
        super().__init__("Качалка")
        self.res = {
            "tren": ("tren.png", "https://raw.githubusercontent.com/KocTo4ka228/Turma/main/tren.png"),
            "b": ("B.png", "https://raw.githubusercontent.com/KocTo4ka228/Turma/main/B.png")
        }
        self.paths = {}
        self.templates = {}
        self.templates_gray = {}
        self._last_debug_at = 0.0
        self._last_space_at = 0.0
        self.space_cfg = {
            "min_radius": 10,
            "max_radius": 70,
            "min_y_ratio": 0.55,
            "edge_margin": 6,
            "min_contrast": 12,
            "cooldown_s": 0.06,
            "hue_min": 35,
            "hue_max": 95,
            "sat_min": 70,
            "val_min": 70,
            "min_area": 120,
            "min_circularity": 0.55,
        }

    def start(self):
        for k, (name, url) in self.res.items():
            self.paths[k] = self.download_image(url, name)
            path = self.paths[k]
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_COLOR)
                if img is not None:
                    self.templates[k] = img
                    self.templates_gray[k] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        super().start()

    def _run_loop(self):
        import pydirectinput
        pydirectinput.PAUSE = 0.01

        zone_b = {"top": 900, "left": 800, "width": 400, "height": 200}
        zone_tren = {"top": 650, "left": 600, "width": 750, "height": 250}

        b_threshold = 0.55
        tren_threshold = 0.60
        space_hold_s = 0.02

        with mss.mss() as sct:
            while not self._stop_event.is_set():
                try:
                    tpl_b = self.templates.get("b")
                    tpl_b_g = self.templates_gray.get("b")
                    tpl_tren = self.templates.get("tren")
                    tpl_tren_g = self.templates_gray.get("tren")

                    if tpl_b is None or tpl_b_g is None or tpl_tren is None or tpl_tren_g is None:
                        self.log_message.emit("Качалка: нет шаблонов (проверь загрузку картинок)")
                        time.sleep(1.0)
                        continue

                    grab_b = sct.grab(zone_b)
                    frame_b = np.array(grab_b)[:, :, :3]
                    frame_b_g = cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY)
                    score_b = self._match_score(frame_b, frame_b_g, tpl_b, tpl_b_g)

                    grab_tr = sct.grab(zone_tren)
                    frame_tr = np.array(grab_tr)[:, :, :3]
                    frame_tr_g = cv2.cvtColor(frame_tr, cv2.COLOR_BGR2GRAY)
                    score_tr = self._match_score(frame_tr, frame_tr_g, tpl_tren, tpl_tren_g)

                    now = time.time()
                    if now - self._last_debug_at >= 1.0:
                        self._last_debug_at = now
                        self.log_message.emit(f"Качалка: B={score_b:.2f} | tren={score_tr:.2f}")

                    if score_b >= b_threshold:
                        self.log_message.emit("Найден B -> ожидание 30с -> '-'")
                        for _ in range(300):
                            if self._stop_event.is_set():
                                break
                            time.sleep(0.1)
                        if self._stop_event.is_set():
                            continue
                        import keyboard
                        keyboard.send("sc12")
                        continue

                    if score_tr >= tren_threshold:
                        if now - self._last_space_at < float(self.space_cfg["cooldown_s"]):
                            time.sleep(0.01)
                            continue
                        self._last_space_at = now
                        self.log_message.emit("Тренажер -> Space")
                        pydirectinput.keyDown("space")
                        time.sleep(space_hold_s)
                        pydirectinput.keyUp("space")

                    time.sleep(0.03)
                except Exception as e:
                    self.log_message.emit(f"Ошибка качалки: {e}")
                    time.sleep(0.5)

    def _match_score(self, frame_bgr, frame_gray, template_bgr, template_gray):
        res = cv2.matchTemplate(frame_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
        _, max_val_c, _, _ = cv2.minMaxLoc(res)
        res_g = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val_g, _, _ = cv2.minMaxLoc(res_g)
        return float(max(max_val_c, max_val_g))

    def _find_valid_circles(self, frame_bgr, frame_gray):
        h, w = frame_gray.shape[:2]
        if h <= 0 or w <= 0:
            return []

        cfg = self.space_cfg
        min_radius = int(cfg.get("min_radius", 10))
        max_radius = int(cfg.get("max_radius", 70))
        if max_radius < min_radius:
            min_radius, max_radius = max_radius, min_radius

        min_y = int(h * float(cfg.get("min_y_ratio", 0.55)))
        edge_margin = int(cfg.get("edge_margin", 6))
        min_contrast = float(cfg.get("min_contrast", 12))

        green_circles = self._find_green_circles(
            frame_bgr,
            min_radius=min_radius,
            max_radius=max_radius,
            min_y=min_y,
            edge_margin=edge_margin,
            hue_min=int(cfg.get("hue_min", 35)),
            hue_max=int(cfg.get("hue_max", 95)),
            sat_min=int(cfg.get("sat_min", 70)),
            val_min=int(cfg.get("val_min", 70)),
            min_area=float(cfg.get("min_area", 120)),
            min_circularity=float(cfg.get("min_circularity", 0.55)),
        )
        if green_circles:
            return green_circles

        blur = cv2.GaussianBlur(frame_gray, (7, 7), 1.5)
        circles = cv2.HoughCircles(
            blur,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=20,
            param1=110,
            param2=24,
            minRadius=min_radius,
            maxRadius=max_radius,
        )
        if circles is None:
            return []

        circles = np.round(circles[0, :]).astype(int)
        return self._filter_circles(frame_gray, circles, min_y, edge_margin, min_contrast)

    def _filter_circles(self, frame_gray, circles, min_y, edge_margin, min_contrast):
        h, w = frame_gray.shape[:2]
        out = []
        for x, y, r in circles:
            if r <= 0:
                continue
            if y < min_y:
                continue
            if x < edge_margin or y < edge_margin or x >= (w - edge_margin) or y >= (h - edge_margin):
                continue
            if x - r < 0 or y - r < 0 or x + r >= w or y + r >= h:
                continue

            center_val = float(frame_gray[y, x])
            rr = max(1, int(r))
            d = int(rr * 0.707)
            pts = [
                (x + rr, y),
                (x - rr, y),
                (x, y + rr),
                (x, y - rr),
                (x + d, y + d),
                (x - d, y + d),
                (x + d, y - d),
                (x - d, y - d),
            ]
            ring_vals = [float(frame_gray[py, px]) for px, py in pts if 0 <= px < w and 0 <= py < h]
            if not ring_vals:
                continue
            ring_mean = float(sum(ring_vals) / len(ring_vals))
            if (ring_mean - center_val) < min_contrast:
                continue

            out.append((int(x), int(y), int(r)))

        out.sort(key=lambda c: c[2], reverse=True)
        return out

    def _find_green_circles(
        self,
        frame_bgr,
        min_radius,
        max_radius,
        min_y,
        edge_margin,
        hue_min,
        hue_max,
        sat_min,
        val_min,
        min_area,
        min_circularity,
    ):
        h, w = frame_bgr.shape[:2]
        if h <= 0 or w <= 0:
            return []

        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        lower = np.array([hue_min, sat_min, val_min], dtype=np.uint8)
        upper = np.array([hue_max, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            peri = cv2.arcLength(cnt, True)
            if peri <= 0:
                continue
            circularity = float(4.0 * np.pi * area / (peri * peri))
            if circularity < min_circularity:
                continue

            (x, y), r = cv2.minEnclosingCircle(cnt)
            x_i = int(round(x))
            y_i = int(round(y))
            r_i = int(round(r))

            if r_i < min_radius or r_i > max_radius:
                continue
            if y_i < min_y:
                continue
            if x_i < edge_margin or y_i < edge_margin or x_i >= (w - edge_margin) or y_i >= (h - edge_margin):
                continue
            if x_i - r_i < 0 or y_i - r_i < 0 or x_i + r_i >= w or y_i + r_i >= h:
                continue

            out.append((x_i, y_i, r_i))

        out.sort(key=lambda c: c[2], reverse=True)
        return out

class ChargeBot(BotBase):
    def __init__(self):
        super().__init__("Заряд")
        self.image_name = "gun.png"
        self.image_url = "https://raw.githubusercontent.com/script-help/resources_rp/main/gun.png"
        self.template = None
        self.template_gray = None

        self.cells = [
            {"x1": 1500, "y1": 275, "x2": 1500, "y2": 325},
            {"x1": 1580, "y1": 275, "x2": 1580, "y2": 325},
            {"x1": 1675, "y1": 275, "x2": 1675, "y2": 325},
            {"x1": 1765, "y1": 275, "x2": 1765, "y2": 325},
            {"x1": 1855, "y1": 275, "x2": 1855, "y2": 325},
            {"x1": 1500, "y1": 360, "x2": 1500, "y2": 425},
        ]

        self.search_region = {"left": 775, "top": 890, "width": 100, "height": 130}
        self.current_cell = 0
        self.waiting_for_disappear = False
        self._found_streak = 0
        self._not_found_streak = 0
        self._last_debug_at = 0.0

        self.main_period_s = 0.08
        self.check_period_s = 0.12
        self.click_sleep_s = 0.12
        self.cycle_sleep_s = 0.12
        self.appear_threshold = 0.52
        self.disappear_threshold = 0.47
        self.streak_needed = 2

    def start(self):
        path = self.download_image(self.image_url, self.image_name)
        if os.path.exists(path):
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                self.template = img
                self.template_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        self.current_cell = 0
        self.waiting_for_disappear = False
        self._found_streak = 0
        self._not_found_streak = 0
        self._last_debug_at = 0.0
        super().start()

    def _run_loop(self):
        import mouse
        import pydirectinput
        pydirectinput.PAUSE = 0.0

        if self.template is None or self.template_gray is None:
            self.log_message.emit("Заряд: не найден шаблон gun.png")
            return

        def right_click(x, y):
            mouse.move(x, y, absolute=True, duration=0)
            time.sleep(0.001)
            mouse.click("right")

        def left_click(x, y):
            mouse.move(x, y, absolute=True, duration=0)
            time.sleep(0.001)
            mouse.click("left")

        def perform_initial_actions(cell):
            right_click(cell["x1"], cell["y1"])
            time.sleep(0.05)
            right_click(1350, 275)

        def check_image_score(sct):
            try:
                grab = sct.grab(self.search_region)
                frame_bgr = np.array(grab)[:, :, :3]
                frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

                res = cv2.matchTemplate(frame_bgr, self.template, cv2.TM_CCOEFF_NORMED)
                _, max_val_c, _, _ = cv2.minMaxLoc(res)

                res_g = cv2.matchTemplate(frame_gray, self.template_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val_g, _, _ = cv2.minMaxLoc(res_g)

                return float(max(max_val_c, max_val_g))
            except Exception:
                return 0.0

        with mss.mss() as sct:
            perform_initial_actions(self.cells[self.current_cell])
            self.log_message.emit(f"Ячейка: {self.current_cell + 1} / {len(self.cells)}")

            last_main = 0.0
            last_check = 0.0
            while not self._stop_event.is_set():
                now = time.monotonic()

                if now - last_check >= self.check_period_s:
                    last_check = now
                    score = check_image_score(sct)
                    found = score >= self.appear_threshold
                    gone = score < self.disappear_threshold

                    if time.monotonic() - self._last_debug_at >= 1.0:
                        self._last_debug_at = time.monotonic()
                        state = "WAIT" if self.waiting_for_disappear else "RUN"
                        self.log_message.emit(f"{state} slot {self.current_cell + 1}/6 | gun={score:.2f}")

                    if self.waiting_for_disappear:
                        if gone:
                            self._not_found_streak += 1
                        else:
                            self._not_found_streak = 0

                        if self._not_found_streak >= self.streak_needed:
                            self.waiting_for_disappear = False
                            self._not_found_streak = 0
                            self._found_streak = 0
                            self.current_cell += 1

                            if self.current_cell >= len(self.cells):
                                self.log_message.emit("ГОТОВО -> ESC")
                                pydirectinput.press("esc")
                                time.sleep(0.3)
                                self.stop()
                                return

                            self.log_message.emit(f"Ячейка: {self.current_cell + 1} / {len(self.cells)}")
                            perform_initial_actions(self.cells[self.current_cell])
                    else:
                        if found:
                            self._found_streak += 1
                        else:
                            self._found_streak = 0

                        if self._found_streak >= self.streak_needed:
                            self._found_streak = 0
                            self._not_found_streak = 0
                            self.log_message.emit("Найден gun.png -> ожидание исчезновения")
                            self.waiting_for_disappear = True

                if not self.waiting_for_disappear and now - last_main >= self.main_period_s:
                    last_main = now
                    cell = self.cells[self.current_cell]
                    left_click(cell["x1"], cell["y1"])
                    time.sleep(self.click_sleep_s)
                    left_click(cell["x2"], cell["y2"])
                    time.sleep(self.click_sleep_s)
                    time.sleep(self.cycle_sleep_s)

                time.sleep(0.01)

class BeeperBot(BotBase):
    def __init__(self):
        super().__init__("Мотоклуб")
    
    def _run_loop(self):
        while not self._stop_event.is_set():
            # Wait 8 sec
            for _ in range(80):
                if self._stop_event.is_set(): return
                time.sleep(0.1)
            
            self.log_message.emit("Зажим E (3 сек)")
            import keyboard
            keyboard.press('e')
            
            # Wait 3 sec
            for _ in range(30):
                if self._stop_event.is_set(): 
                    keyboard.release('e')
                    return
                time.sleep(0.1)
            
            keyboard.release('e')

class FoodBot(BotBase):
    def __init__(self):
        super().__init__("Смузи")
        
    def _run_loop(self):
        # Click sequence
        import mouse
        
        while not self._stop_event.is_set():
            # 1. Click Vegetables (1080, 289) - Right Click
            self.log_message.emit("Овощи (R-Click)")
            mouse.move(1080, 289, absolute=True, duration=0)
            time.sleep(0.05)
            mouse.click('right')
            time.sleep(0.05)

            # 2. Click Water (1166, 287) - Right Click
            self.log_message.emit("Вода (R-Click)")
            mouse.move(1166, 287, absolute=True, duration=0)
            time.sleep(0.05)
            mouse.click('right')
            time.sleep(0.05)

            # 3. Click Whisk (815, 582) - Right Click
            self.log_message.emit("Венчик (R-Click)")
            mouse.move(815, 582, absolute=True, duration=0)
            time.sleep(0.05)
            mouse.click('right')
            time.sleep(0.05)

            # 4. Start Craft (816, 672) - Left Click
            self.log_message.emit("Крафт (L-Click)")
            mouse.move(816, 672, absolute=True, duration=0)
            mouse.click('left')
            
            # Wait 5 seconds
            for _ in range(50):
                if self._stop_event.is_set(): return
                time.sleep(0.1)
