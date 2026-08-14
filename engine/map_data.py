# --- Map Configuration ---
MAP_CONFIG = {
    "start": {
        "folder": "maps/snow_start",
        "next": "snow_1_2",
        "prev": None,
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "无主雪地",
        "has_bonfire": True,
        "bonfire_pos": (128 * 3, 128 * 3),
        "spawn_pos": (128 * 3, 128 * 5),
        "show_title": True
    },
    "snow_1_2": {
        "folder": "maps/snow_1_2",
        "next": "snow_1_3",
        "prev": "start",
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "雪地1.2",
        "has_bonfire": False,
        "show_title": False
    },
    "snow_1_3": {
        "folder": "maps/snow_1_3",
        "next": None,
        "prev": "snow_1_2",
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "雪地1.3",
        "has_bonfire": False,
        "show_title": False
    },
    "base_1": {
        "folder": "maps/base_1",
        "next": "base_2",
        "prev": None,
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "基地",
        "has_bonfire": True,
        "bonfire_pos": (128 * 3, 128 * 4),
        "spawn_pos": (128 * 3, 128 * 4),
        "show_title": True
    },
    "base_2": {
        "folder": "maps/base_2",
        "next": "base_3",
        "prev": "base_1",
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "基地深处",
        "has_bonfire": False,
        "show_title": False
    },
    "base_3": {
        "folder": "maps/base_3",
        "next": "base_4",
        "prev": "base_2",
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "基地核心",
        "has_bonfire": False,
        "show_title": False
    },
    "pipe_nightmare_1": {
        "folder": "maps/pipe_nightmare_1",
        "next": "pipe_nightmare_2",
        "prev": "base_5",
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "管道噩梦1",
        "has_bonfire": False,
        "show_title": False
    },
    "pipe_nightmare_2": {
        "folder": "maps/pipe_nightmare_2",
        "next": None,
        "prev": "pipe_nightmare_1",
        "down": None, # Removed connection to pipe_nightmare_3 to avoid skip
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "管道噩梦2",
        "has_bonfire": False,
        "show_title": False
    },
    "pipe_nightmare_3": {
        "folder": "maps/pipe_nightmare_3",
        "next": "pipe_nightmare_1_2",
        "prev": None,
        "down": "pipe_nightmare_2_1",
        "bgm": "audio/bgm/oldcore.mp3",
        "name": "管道噩梦",
        "has_bonfire": True,
        "bonfire_pos": (128 * 3, 128 * 3),
        "spawn_pos": (128 * 3, 128 * 4),
        "show_title": True,
        "open_top_rows": True
    },
    "pipe_nightmare_1_2": {
        "folder": "maps/pipe_nightmare_3", # Use Pipe 3 Assets
        "next": "pipe_nightmare_1_3",
        "prev": "pipe_nightmare_3",
        "bgm": "audio/bgm/oldcore.mp3",
        "name": "管道大噩梦1-2",
        "has_bonfire": False,
        "show_title": False,
        "is_pipe_channel": True
    },
    "pipe_nightmare_2_1": {
        "folder": "maps/pipe_nightmare_3", # Use Pipe 3 Assets (Vertical)
        "next": None,
        "prev": None,
        "up": "pipe_nightmare_3",
        "down": "pipe_nightmare_3_1",
        "bgm": "audio/bgm/oldcore.mp3",
        "name": "管道大噩梦2-1",
        "has_bonfire": False,
        "show_title": False,
        "is_vertical_pipe_channel": True,
        "open_top_rows": True
    },
    "pipe_nightmare_1_3": {
        "folder": "maps/pipe_nightmare_3", # Reuse pipe tiles (gray_floor was legacy, deleted)
        "next": None,
        "prev": "pipe_nightmare_1_2",
        "down": "pipe_nightmare_2_3",
        "bgm": "audio/bgm/oldcore.mp3",
        "name": "管道大噩梦1-3",
        "has_bonfire": False,
        "show_title": False,
        "open_top_rows": True,
        "extra_obstacles": [
             # --- Boundary Limits ---
             # 1. Left Edge Return Restriction: Only Row 2,3 (Indices) allowed.
             # Block return at (-1,0), (-1,1) and (-1,4), (-1,5)
             (-1, 0), (-1, 1), (-1, 4), (-1, 5),

             # 2. Bottom Exit Restriction: Only Col 2,3 allowed.
             # Block exit at (0,6), (1,6), (4,6), (5,6)
             (0, 6), (1, 6), (4, 6), (5, 6),

             # --- Maze Walls ---
             # Force Path: Left -> Top -> Right -> Bottom -> Inner Hook -> Exit

             # 1. Block Center Upper Rows (Force Top Perimeter)
             (1, 1), (2, 1), (3, 1), (4, 1),
             (1, 2), (2, 2), (3, 2), (4, 2),

             # 2. Block Center Lower (Guide Hook)
             # Block (1,3), (1,4) to wall off left side
             (1, 3), (1, 4),

             # Block Bottom-Left Path (Prevent Shortcut)
             (0, 4), (0, 5), (1, 5),

             # Block (3,5) Removed to open exit path
             # Block Bottom-Right corners to force exit only at Cols 2,3 (Indices)
             (4, 5), (5, 5),

             # Path Trace:
             # Start (0,2)/(0,3) -> Up to (0,0)
             # Right along Top (0,0)->(5,0)
             # Down along Right (5,0)->(5,5)
             # Left to (4,5)
             # Up to (4,3) [Avoids (3,5) block]
             # Left to (2,3)
             # Down to (2,5) -> Exit!
        ]
    },
    "pipe_nightmare_2_3": {
        "folder": "maps/pipe_nightmare_3", # Use Pipe 3 Assets (Bonfire style)
        "next": None,
        "down": "pipe_nightmare_3_3",
        "prev": "pipe_nightmare_2_2",
        "up": "pipe_nightmare_1_3",
        "bgm": "audio/bgm/oldcore.mp3",
        "name": "管道大噩梦2-3",
        "has_bonfire": False,
        "show_title": False,
        "open_top_rows": True
    },
    "pipe_nightmare_3_1": {
        "folder": "maps/pipe_nightmare_3", # Consistent assets
        "next": "pipe_nightmare_3_2",
        "prev": None,
        "up": "pipe_nightmare_2_1",
        "bgm": "audio/bgm/oldcore.mp3",
        "name": "管道大噩梦3-1",
        "has_bonfire": False,
        "show_title": False,
        "open_top_rows": True
    },
    "pipe_nightmare_2_2": {
        "folder": "maps/pipe_nightmare_2_2",
        "next": "pipe_nightmare_2_3",
        "prev": None,
        "down": "pipe_nightmare_3_2",
        "bgm": "audio/bgm/oldcore.mp3",
        "name": "管道大噩梦2-2",
        "has_bonfire": False,
        "show_title": False,
        "open_top_rows": True,
        "extra_obstacles": [
            # Block Row 0 (Distant View)
            (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0),
            # Block Row 1 (Distant View)
            (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1)
        ]
    },
    "pipe_nightmare_3_2": {
        "folder": "maps/pipe_nightmare_3_2",
        "next": None,
        "prev": "pipe_nightmare_3_1",
        "up": "pipe_nightmare_2_2", # Connects to 2-2 (implied) or just placeholder
        "bgm": "audio/bgm/oldcore.mp3",
        "name": "管道大噩梦3-2",
        "has_bonfire": False,
        "show_title": False,
        "open_top_rows": True
    },
    "pipe_nightmare_3_3": {
        "folder": "maps/pipe_nightmare_3_3",
        "next": None,
        "prev": None,
        "up": "pipe_nightmare_2_3",
        "bgm": "audio/bgm/oldcore.mp3",
        "name": "管道大噩梦3-3",
        "has_bonfire": False,
        "show_title": False,
        "open_top_rows": True
    },
    "base_4": {
        "folder": "maps/base_4",
        "next": "base_5",
        "prev": "base_3",
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "基地深层",
        "has_bonfire": False,
        "show_title": False
    },
    "base_5": {
        "folder": "maps/base_5",
        "next": "pipe_nightmare_1",
        "prev": "base_4",
        "bgm": "audio/bgm/city_ruins.mp3",
        "bgm_start": 4.0,
        "name": "基地裂隙",
        "has_bonfire": False,
        "show_title": False,
        "extra_obstacles": [
            (4, 2), (5, 2), # Row 3 (Index 2), Cols 5,6 (Index 4,5)
            (4, 3), (5, 3)  # Row 4 (Index 3), Cols 5,6 (Index 4,5)
        ]
    }
}
