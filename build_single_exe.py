import os
import shutil
import sys
import subprocess
from version import VERSION

def get_pyinstaller_path():
    return [sys.executable, '-m', 'PyInstaller']

def build_main():
    print(f"\n--- Building MoneyTracker v{VERSION} (Single EXE) ---")
    
    assets_path = os.path.abspath('assets')
    icon_path = os.path.abspath('icon_v2.ico')
    if not os.path.exists(icon_path):
        icon_path = os.path.abspath('icon.ico')
        
    version_file = os.path.abspath('version_info.txt')
    gui_assets_path = os.path.abspath('gui/assets')

    # Essential files to bundle
    add_data_args = []
    
    if os.path.exists(assets_path):
        add_data_args.append(f'--add-data={assets_path};assets')
    
    if os.path.exists(icon_path):
        add_data_args.append(f'--add-data={icon_path};.')
        
    if os.path.exists(gui_assets_path):
         add_data_args.append(f'--add-data={gui_assets_path};gui/assets')
    
    # We no longer bundle updater.exe because we use an integrated PowerShell script

    pyinstaller_cmd = get_pyinstaller_path()
    dist_dir = f"Release_v{VERSION}_Single"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir, exist_ok=True)
    
    cmd = [
        *pyinstaller_cmd,
        'main.py',
        '--onefile',
        '--noconsole',
        '--noupx', 
        '--contents-directory=internal', # Put DLLs in a subfolder to avoid loading conflicts
        '--name=MoneyTracker',
        f'--icon={icon_path}' if os.path.exists(icon_path) else '',
        f'--version-file={version_file}' if os.path.exists(version_file) else '',
        *add_data_args,
        f'--distpath={dist_dir}',
        '--workpath=build_temp_main',
        '--clean',
        '--hidden-import=PyQt6.QtSvg',
        '--hidden-import=engineio.async_drivers.threading',
        '--hidden-import=flask_socketio',
        '--hidden-import=socketio',
        '--hidden-import=dns', 
        '--hidden-import=dns.resolver',
    ]
    
    # Remove empty strings from cmd
    cmd = [c for c in cmd if c]
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    print(f"\n--- SUCCESS! ---")
    print(f"Single self-updating EXE is in: {dist_dir}/MoneyTracker.exe")

if __name__ == "__main__":
    # Clean temp folders
    for d in ['build_temp_main']:
        if os.path.exists(d):
            try: shutil.rmtree(d)
            except: pass

    try:
        build_main()
    except Exception as e:
        print(f"\nBUILD FAILED: {e}")
        sys.exit(1)
