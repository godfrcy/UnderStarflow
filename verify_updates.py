import pygame
import os
import sys

# Mock pygame
pygame.init()
pygame.display.set_mode((100, 100))

# Add path
sys.path.append(os.getcwd())

from entities.enemies import OverworldEnemy
from entities.player import Player

def verify_sprite_offset():
    print("\n--- Verifying Sprite Offset Fix ---")
    # Mock enemy
    # Create a dummy image for normal frames (64x64)
    normal_img = pygame.Surface((64, 64))
    
    # Create a dummy image for idle frames (150x150)
    idle_img = pygame.Surface((150, 150))
    
    # Instantiate enemy
    # Note: OverworldEnemy loads frames from disk. We'll manually inject frames to avoid dependency on files.
    enemy = OverworldEnemy(200, 200, is_static=False)
    
    # Inject frames
    enemy.frames = [normal_img]
    enemy.frames_idle = [idle_img]
    
    # Initialize state
    enemy.image = enemy.frames[0]
    enemy.rect = enemy.image.get_rect()
    enemy.rect.center = (200, 200)
    enemy.pos = [float(enemy.rect.x), float(enemy.rect.y)]
    
    print(f"Initial State (Normal Frame): Rect Center={enemy.rect.center}, Size={enemy.rect.size}, TopLeft={enemy.rect.topleft}")
    
    # Update 1: Switch to Idle (should happen if not chasing)
    enemy.is_chasing = False
    enemy.update(player=None)
    
    print(f"State after Update (Idle Frame): Rect Center={enemy.rect.center}, Size={enemy.rect.size}, TopLeft={enemy.rect.topleft}")
    
    if enemy.rect.center == (200, 200):
        print("PASS: Center remained (200, 200) after switching to larger idle frame.")
    else:
        print(f"FAIL: Center shifted to {enemy.rect.center}")

    if enemy.rect.size == (150, 150):
        print("PASS: Size updated to (150, 150).")
    else:
        print(f"FAIL: Size is {enemy.rect.size}")

def verify_leveling():
    print("\n--- Verifying Leveling System ---")
    p = Player(0, 0)
    
    print(f"Initial: Level {p.level}, HP {p.max_hp}, ATK {p.attack}, EXP {p.exp}/{p.max_exp}")
    
    # Gain 50 XP (No level up)
    p.gain_exp(50)
    print(f"After 50 XP: Level {p.level}, EXP {p.exp}")
    if p.level == 1 and p.exp == 50:
        print("PASS: Partial XP gain.")
    else:
        print("FAIL: XP gain logic incorrect.")

    # Gain 50 XP (Level up to 2)
    p.gain_exp(50)
    print(f"After +50 XP: Level {p.level}, HP {p.max_hp}, ATK {p.attack}, EXP {p.exp}")
    
    if p.level == 2:
        print("PASS: Level up to 2.")
    else:
        print("FAIL: Did not level up.")
        
    if p.max_hp == 30 and p.attack == 20: # Initial 20/10 -> +10/+10
        print("PASS: Stats increased correctly.")
    else:
        print(f"FAIL: Stats incorrect (HP={p.max_hp}, ATK={p.attack}).")
        
    if p.exp == 0:
         print("PASS: EXP reset.")
    else:
         print(f"FAIL: EXP not reset (EXP={p.exp}).")

    # Gain 250 XP (Level up multiple times? Logic says while loop)
    # 100 per level. 250 XP should be +2 levels and 50 remainder?
    # Current Level 2. Exp 0.
    # +100 -> Lvl 3. Exp 0.
    # +100 -> Lvl 4. Exp 0.
    # +50 -> Lvl 4. Exp 50.
    p.gain_exp(250)
    print(f"After +250 XP: Level {p.level}, HP {p.max_hp}, ATK {p.attack}, EXP {p.exp}")
    
    if p.level == 4 and p.exp == 50:
        print("PASS: Multi-level gain works.")
    else:
        print("FAIL: Multi-level gain incorrect.")

if __name__ == "__main__":
    try:
        verify_sprite_offset()
        verify_leveling()
    except Exception as e:
        print(f"Error: {e}")
