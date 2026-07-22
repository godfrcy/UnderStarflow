import os
import pygame

def resource_path(relative_path):
    return os.path.abspath(relative_path)

RENDER_TILE_SIZE = 128

def check_loading():
    folder_name = "assetsDB/幽灵士兵_grid"
    file_prefix = "幽灵士兵"
    base_path = resource_path(folder_name)
    print(f"Checking folder: {base_path}")
    
    if not os.path.exists(base_path):
        print("Folder does not exist!")
        return

    frames = []
    # Grid logic
    for row in range(1, 5):
        for col in range(1, 5):
            fname = f"{file_prefix}_{row}_{col}.png"
            full_path = os.path.join(base_path, fname)
            if os.path.exists(full_path):
                print(f"Found: {fname}")
                frames.append(fname)
            else:
                pass
                # print(f"Not Found: {fname}")
    
    print(f"Total frames found: {len(frames)}")
    if len(frames) == 0:
        print("ERROR: No frames loaded!")
    else:
        print("Success!")

if __name__ == "__main__":
    check_loading()
