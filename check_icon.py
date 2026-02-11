# from PIL import Image
import sys
import os

print("Script started - PIL disabled")

try:
    with open("icon_check_result.txt", "w") as f:
        f.write("Starting check...\n")
        if not os.path.exists("icon.ico"):
            f.write("icon.ico does not exist!\n")
            print("icon.ico does not exist!")
        else:
            # img = Image.open("icon.ico")
            # f.write(f"Format: {img.format}\n")
            # f.write(f"Sizes: {img.info.get('sizes')}\n")
            # print(f"Format: {img.format}")
            # print(f"Sizes: {img.info.get('sizes')}")
            f.write("File exists (PIL disabled)\n")
except Exception as e:
    print(f"Error: {e}")
    with open("icon_check_result.txt", "w") as f:
        f.write(f"Error: {e}\n")
