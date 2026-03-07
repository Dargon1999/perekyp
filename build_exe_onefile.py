import os
import shutil
import sys
import subprocess
from version import VERSION

def get_pyinstaller_path():
    return [sys.executable, '-m', 'PyInstaller']

def build_updater():
    print("Building updater.exe...")
    pyinstaller_cmd = get_pyinstaller_path()
        
    cmd = [
        *pyinstaller_cmd,
        'updater.py',
        '--onefile',
        '--noconsole',
        '--name=updater',
        '--clean',
        '--distpath=dist',
        '--workpath=build_updater',
        '--specpath=build_updater_spec'
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("Updater build complete.")

def build_main():
    print("Building MoneyTracker.exe...")
    
    updater_path = os.path.abspath('dist/updater.exe')
    if not os.path.exists(updater_path):
        print(f"Error: {updater_path} not found. Build updater first.")
        return

    assets_path = os.path.abspath('assets')
    icon_path = os.path.abspath('icon.ico')
    version_file = os.path.abspath('version_info.txt')
    gui_assets_path = os.path.abspath('gui/assets')

    add_data_args = [
        f'--add-data={assets_path};assets',
        f'--add-data={icon_path};.', 
        f'--add-binary={updater_path};.',
    ]

    if os.path.exists(gui_assets_path):
         add_data_args.append(f'--add-data={gui_assets_path};gui/assets')
    
    pyinstaller_cmd = get_pyinstaller_path()

    release_dir = f"Release_{VERSION}"
    cmd = [
        *pyinstaller_cmd,
        'main.py',
        '--onefile',
        '--noconsole',
        '--name=MoneyTracker',
        f'--icon={icon_path}',
        f'--version-file={version_file}',
        *add_data_args,
        f'--distpath={release_dir}',
        '--workpath=build_main',
        '--specpath=build_main_spec',
        '--hidden-import=engineio.async_drivers.threading',
        '--hidden-import=flask_socketio',
        '--hidden-import=socketio',
        '--hidden-import=dns', 
        '--hidden-import=dns.resolver',
        '--exclude-module=PyQt6.QtQuick',
        '--exclude-module=PyQt6.QtQml',
        '--exclude-module=PyQt6.QtPdf',
        '--exclude-module=PyQt6.QtVirtualKeyboard',
        '--exclude-module=PyQt6.QtTest',
        '--exclude-module=PyQt6.QtSensors',
        '--exclude-module=PyQt6.QtMultimedia',
        '--exclude-module=PyQt6.QtPositioning',
        '--exclude-module=PyQt6.QtQuickWidgets',
        '--exclude-module=PyQt6.QtQuick3D',
        '--exclude-module=PyQt6.QtRemoteObjects',
        '--exclude-module=PyQt6.QtWebChannel',
        '--exclude-module=PyQt6.QtWebEngineCore',
        '--exclude-module=PyQt6.QtWebEngineWidgets',
        '--exclude-module=PyQt6.QtWebView'
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("MoneyTracker build complete.")

if __name__ == "__main__":
    release_dir = f"Release_{VERSION}"
    # Clean previous builds
    for d in ['dist', 'build_updater', 'build_main', 'build_main_spec', release_dir]:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
            except Exception as e:
                print(f"Warning: Could not remove directory {d}: {e}")

    print("--- BUILD START ---")
    build_updater()
    build_main()
    print("--- BUILD END ---")
    
    print("Build process finished.")
    print(f"Output: {release_dir}/MoneyTracker.exe")
