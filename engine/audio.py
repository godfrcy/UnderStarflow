import pygame
import os
from engine.utils import resource_path

def load_bgm(filename, start_pos=0.0):
    """
    尝试加载背景音乐，自动处理后缀名
    优先查找 .mp3, .ogg, .wav，最后尝试原始文件名
    """
    base_name = os.path.splitext(filename)[0]
    extensions = [".mp3", ".ogg", ".wav", ".m4a"]
    
    # 尝试所有扩展名
    for ext in extensions:
        full_name = base_name + ext
        try:
            path = resource_path(full_name)
            if os.path.exists(path):
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(-1, start=start_pos)
                print(f"Playing BGM: {full_name}")
                return
        except Exception as e:
            # 静默失败，尝试下一个
            pass
            
    # 如果都失败了，尝试直接加载原始文件名 (兜底)
    try:
        path = resource_path(filename)
        if os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1, start=start_pos)
            print(f"Playing BGM: {filename}")
            return
    except Exception as e:
        print(f"Failed to load BGM {filename}: {e}")
