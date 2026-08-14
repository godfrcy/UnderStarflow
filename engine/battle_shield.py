import pygame
import random
import math
from engine.config import *


class ShieldMixin:
    def update_shield_minigame(self):
        # Shield Recovery
        if hasattr(self, 'shield_broken_timer') and self.shield_broken_timer > 0:
             self.shield_broken_timer -= 1

        # Calculate spawn interval based on progress (Accelerating)
        # Timer: 480 -> 0. 
        # Progress: 0.0 -> 1.0
        progress = 1.0 - (self.enemy_turn_timer / self.ENEMY_TURN_DURATION)
        
        # Interval: Starts at 40, drops to 10
        spawn_interval = int(40 - (30 * progress))
        spawn_interval = max(18, spawn_interval) # Increased min interval to avoid undodgeable clusters
        
        if self.enemy_turn_timer % spawn_interval == 0: 
            # Spawn Arrow
            valid_dirs = ["UP", "DOWN", "LEFT", "RIGHT"]
            
            # If inverted, Top (Visual) is Coordinate Bottom (DOWN). Disable it.
            if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
                if "DOWN" in valid_dirs: valid_dirs.remove("DOWN")

            direction = random.choice(valid_dirs)
            start_pos = [0, 0]
            cx, cy = self.heart_rect.centerx, self.heart_rect.centery
            dist = 300 # Start from far away
            
            if direction == "UP": start_pos = [cx, cy - dist]
            elif direction == "DOWN": start_pos = [cx, cy + dist]
            elif direction == "LEFT": start_pos = [cx - dist, cy]
            elif direction == "RIGHT": start_pos = [cx + dist, cy]
            
            # Determine Type
            arrow_type = 'white'
            # 30% Chance for Blue if Inverted (Skill B)
            if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
                 # Initialize pity counter if not present
                 if not hasattr(self, 'blue_pity_counter'):
                     self.blue_pity_counter = 0
                 
                 # Logic: Base 35% chance OR Force if pity >= 3 (Guarantee at least 1 in 4)
                 is_blue = False
                 if self.blue_pity_counter >= 3:
                     is_blue = True
                     # print("Blue Bullet Forced by Pity System")
                 elif random.random() < 0.35: 
                     is_blue = True
                 
                 if is_blue:
                     arrow_type = 'blue'
                     self.blue_pity_counter = 0
                 else:
                     self.blue_pity_counter += 1
            
            # Apply speed multiplier
            arrow_speed = 5 * self.bullet_speed_multiplier
            self.shield_arrows.append({'pos': start_pos, 'dir': direction, 'speed': arrow_speed, 'type': arrow_type})
            
        # Update Arrows
        for arrow in self.shield_arrows[:]:
            cx, cy = self.heart_rect.centerx, self.heart_rect.centery
            arrow_type = arrow.get('type', 'white')
            
            # Move IN to center (Both White and Blue now spawn from outside)
            dx = cx - arrow['pos'][0]
            dy = cy - arrow['pos'][1]
            dist_to_center = math.hypot(dx, dy)
            
            if dist_to_center > 0:
                arrow['pos'][0] += (dx / dist_to_center) * arrow['speed']
                arrow['pos'][1] += (dy / dist_to_center) * arrow['speed']
            
            # Collision Check
            # Check if hitting shield (Only if shield is active/not broken)
            is_shield_active = True
            if hasattr(self, 'shield_broken_timer') and self.shield_broken_timer > 0:
                is_shield_active = False

            if is_shield_active:
                arrow_rect = pygame.Rect(arrow['pos'][0]-5, arrow['pos'][1]-5, 10, 10)
                
                # Simple check: if close to center and direction matches shield direction
                hit_shield = False
                if dist_to_center < 35: # Close to shield radius
                    if arrow['dir'] == self.shield_dir:
                        hit_shield = True
                
                if hit_shield:
                    if arrow_type == 'blue':
                        # Blue Bullet -> Breaks Shield
                        self.shield_broken_timer = 180 # 3 seconds
                        self.shield_arrows.remove(arrow)
                        if self.calibration_sfx: 
                             self.calibration_sfx.set_volume(0.8)
                             self.calibration_sfx.play()
                    else:
                        # White Bullet -> Blocked
                        self.shield_arrows.remove(arrow)
                        # Play block sound
                        if self.calibration_sfx:
                            self.calibration_sfx.set_volume(0.5)
                            self.calibration_sfx.play()
                    continue
                
            # Check if hitting heart
            if dist_to_center < 10:
                self.shield_arrows.remove(arrow)
                
                # Blue bullets do NO damage (only shield break effect)
                if arrow_type != 'blue':
                    self.player.hp -= 2 
                    self.damage_flash_timer = 5
                    if self.player.hp <= 0:
                        self.handle_player_death()
                continue
