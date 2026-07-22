
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS_DB = os.path.join(ROOT, "assetsDB")

# Define the new structure
STRUCTURE = [
    "maps",
    "characters/enemies/machine_soldier",
    "characters/enemies/new_soldier",
    "characters/enemies/variable",
    "characters/enemies/rebel_leader",
    "characters/enemies/rebel_walker",
    "characters/enemies/black_ranger",
    "characters/player",
    "items/battery",
    "objects/bonfire",
    "audio/bgm",
    "audio/sfx",
    "ui/backgrounds",
    "ui/portraits"
]

# Define moves: (source_name, destination_relative_path)
# source_name is relative to assetsDB
MOVES = {
    # Maps
    "基地": "maps/base_1",
    "base2_grid": "maps/base_2",
    "base3_grid": "maps/base_3",
    "基地4_grid": "maps/base_4",
    "基地5_grid": "maps/base_5",
    "管道噩梦1_grid": "maps/pipe_nightmare_1",
    "管道噩梦2_grid": "maps/pipe_nightmare_2",
    "管道噩梦3_grid": "maps/pipe_nightmare_3",
    "雪地grid": "maps/snow_start",
    "雪地1.2_grid": "maps/snow_1_2",
    "雪地1.3_grid": "maps/snow_1_3",
    
    # Enemies
    "jikaizhong_grid": "characters/enemies/machine_soldier",
    "newsoldier_grid": "characters/enemies/new_soldier",
    "variable_grid": "characters/enemies/variable",
    "义军女1": "characters/enemies/rebel_leader",
    "义军行走_grid": "characters/enemies/rebel_walker",
    "黑游侠_grid": "characters/enemies/black_ranger",

    # Player
    "anthe_sheet.png": "characters/player",
    
    # Items/Objects
    "new items_grid": "items/battery",
    "fire_grid": "objects/bonfire",
    
    # Files (Audio/UI) - Source is filename, Dest is folder
    "city ruins.mp3": "audio/bgm",
    "the tree.mp3": "audio/bgm",
    "monster_song.mp3": "audio/bgm",
    "jikaizhong.mp3": "audio/bgm",
    "the fish.MP3": "audio/bgm",
    "new items.mp3": "audio/bgm", # Assuming it's BGM based on usage
    "英雄主义.mp3": "audio/bgm",
    "new map.mp3": "audio/bgm",
    "sound.MP3": "audio/sfx",
    "attack_success.wav": "audio/sfx",
    
    # UI/Misc
    "icon.ico": "ui",
    "startgame.jpg": "ui/backgrounds",
    "tile01.jpg": "ui/backgrounds",
    "mechanical_heart.jpeg": "ui/backgrounds", # Guessing
    "同步率.png": "ui",
    "阿尔忒半身像.png": "ui/portraits",
    "头像框.png": "ui/portraits",
    
    # Special case: assets/demo_map -> maps/demo_map
    # We'll handle this separately or copy it
}

def main():
    print(f"Organizing assets in {ASSETS_DB}...")
    
    # 1. Create Directories
    for folder in STRUCTURE:
        path = os.path.join(ASSETS_DB, folder)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Created {path}")

    # 2. Move Files/Folders
    for src_name, dest_rel_path in MOVES.items():
        src_path = os.path.join(ASSETS_DB, src_name)
        dest_path = os.path.join(ASSETS_DB, dest_rel_path)
        
        # Check if dest is a folder (for files) or the new name (for folders)
        # If moving a folder to a new name: dest_path is the new folder path
        # If moving a file to a folder: dest_path is the folder
        
        if not os.path.exists(src_path):
            print(f"Skip: {src_name} not found.")
            continue
            
        if os.path.isdir(src_path):
            # Moving/Renaming a directory
            # If dest exists (and is empty or we are merging), we might have issues.
            # But here we assume renaming.
            # shutil.move(src, dst)
            try:
                # If destination folder exists (created in step 1), rmdir it so move works as rename?
                # No, if we created 'maps/base_1', shutil.move('基地', 'maps/base_1') might put '基地' INSIDE 'maps/base_1'.
                # We want '基地' contents to BE 'maps/base_1'.
                
                # If we created the directory structure, we should be careful.
                # 'maps' exists. 'maps/base_1' might NOT exist yet if we only created 'maps'.
                # STRUCTURE list has "maps", but not "maps/base_1".
                # Wait, STRUCTURE has "characters/enemies/machine_soldier".
                # So the leaf folder exists.
                
                # If "characters/enemies/machine_soldier" exists and is empty:
                # shutil.move("jikaizhong_grid", "characters/enemies/machine_soldier") -> "characters/enemies/machine_soldier/jikaizhong_grid"
                # THIS IS WRONG.
                
                # Correct approach:
                # If target directory exists and is empty, remove it, then move/rename source to target.
                
                if os.path.exists(dest_path) and os.path.isdir(dest_path) and not os.listdir(dest_path):
                    os.rmdir(dest_path)
                
                shutil.move(src_path, dest_path)
                print(f"Moved {src_name} -> {dest_rel_path}")
            except Exception as e:
                print(f"Error moving {src_name}: {e}")
        else:
            # Moving a file
            # Dest should be a directory
            # dest_path from MOVES is likely a directory (e.g., "audio/bgm")
            # If it's a file rename, we need to specify full path.
            # My mapping for files is "filename": "folder".
            
            try:
                shutil.move(src_path, dest_path)
                print(f"Moved file {src_name} -> {dest_rel_path}")
            except Exception as e:
                print(f"Error moving file {src_name}: {e}")

    # 3. Handle 'assets/demo_map' special case
    # Move assetsDB/assets/demo_map -> assetsDB/maps/demo_map
    src_demo = os.path.join(ASSETS_DB, "assets", "demo_map")
    dest_demo = os.path.join(ASSETS_DB, "maps", "demo_map")
    if os.path.exists(src_demo):
        if os.path.exists(dest_demo):
             shutil.rmtree(dest_demo) # Clean slate
        shutil.move(src_demo, dest_demo)
        print("Moved demo_map")
        
        # Check if assetsDB/assets is empty, remove if so
        assets_folder = os.path.join(ASSETS_DB, "assets")
        if os.path.exists(assets_folder) and not os.listdir(assets_folder):
            os.rmdir(assets_folder)
            print("Removed empty assets folder")
    
    # 4. Handle 'black_ranger_ex.png' -> 'characters/enemies/black_ranger/black_ranger.png'?
    # Actually, if 'black_ranger_ex.png' is a file, and we want to put it in a folder.
    # The MOVES has "黑游侠_grid" -> "characters/enemies/black_ranger".
    # If "黑游侠_grid" doesn't exist but there are pngs, we might need manual handling.
    # But LS showed "black_ranger_ex.png" (file) and NO "黑游侠_grid" folder in the first 40000 chars.
    # Wait, I missed "黑游侠_grid" in LS output? 
    # Let me re-check LS output in memory.
    # LS output was truncated.
    # I should assume "黑游侠_grid" might NOT exist if I didn't see it, OR it was truncated.
    # But main.py references "黑游侠_grid". So it must exist.
    
    print("Done.")

if __name__ == "__main__":
    main()
