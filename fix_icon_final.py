from PIL import Image
import os
import sys

def fix_icon():
    print("Generating high-res icon (Final Attempt)...", flush=True)
    try:
        if not os.path.exists("icon.ico"):
            print("icon.ico missing!", flush=True)
            return

        img = Image.open("icon.ico")
        
        # Get best frame
        max_size = (0, 0)
        best_frame = img.copy()
        try:
            i = 0
            while True:
                img.seek(i)
                if img.size[0] > max_size[0]:
                    max_size = img.size
                    best_frame = img.copy()
                i += 1
        except EOFError:
            pass
            
        print(f"Best frame: {best_frame.size}", flush=True)
        img = best_frame.convert("RGBA")
        
        # Sizes: Large to Small usually works better for some tools, but Pillow standard is arbitrary
        # Let's do explicit list
        target_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        
        imgs = []
        for size in target_sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            imgs.append(resized)
            
        # Save
        # We save the first one (256) and append the rest
        # This ensures the primary icon is the large one (good for Vista+)
        imgs[0].save("icon_final.ico", format="ICO", sizes=target_sizes, append_images=imgs[1:])
        
        print("Created icon_final.ico", flush=True)
        
        # Verify
        v_img = Image.open("icon_final.ico")
        print(f"Verified sizes: {v_img.info.get('sizes')}", flush=True)
        
    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    fix_icon()
