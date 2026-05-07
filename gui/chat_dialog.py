from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QTextEdit, QLineEdit, QScrollArea, QWidget, QComboBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import os
import json
import requests
from gui.styles import StyleManager
from gui.key_manager import KeyManager
import logging

class ChatDialog(QDialog):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Чат ИИ")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(720, 540)
        self.data_manager = data_manager
        self.key_manager = KeyManager(self.data_manager)
        self.current_theme = "dark"
        self.logger = logging.getLogger(__name__)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(10)
        top = QHBoxLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Авто"])
        self.model_combo = QComboBox()
        self.model_combo.addItems(["Авто"])
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("API ключ (хранится шифрованно)")
        self.save_key_btn = QPushButton("Сохранить ключ")
        self.save_key_btn.clicked.connect(self.save_key)
        top.addWidget(QLabel("Провайдер/Модель: Авто"))
        top.addWidget(self.key_input)
        top.addWidget(self.save_key_btn)
        self.layout.addLayout(top)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.msg_layout = QVBoxLayout(self.scroll_content)
        self.msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
        input_row = QHBoxLayout()
        self.input = QTextEdit()
        self.input.setFixedHeight(80)
        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self.on_send)
        input_row.addWidget(self.input)
        input_row.addWidget(self.send_btn)
        self.layout.addLayout(input_row)
        self.key_manager.ensure_preloaded_keys()
        self.load_key()
        self.apply_theme(self.current_theme)
        # Preload cached best combo
        self.cached_combo = self._load_cached_combo()

    def _load_cached_combo(self):
        try:
            raw = self.data_manager.get_global_data("ai_best_combo", "")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def apply_theme(self, theme_name):
        t = StyleManager.get_theme(theme_name)
        self.setStyleSheet(f"QDialog{{background-color:{t['bg_secondary']};border:1px solid {t['border']};border-radius:8px;}}")
        self.input.setStyleSheet(f"QTextEdit{{background-color:{t['input_bg']};border:1px solid {t['border']};color:{t['text_main']};}}")
        self.key_input.setStyleSheet(f"QLineEdit{{background-color:{t['input_bg']};border:1px solid {t['border']};color:{t['text_main']};}}")

    def add_message(self, role, text):
        frame = QFrame()
        l = QVBoxLayout(frame)
        l.setContentsMargins(8, 8, 8, 8)
        l.addWidget(QLabel("Ты" if role == "user" else "ИИ"))
        body = QLabel(text)
        body.setWordWrap(True)
        l.addWidget(body)
        self.msg_layout.addWidget(frame)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def on_send(self):
        prompt = self.input.toPlainText().strip()
        if not prompt:
            return
        self.add_message("user", prompt)
        self.input.clear()
        try:
            reply = self.send_with_auto(prompt)
            self.add_message("assistant", reply)
        except Exception as e:
            self.add_message("assistant", f"Ошибка: {e}")

    def save_key(self):
        key = self.key_input.text().strip()
        if not key:
            return
        prov = self.provider_combo.currentText().lower()
        self.data_manager.save_secure_value(f"{prov}_api_key", key)

    def load_key(self):
        prov = (self.provider_combo.currentText().lower() if self.provider_combo.currentText() != "Авто" else "openai")
        auto_key = self.key_manager.get_key(prov)
        if auto_key:
            self.key_input.setText(auto_key)

    def _extract_text(self, j):
        # Handle 'choices' and potential misspelling 'chioses'
        arr = j.get("choices") or j.get("chioses")
        if isinstance(arr, list) and arr:
            msg = arr[0].get("message", {})
            if isinstance(msg, dict):
                return msg.get("content", "")
        return ""

    def call_provider(self, prompt, prov, model):
        key = self.key_input.text().strip() or self.key_manager.get_key(prov.lower())
        self.logger.info(f"AI request via {prov}/{model}")
        if prov.lower() == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            if r.status_code == 429:
                raise Exception("Rate limit")
            if r.status_code >= 500:
                raise Exception(f"Server error {r.status_code}")
            j = r.json()
            return self._extract_text(j)
        elif prov.lower() == "deepseek":
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
            try:
                r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
                if r.status_code == 429:
                    raise Exception("Rate limit")
                if r.status_code >= 500:
                    raise Exception(f"Server error {r.status_code}")
                j = r.json()
                # Check for API errors in response
                if "error" in j:
                    err_msg = j["error"].get("message", str(j["error"]))
                    raise Exception(f"DeepSeek API Error: {err_msg}")
                return self._extract_text(j)
            except requests.exceptions.RequestException as req_err:
                raise Exception(f"Network error: {req_err}")
        return "Провайдер не поддерживается"

    def call_provider_with_rotation(self, prompt, prov, model):
        try:
            return self.call_provider(prompt, prov, model)
        except Exception as e:
            # Try rotate on authorization errors
            if "401" in str(e) or "unauthorized" in str(e).lower():
                nk = self.key_manager.rotate_key(prov)
                if nk:
                    self.key_input.setText(nk)
                    return self.call_provider(prompt, prov, model)
            # Rate limit fallback to next key
            if "rate limit" in str(e).lower():
                nk = self.key_manager.rotate_key(prov)
                if nk:
                    self.key_input.setText(nk)
                    return self.call_provider(prompt, prov, model)
            raise

    def send_with_auto(self, prompt):
        # Provider/model pools
        providers = ["openai", "deepseek"]
        models = {
            "openai": ["gpt-4o-mini", "gpt-4o"],
            "deepseek": ["deepseek-chat"]
        }
        # Use cached combo first
        if self.cached_combo:
            p = self.cached_combo.get("provider")
            m = self.cached_combo.get("model")
            if p and m and self.key_manager.get_key(p):
                try:
                    resp = self.call_provider_with_rotation(prompt, p, m)
                    # Refresh cache hit count
                    self._cache_combo(p, m)
                    return resp
                except Exception as e:
                    self.logger.error(f"Cached combo failed: {e}")
        # Probe providers/models
        for p in providers:
            if not self.key_manager.get_key(p):
                self.logger.warning(f"No key for {p}, skipping")
                continue
            for m in models[p]:
                try:
                    resp = self.call_provider_with_rotation(prompt, p, m)
                    self._cache_combo(p, m)
                    return resp
                except Exception as e:
                    self.logger.error(f"Combo {p}/{m} failed: {e}")
                    continue
        raise Exception("Нет доступных провайдеров или все недоступны")

    def _cache_combo(self, provider, model):
        try:
            combo = {"provider": provider, "model": model}
            self.data_manager.set_global_data("ai_best_combo", json.dumps(combo))
            self.cached_combo = combo
        except Exception as e:
            self.logger.error(f"Cache combo error: {e}")
