import os
import shutil
import sys
import subprocess
from version import VERSION

def get_pyinstaller_path():
    return [sys.executable, '-m', 'PyInstaller']

def build_updater():
    print("\n--- Phase 1: Building updater.exe ---")
    pyinstaller_cmd = get_pyinstaller_path()
        
    # Build updater as a standalone EXE first
    cmd = [
        *pyinstaller_cmd,
        'updater.py',
        '--onefile',
        '--noconsole',
        '--name=updater',
        '--clean',
        '--distpath=dist_temp',
        '--workpath=build_temp_updater'
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("Updater build complete.")
    return os.path.abspath('dist_temp/updater.exe')

def build_main(updater_path):
    print("\n--- Phase 2: Building MoneyTracker.exe (Bundled) ---")
    
    if not os.path.exists(updater_path):
        print(f"Error: {updater_path} not found!")
        return

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
    
    # Bundle updater.exe INSIDE the main EXE
    # We add it as data so it's easily accessible in _MEIPASS
    add_data_args.append(f'--add-data={updater_path};.')

    pyinstaller_cmd = get_pyinstaller_path()

    dist_dir = f"Release_v{VERSION}"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir, exist_ok=True)

    cmd = [
        *pyinstaller_cmd,
        'main.py',
        '--onefile',
        '--noconsole',
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
    
    # Copy updater.exe to release folder too, just in case
    shutil.copy2(updater_path, os.path.join(dist_dir, 'updater.exe'))
    
    print(f"\n--- SUCCESS! ---")
    print(f"Bundled EXE is in: {dist_dir}/MoneyTracker.exe")
    print(f"Standalone updater is also in the same folder.")

if __name__ == "__main__":
    # Clean temp folders
    for d in ['dist_temp', 'build_temp_updater', 'build_temp_main']:
        if os.path.exists(d):
            try: shutil.rmtree(d)
            except: pass

    try:
        updater_exe = build_updater()
        build_main(updater_exe)
    except Exception as e:
        print(f"\nBUILD FAILED: {e}")
        sys.exit(1)
    finally:
        # Final cleanup of temp build files
        if os.path.exists('dist_temp'):
            shutil.rmtree('dist_temp')
