import PyInstaller.__main__
import os
import shutil

def build():
    # Remove previous build artifacts
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    # Define paths
    entry_point = "main.py"
    icon_path = "icon.ico" # Use the provided icon.ico file
    
    # Common data folders to include
    # Format: (source, destination)
    added_data = [
        ("gui/assets", "gui/assets"),
        ("data_manager.py", "."),
        ("version.py", "."),
        ("gui/styles.py", "gui"),
        ("gui/tabs", "gui/tabs"),
        ("gui/widgets", "gui/widgets"),
        ("icon.ico", "."),
        ("dist/updater.exe", "."),
    ]

    # Construct PyInstaller arguments
    args = [
        entry_point,
        "--onefile",
        "--windowed",
        "--name=MoneyTracker",
        "--clean",
        "--collect-all", "PyQt6",
    ]

    # Add icon if found
    if os.path.exists(icon_path):
        args.append(f"--icon={icon_path}")
    elif os.path.exists("gui/assets/icons/car_rental.svg"):
        # PyInstaller usually needs .ico for Windows, skipping for now if not .ico
        pass

    # Add data files
    for src, dest in added_data:
        if os.path.exists(src):
            args.extend(["--add-data", f"{src};{dest}"])

    print(f"Starting build with arguments: {' '.join(args)}")
    PyInstaller.__main__.run(args)
    print("\nBuild finished! Check the 'dist' folder for MoneyTracker.exe")

if __name__ == "__main__":
    build()
