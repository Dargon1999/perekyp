import requests
import json
import logging
import os
import sys
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QSystemTrayIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl

class NotificationManager(QObject):
    """
    Centralized notification management system.
    Supports tray icons, audio, queueing, and external channels (Discord).
    """
    notification_triggered = pyqtSignal(str, str, str) # title, message, level

    def __init__(self, tray_icon=None, parent=None):
        super().__init__(parent)
        self.tray_icon = tray_icon
        self.queue = []
        self._is_processing = False
        self._lock = threading.Lock()
        
        # External channel config (Example: Discord Webhook)
        self.discord_webhook_url = None 
        
        # Audio setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)
        
        self.sounds = {
            "info": "gui/assets/sounds/info.wav",
            "warning": "gui/assets/sounds/warning.wav",
            "error": "gui/assets/sounds/error.wav",
            "success": "gui/assets/sounds/success.wav"
        }

    def set_discord_webhook(self, url):
        self.discord_webhook_url = url

    def notify(self, title, message, level="info", sound=True, external=True, duration=None):
        """Send a notification with optional custom duration."""
        if duration is None:
            # Try to get from data manager if available
            if hasattr(self, 'data_manager'):
                duration = self.data_manager.get_global_data("notif_duration", 3)
            else:
                duration = 3

        with self._lock:
            self.queue.append({
                "title": title,
                "message": message,
                "level": level,
                "sound": sound,
                "external": external,
                "duration": duration * 1000,
                "timestamp": time.time()
            })
        
        logging.info(f"[Notification] {level.upper()}: {title} - {message}")
        
        if not self._is_processing:
            QTimer.singleShot(0, self._process_queue)

    def _process_queue(self):
        with self._lock:
            if not self.queue:
                self._is_processing = False
                return
            
            self._is_processing = True
            item = self.queue.pop(0)

        # 1. Tray Notification
        if self.tray_icon:
            icon = QSystemTrayIcon.MessageIcon.Information
            if item["level"] == "warning":
                icon = QSystemTrayIcon.MessageIcon.Warning
            elif item["level"] == "error":
                icon = QSystemTrayIcon.MessageIcon.Critical
            
            duration_ms = item.get("duration", 3000)
            self.tray_icon.showMessage(
                item["title"],
                item["message"],
                icon,
                duration_ms
            )

        # 2. Audio Feedback
        if item["sound"]:
            self.play_sound(item["level"])

        # 3. External Channel (Discord)
        if item["external"] and self.discord_webhook_url:
            threading.Thread(target=self._send_to_discord, args=(item,), daemon=True).start()

        # 4. Emit signal for UI layer
        self.notification_triggered.emit(item["title"], item["message"], item["level"])

        # Process next after a short delay to avoid overlapping
        QTimer.singleShot(500, self._process_queue)

    def _send_to_discord(self, item):
        """Send notification to Discord via Webhook."""
        if not self.discord_webhook_url: return
        
        try:
            color = 0x3498db # Blue
            if item["level"] == "warning": color = 0xf1c40f # Yellow
            elif item["level"] == "error": color = 0xe74c3c # Red
            elif item["level"] == "success": color = 0x2ecc71 # Green
            
            payload = {
                "embeds": [{
                    "title": item["title"],
                    "description": item["message"],
                    "color": color,
                    "footer": {"text": "MoneyTracker System Notification"},
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            requests.post(self.discord_webhook_url, json=payload, timeout=5)
        except Exception as e:
            logging.error(f"Failed to send Discord notification: {e}")

    def play_sound(self, level):
        """Play sound based on level with custom volume."""
        # Get volume from data manager
        vol = 70
        if hasattr(self, 'data_manager'):
            vol = self.data_manager.get_global_data("notif_volume", 70)
        
        if vol == 0: return # Muted
        
        sound_file = self.sounds.get(level)
        if sound_file and os.path.exists(sound_file):
            self.audio_output.setVolume(vol / 100.0)
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(sound_file)))
            self.player.play()
        else:
            # Fallback beep
            pass

    def set_tray_icon(self, tray_icon):
        self.tray_icon = tray_icon

from datetime import datetime
