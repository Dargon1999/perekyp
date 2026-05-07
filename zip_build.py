
import shutil
import os

def make_archive():
    source_dir = r"dist\MoneyTracker"
    output_filename = r"build\MoneyTracker_v8"
    
    # Ensure build dir exists
    if not os.path.exists("build"):
        os.makedirs("build")
        
    print(f"Zipping {source_dir} to {output_filename}.zip...")
    shutil.make_archive(output_filename, 'zip', source_dir)
    print("Done.")

if __name__ == "__main__":
    make_archive()
