
import sys
import os
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import subprocess

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Установка MoneyTracker")
        self.root.geometry("500x350")
        self.root.resizable(False, False)
        
        # Center window
        self.center_window()
        
        # Default install path
        self.install_path = tk.StringVar(value=os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'MoneyTracker'))
        
        self.setup_ui()
        
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#f0f0f0", height=60)
        header_frame.pack(fill="x")
        
        title_label = tk.Label(header_frame, text="Мастер установки MoneyTracker", font=("Segoe UI", 14, "bold"), bg="#f0f0f0")
        title_label.pack(pady=15)
        
        # Content
        content_frame = tk.Frame(self.root, padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        tk.Label(content_frame, text="Выберите папку для установки:", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 5))
        
        # Path selection
        path_frame = tk.Frame(content_frame)
        path_frame.pack(fill="x", pady=(0, 20))
        
        self.path_entry = tk.Entry(path_frame, textvariable=self.install_path, font=("Segoe UI", 10))
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_btn = tk.Button(path_frame, text="Обзор...", command=self.browse_folder)
        browse_btn.pack(side="right")
        
        # Options
        self.create_shortcut_var = tk.BooleanVar(value=True)
        tk.Checkbutton(content_frame, text="Создать ярлык на рабочем столе", variable=self.create_shortcut_var, font=("Segoe UI", 10)).pack(anchor="w")
        
        self.run_after_var = tk.BooleanVar(value=True)
        tk.Checkbutton(content_frame, text="Запустить после установки", variable=self.run_after_var, font=("Segoe UI", 10)).pack(anchor="w")
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(content_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=(20, 5))
        
        self.status_label = tk.Label(content_frame, text="Готов к установке", font=("Segoe UI", 9), fg="gray")
        self.status_label.pack(anchor="w")
        
        # Footer
        footer_frame = tk.Frame(self.root, height=50)
        footer_frame.pack(fill="x", side="bottom", pady=10)
        
        self.install_btn = tk.Button(footer_frame, text="Установить", command=self.start_installation, bg="#0078d4", fg="white", font=("Segoe UI", 10, "bold"), padx=20, pady=5)
        self.install_btn.pack(side="right", padx=20)
        
        tk.Button(footer_frame, text="Отмена", command=self.root.quit, padx=10).pack(side="right")

    def browse_folder(self):
        directory = filedialog.askdirectory(initialdir=self.install_path.get())
        if directory:
            self.install_path.set(os.path.join(directory, 'MoneyTracker'))

    def start_installation(self):
        self.install_btn.config(state="disabled")
        threading.Thread(target=self.install_process, daemon=True).start()

    def install_process(self):
        try:
            dest_dir = self.install_path.get()
            
            # Determine source zip path (handle bundled resource)
            if hasattr(sys, '_MEIPASS'):
                zip_path = os.path.join(sys._MEIPASS, "MoneyTracker_v8.zip")
            else:
                zip_path = "build/MoneyTracker_v8.zip"
            
            if not os.path.exists(zip_path):
                raise FileNotFoundError("Файл установки не найден (MoneyTracker_v8.zip)")

            self.status_label.config(text="Распаковка файлов...")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                
                for i, file in enumerate(file_list):
                    zip_ref.extract(file, dest_dir)
                    progress = (i / total_files) * 100
                    self.progress_var.set(progress)
                    self.root.update_idletasks()
            
            self.progress_var.set(100)
            
            if self.create_shortcut_var.get():
                self.status_label.config(text="Создание ярлыка...")
                self.create_shortcut(dest_dir)
            
            self.status_label.config(text="Установка завершена!")
            messagebox.showinfo("Успех", "Установка успешно завершена!")
            
            if self.run_after_var.get():
                exe_path = os.path.join(dest_dir, "MoneyTracker.exe")
                if os.path.exists(exe_path):
                    subprocess.Popen([exe_path], cwd=dest_dir)
            
            self.root.quit()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка установки:\n{str(e)}")
            self.install_btn.config(state="normal")
            self.status_label.config(text="Ошибка установки")

    def create_shortcut(self, target_dir):
        try:
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            target = os.path.join(target_dir, "MoneyTracker.exe")
            shortcut_path = os.path.join(desktop, "MoneyTracker.lnk")
            
            vbs_script = f"""
            Set oWS = WScript.CreateObject("WScript.Shell")
            sLinkFile = "{shortcut_path}"
            Set oLink = oWS.CreateShortcut(sLinkFile)
            oLink.TargetPath = "{target}"
            oLink.WorkingDirectory = "{target_dir}"
            oLink.IconLocation = "{target},0"
            oLink.Save
            """
            
            vbs_path = os.path.join(target_dir, "create_shortcut.vbs")
            with open(vbs_path, "w") as f:
                f.write(vbs_script)
            
            subprocess.run(["cscript", "//Nologo", vbs_path], check=True)
            os.remove(vbs_path)
            
        except Exception as e:
            print(f"Failed to create shortcut: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()
