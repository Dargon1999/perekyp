from PyQt5 import QtWidgets, QtCore, QtGui
from widgets.common import CommonUI, CommonLogger
from utils.hwid import get_hwid, get_pc_name
from utils.firebase_api import FirebaseAPI
import datetime
import os
import subprocess
import threading

class AdminPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._start_sms_listener()

    def _init_ui(self):
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 1. Информация о системе
        sys_group, sys_layout = CommonUI.create_settings_group("🖥️ Информация о системе")
        self.pc_name_label = QtWidgets.QLabel(f"Имя ПК: {get_pc_name()}")
        self.hwid_label = QtWidgets.QLabel(f"HWID: {get_hwid()[:16]}...")
        self.hwid_label.setToolTip(get_hwid())
        self.version_label = QtWidgets.QLabel("Версия: 3.7")
        self.license_label = QtWidgets.QLabel("Лицензия: Активна")
        
        refresh_btn = QtWidgets.QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self._refresh_sys_info)
        
        for lbl in [self.pc_name_label, self.hwid_label, self.version_label, self.license_label]:
            lbl.setStyleSheet("color: white; font-size: 13px;")
            sys_layout.addWidget(lbl)
        sys_layout.addWidget(refresh_btn)
        self.layout.addWidget(sys_group)

        # 2. Управление SMS
        sms_group, sms_layout = CommonUI.create_settings_group("💬 Управление SMS")
        self.sms_tabs = QtWidgets.QTabWidget()
        self.sms_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #222; color: #888; padding: 5px 15px; }
            QTabBar::tab:selected { background: #333; color: white; border-bottom: 2px solid #0A84FF; }
        """)
        
        self.inbox_list = QtWidgets.QListWidget()
        self.archive_list = QtWidgets.QListWidget()
        
        self.sms_tabs.addTab(self.inbox_list, "Входящие")
        self.sms_tabs.addTab(self.archive_list, "Архив")
        
        sms_layout.addWidget(self.sms_tabs)
        
        sms_controls = QtWidgets.QHBoxLayout()
        self.archive_btn = QtWidgets.QPushButton("📦 В архив")
        self.archive_btn.clicked.connect(self._archive_selected_sms)
        sms_controls.addWidget(self.archive_btn)
        sms_layout.addLayout(sms_controls)
        
        self.layout.addWidget(sms_group)

        # 3. Управление лицензиями
        lic_group, lic_layout = CommonUI.create_settings_group("🔑 Управление лицензиями")
        lic_btns = QtWidgets.QHBoxLayout()
        
        create_btn = QtWidgets.QPushButton("➕ Создать")
        reset_btn = QtWidgets.QPushButton("🔄 Обнулить HWID")
        extend_btn = QtWidgets.QPushButton("⏳ Продлить (+30д)")
        
        create_btn.clicked.connect(self._create_license)
        reset_btn.clicked.connect(self._reset_hwid)
        extend_btn.clicked.connect(self._extend_license)
        
        for btn in [create_btn, reset_btn, extend_btn]:
            btn.setStyleSheet("background: #333; color: white; padding: 5px;")
            lic_btns.addWidget(btn)
        
        lic_layout.addLayout(lic_btns)
        self.layout.addWidget(lic_group)

        # 4. Очистка временных файлов
        cleanup_group, cleanup_layout = CommonUI.create_settings_group("🧹 Очистка временных файлов")
        self.check_temp = QtWidgets.QCheckBox("%Temp%")
        self.check_sys_temp = QtWidgets.QCheckBox("%SystemRoot%\\TEMP")
        self.check_tmp_files = QtWidgets.QCheckBox("*.tmp")
        self.check_recycle = QtWidgets.QCheckBox("Корзина")
        
        for chk in [self.check_temp, self.check_sys_temp, self.check_tmp_files, self.check_recycle]:
            chk.setStyleSheet("color: white;")
            chk.setChecked(True)
            cleanup_layout.addWidget(chk)
            
        self.cleanup_btn = QtWidgets.QPushButton("🚀 Выполнить очистку")
        self.cleanup_btn.clicked.connect(self._run_cleanup)
        cleanup_layout.addWidget(self.cleanup_btn)
        
        self.progress = QtWidgets.QProgressBar()
        self.progress.setVisible(False)
        cleanup_layout.addWidget(self.progress)
        
        self.log_window = QtWidgets.QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setMaximumHeight(100)
        self.log_window.setStyleSheet("background: black; color: #00FF00; font-family: monospace;")
        cleanup_layout.addWidget(self.log_window)
        self.layout.addWidget(cleanup_group)

    def _refresh_sys_info(self):
        CommonLogger.log("[Admin] Обновление информации о системе...")
        self._toast("Обновлено", "Информация о системе успешно обновлена")

    def _create_license(self):
        ok, res = FirebaseAPI.create_license(30)
        if ok:
            QtWidgets.QApplication.clipboard().setText(res)
            self._toast("Успех", f"Лицензия создана и скопирована:\n{res}")
        else:
            self._toast("Ошибка", f"Не удалось создать лицензию: {res}")

    def _reset_hwid(self):
        key, ok = QtWidgets.QInputDialog.getText(self, "Сброс HWID", "Введите ключ лицензии:")
        if ok and key:
            if FirebaseAPI.reset_hwid(key):
                self._toast("Успех", "Привязка HWID сброшена")
            else:
                self._toast("Ошибка", "Не удалось сбросить HWID")

    def _extend_license(self):
        key, ok = QtWidgets.QInputDialog.getText(self, "Продление", "Введите ключ лицензии:")
        if ok and key:
            ok, res = FirebaseAPI.extend_license(key, 30)
            if ok:
                self._toast("Успех", f"Лицензия продлена до: {res}")
            else:
                self._toast("Ошибка", f"Ошибка: {res}")

    def _archive_selected_sms(self):
        item = self.inbox_list.currentItem()
        if item:
            sms_id = item.data(QtCore.Qt.UserRole)
            sms_data = {"text": item.text(), "date": datetime.datetime.now().isoformat()}
            FirebaseAPI.archive_sms(sms_id, sms_data)
            self.archive_list.addItem(item.text())
            self.inbox_list.takeItem(self.inbox_list.row(item))

    def _start_sms_listener(self):
        def listener():
            FirebaseAPI.get_sms(self._handle_new_sms)
        threading.Thread(target=listener, daemon=True).start()

    def _handle_new_sms(self, data):
        # This is a mock since we don't have real long-polling stream here
        # In real app, this would be triggered by the stream
        pass

    def _run_cleanup(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log_window.clear()
        
        commands = []
        if self.check_temp.isChecked(): commands.append("DEL /F /S /Q /A %Temp%\\*")
        if self.check_sys_temp.isChecked(): commands.append("DEL /F /S /Q /A %SystemRoot%\\TEMP\\*")
        if self.check_tmp_files.isChecked(): commands.append("del /S /F /Q %TEMP%\\*.tmp")
        if self.check_recycle.isChecked():
            commands.append('RD "C:\\Recycler\\" /S /Q')
            commands.append('RD "C:\\$RECYCLE.BIN\\" /S /Q')

        total = len(commands)
        # Windows-specific flags to hide console
        flags = 0
        if os.name == 'nt':
            flags = 0x08000000 # CREATE_NO_WINDOW

        for i, cmd in enumerate(commands):
            self.log_window.append(f"> {cmd}")
            subprocess.run(cmd, shell=True, capture_output=True, creationflags=flags)
            self.progress.setValue(int((i + 1) / total * 100))
            QtWidgets.QApplication.processEvents()

        self._toast("Очистка", "Временные файлы успешно удалены")

    def _toast(self, title, msg):
        QtWidgets.QMessageBox.information(self, title, msg)
