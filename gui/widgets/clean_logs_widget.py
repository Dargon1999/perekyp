import os
import shutil
import time
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QTextEdit


@dataclass
class CleanResult:
    deleted_files: int
    deleted_dirs: int
    freed_bytes: int
    errors: int


class CleanWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    counters = pyqtSignal(int, int, int)
    finished_ok = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._stop = False

    def request_stop(self):
        self._stop = True

    def run(self):
        deleted_files = 0
        deleted_dirs = 0
        freed_bytes = 0
        errors = 0

        steps = self._build_steps()
        total = max(1, len(steps))

        self.log.emit("Запуск чистки…")
        for idx, step in enumerate(steps, start=1):
            if self._stop:
                self.log.emit("Остановлено пользователем.")
                break
            try:
                df, dd, fb = step()
                deleted_files += df
                deleted_dirs += dd
                freed_bytes += fb
            except Exception as e:
                errors += 1
                self.log.emit(f"Ошибка: {e}")
            self.counters.emit(deleted_files, deleted_dirs, freed_bytes)
            self.progress.emit(int(idx * 100 / total))

        res = CleanResult(deleted_files, deleted_dirs, freed_bytes, errors)
        self.finished_ok.emit(res)

    def _build_steps(self):
        steps = []

        temp_root = os.getenv("TEMP") or os.getenv("TMP") or ""
        app_temp = os.path.join(temp_root, "MoneyTracker_Bots")
        steps.append(lambda: self._clean_dir(app_temp, label="Temp: MoneyTracker_Bots"))

        local_tmp = os.path.join(temp_root, "MoneyTracker")
        steps.append(lambda: self._clean_dir(local_tmp, label="Temp: MoneyTracker"))

        steps.append(lambda: self._delete_tmp_files(temp_root))
        steps.append(lambda: self._recreate_dir(app_temp))

        return steps

    def _dir_size(self, path):
        total = 0
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total += os.path.getsize(fp)
                except Exception:
                    pass
        return total

    def _clean_dir(self, path, label):
        if not path or not os.path.exists(path):
            self.log.emit(f"{label}: нет папки")
            return 0, 0, 0

        self.log.emit(f"{label}: очистка")
        freed_before = self._dir_size(path)
        deleted_files = 0
        deleted_dirs = 0

        for root, dirs, files in os.walk(path, topdown=False):
            for f in files:
                if self._stop:
                    return deleted_files, deleted_dirs, 0
                fp = os.path.join(root, f)
                try:
                    os.remove(fp)
                    deleted_files += 1
                except Exception:
                    pass
            for d in dirs:
                if self._stop:
                    return deleted_files, deleted_dirs, 0
                dp = os.path.join(root, d)
                try:
                    os.rmdir(dp)
                    deleted_dirs += 1
                except Exception:
                    pass

        freed_after = self._dir_size(path)
        freed = max(0, freed_before - freed_after)
        self.log.emit(f"{label}: готово")
        return deleted_files, deleted_dirs, freed

    def _delete_tmp_files(self, root_dir):
        if not root_dir or not os.path.exists(root_dir):
            self.log.emit("*.tmp: нет TEMP")
            return 0, 0, 0

        self.log.emit("*.tmp: удаление рекурсивно (в TEMP)")
        deleted_files = 0
        freed = 0
        for root, _, files in os.walk(root_dir):
            for f in files:
                if self._stop:
                    return deleted_files, 0, freed
                if not f.lower().endswith(".tmp"):
                    continue
                fp = os.path.join(root, f)
                try:
                    freed += os.path.getsize(fp)
                except Exception:
                    pass
                try:
                    os.remove(fp)
                    deleted_files += 1
                except Exception:
                    pass
        self.log.emit("*.tmp: готово")
        return deleted_files, 0, freed

    def _recreate_dir(self, path):
        if not path:
            return 0, 0, 0
        self.log.emit("Temp: пересоздание папки")
        deleted_dirs = 0
        freed = 0
        if os.path.exists(path):
            try:
                freed = self._dir_size(path)
                shutil.rmtree(path, ignore_errors=True)
                deleted_dirs += 1
            except Exception:
                pass
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass
        self.log.emit("Temp: пересоздание готово")
        return 0, deleted_dirs, freed


class CleanLogsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._running = False

        self.setStyleSheet("""
            QWidget { background: transparent; color: #e5e7eb; }
            QTextEdit { background: rgba(15, 23, 42, 180); border: 1px solid rgba(148, 163, 184, 60); border-radius: 10px; padding: 8px; }
            QProgressBar { border: 1px solid rgba(148, 163, 184, 60); border-radius: 8px; background: rgba(15, 23, 42, 120); height: 16px; text-align: center; }
            QProgressBar::chunk { border-radius: 8px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #22c55e, stop:1 #3b82f6); }
            QPushButton { background: rgba(59, 130, 246, 200); border: 1px solid rgba(59, 130, 246, 220); border-radius: 10px; padding: 10px 14px; font-weight: 600; }
            QPushButton:hover { background: rgba(59, 130, 246, 235); }
            QPushButton:disabled { background: rgba(100, 116, 139, 140); border-color: rgba(100, 116, 139, 140); }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Чистка логов")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #f8fafc;")
        layout.addWidget(title)

        self.info = QLabel("F8 — запуск. Очищается только кэш/временные файлы приложения.")
        self.info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info.setStyleSheet("color: rgba(148, 163, 184, 220);")
        layout.addWidget(self.info)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        counters = QHBoxLayout()
        self.lbl_files = QLabel("Файлы: 0")
        self.lbl_dirs = QLabel("Папки: 0")
        self.lbl_size = QLabel("Освобождено: 0 MB")
        for w in (self.lbl_files, self.lbl_dirs, self.lbl_size):
            w.setStyleSheet("color: rgba(226, 232, 240, 220); font-weight: 600;")
        counters.addWidget(self.lbl_files)
        counters.addWidget(self.lbl_dirs)
        counters.addWidget(self.lbl_size)
        layout.addLayout(counters)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Запустить")
        self.btn_start.clicked.connect(self.start_cleaning)
        self.btn_stop = QPushButton("Стоп")
        self.btn_stop.clicked.connect(self.stop_cleaning)
        self.btn_stop.setEnabled(False)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box, 1)

    def start_cleaning(self):
        if self._running:
            return
        self._running = True
        self.progress.setValue(0)
        self.log_box.clear()
        self._set_buttons()

        self._worker = CleanWorker()
        self._worker.progress.connect(self.progress.setValue)
        self._worker.log.connect(self._append_log)
        self._worker.counters.connect(self._update_counters)
        self._worker.finished_ok.connect(self._finish)
        self._worker.start()

    def stop_cleaning(self):
        if self._worker:
            self._worker.request_stop()

    def _append_log(self, msg):
        t = time.strftime("%H:%M:%S")
        self.log_box.append(f"[{t}] {msg}")

    def _update_counters(self, files, dirs, freed_bytes):
        self.lbl_files.setText(f"Файлы: {files}")
        self.lbl_dirs.setText(f"Папки: {dirs}")
        self.lbl_size.setText(f"Освобождено: {freed_bytes / (1024 * 1024):.1f} MB")

    def _finish(self, res):
        self._running = False
        self._set_buttons()
        self.progress.setValue(100)
        self._append_log(
            f"Готово. Файлы: {res.deleted_files}, папки: {res.deleted_dirs}, ошибок: {res.errors}, освобождено: {res.freed_bytes / (1024 * 1024):.1f} MB"
        )

    def _set_buttons(self):
        self.btn_start.setEnabled(not self._running)
        self.btn_stop.setEnabled(self._running)

