import sys
import os
import pygame

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # Check root first (if flat packed)
        path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(path):
            return path
            
        # Check assetsDB folder (if packed as directory)
        path = os.path.join(sys._MEIPASS, "assetsDB", relative_path)
        if os.path.exists(path):
            return path
            
        return os.path.join(sys._MEIPASS, relative_path)
        
    # Return absolute path relative to the project root (one level up from engine/)
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Support assetsDB structure
    assets_db_path = os.path.join(base_path, "assetsDB", relative_path)
    if os.path.exists(assets_db_path):
        return assets_db_path
        
    return os.path.join(base_path, relative_path)

def get_font(size):
    """
    Safely load a font. 
    1. Try system SimHei (Windows CJK).
    2. Try system Microsoft YaHei.
    3. Fallback to default (None).
    Avoids SysFont to prevent registry scanning crashes on some Windows systems.
    """
    # Common Windows font paths for Chinese
    font_paths = [
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                continue
                
    # Fallback to default font (may not support Chinese, but won't crash)
    return pygame.font.Font(None, size)
