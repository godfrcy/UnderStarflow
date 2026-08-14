import pygame
import random
import math
from engine.config import *
from entities.bullets import Bullet, PlasmaBlade, LaserNetworkLine, YellowBullet
from entities.particles import BattleDust, DebrisParticle


class BulletSpawnMixin:
    def spawn_bullets(self):
        # Calculate elapsed time (timer starts at 480, decrements to 479 first thing)
        # So elapsed = 480 - 479 = 1 (Frame 1)
        time_elapsed = self.ENEMY_TURN_DURATION - self.enemy_turn_timer
        
        # Black Ranger Skills
        # Skill A: All-around shooting (Yellow + Blue)
        if "black_ranger_a" in self.active_skills:
            # Spawn logic
            if not hasattr(self, 'bullet_spawn_timer'):
                self.bullet_spawn_timer = 0
            self.bullet_spawn_timer += 1
            
            # Spawn every 20 frames (approx 3 times a second)
            if self.bullet_spawn_timer % 20 == 0:
                # Spawn around the circle outside battle box
                center_x, center_y = self.battle_box.center
                radius = 200 # Outside the box
                
                # Number of bullets per wave (Reduced from 6 to 3)
                count = 3
                angle_offset = random.uniform(0, 360)
                
                for i in range(count):
                    angle = (360 / count) * i + angle_offset
                    rad = math.radians(angle)
                    start_x = center_x + math.cos(rad) * radius
                    start_y = center_y + math.sin(rad) * radius
                    
                    # Target center
                    dx = center_x - start_x
                    dy = center_y - start_y
                    dist = math.hypot(dx, dy)
                    speed = 7 * self.bullet_speed_multiplier # "Fast"
                    
                    vx = (dx / dist) * speed
                    vy = (dy / dist) * speed
                    
                    # Mix Blue and Yellow
                    # User: "Also intersperse Blue Bullets"
                    # Yellow: New mechanism (safe if stationary)
                    # Increased Blue proportion (Skill A request: more blue)
                    b_type = "yellow_line" if random.random() < 0.3 else "blue_sphere"
                    
                    if b_type == "yellow_line":
                        # Yellow Bullets wait 0.5s (30 frames)
                        rect = pygame.Rect(start_x, start_y, 40, 10) # Long line shape
                        # Rotate rect based on angle? Pygame rects are axis aligned.
                        # For visual, we might need to handle rotation in draw, but for now axis-aligned rect is fine or small rect.
                        # Let's make it a small square for hitbox, but visual will be line?
                        # Or just a small projectile.
                        b = YellowBullet(pygame.Rect(start_x, start_y, 10, 10), vx, vy, wait_time=30)
                        self.bullets.append(b)
                    else:
                        # Blue Sphere
                        # No wait, just shoot? Or maybe wait too to sync?
                        # "Speed can be faster, but after spawning freeze 0.5s" -> Applies to Yellow?
                        # "Yellow is a new mechanism... also intersperse Blue".
                        # Let's apply wait to both for consistency or just Yellow? 
                        # "From 360 degrees... Yellow bullets... freeze 0.5s... also intersperse Blue".
                        # I'll apply wait to Yellow only based on description, or both.
                        # Blue sphere is standard. Let's make Blue standard projectile.
                        b = Bullet(pygame.Rect(start_x, start_y, 10, 10), vx, vy, (0, 100, 255), "blue_sphere")
                        self.bullets.append(b)

        # Skill C: Fire Suppression (Small Box 9x9 -> 120x120)
        if "black_ranger_c" in self.active_skills:
             if not hasattr(self, 'bullet_spawn_timer'):
                self.bullet_spawn_timer = 0
             self.bullet_spawn_timer += 1
             
             # Spawn frequently from bottom
             # "Divide battle box bottom into three equal parts and shoots up"
             if self.bullet_spawn_timer % 15 == 0:
                 # Divide into 3 sections
                 section_width = self.battle_box.width // 3
                 section_idx = random.randint(0, 2)
                 
                 spawn_x = self.battle_box.left + (section_idx * section_width) + (section_width // 2) - 10 # Center of section, minus half bullet width
                 spawn_y = self.battle_box.bottom
                 
                 # Upward speed
                 vy = -5 * self.bullet_speed_multiplier # Faster
                 vx = 0
                 
                 b_type = "yellow_line" if random.random() < 0.5 else "blue_sphere"
                 
                 bullet_w = 20 # Thick bar
                 bullet_h = 40
                 
                 rect = pygame.Rect(spawn_x, spawn_y, bullet_w, bullet_h)
                 
                 if b_type == "yellow_line":
                     # Yellow Bullet (Thick Vertical Bar)
                     # Yellow mechanic: Safe if stationary
                     # Using YellowBullet with wait_time=0 for immediate movement but retaining logic
                     # But YellowBullet logic in update handles wait.
                     # If wait_time=0, it moves immediately.
                     b = YellowBullet(rect, vx, vy, wait_time=0) 
                     self.bullets.append(b)
                 else:
                     # Blue Bullet (Thick Vertical Bar)
                     # Standard damage
                     # Use "blue_sphere" type for standard damage logic, but shape is rect
                     # But draw() might draw a sphere if type is blue_sphere.
                     # Let's check draw().
                     # If I want it to look like a thick bar, I should use a new type or "normal" with blue color?
                     # Or "blue_rect".
                     # Let's use "blue_rect" and ensure draw handles it or default rect.
                     # Bullet.draw() usually draws rect if no specific sprite.
                     # Let's check Bullet.draw(). 
                     # Assuming Bullet.draw draws rect if type unknown or just uses color.
                     # I'll use "blue_rect" for clarity.
                     self.bullets.append(Bullet(rect, vx, vy, (0, 100, 255), "blue_rect"))

        # Laser
        # Fire at Frame 1, 121, 241... (Every 2s)
        # Modified to 120 frames to avoid overlap (Laser lasts 100 frames)
        if "laser" in self.active_skills and time_elapsed % 120 == 1:
            spawn_x = random.randint(self.battle_box.left + 20, self.battle_box.right - 20)
            laser_rect = pygame.Rect(spawn_x, self.battle_box.top, 20, self.battle_box.height)
            self.bullets.append(Bullet(laser_rect, 0, 0, b_type="laser"))
            
        # Moving Laser
        if "moving_laser" in self.active_skills and time_elapsed % 60 == 1:
            orientation = random.choice(['h', 'v'])
            speed_val = random.uniform(1.0, 3.0) * self.bullet_speed_multiplier
            direction = random.choice([1, -1])
            speed = speed_val * direction
            if orientation == 'v':
                w, h = 24, self.battle_box.height
                x = random.randint(self.battle_box.left, self.battle_box.right - w)
                y = self.battle_box.top
                self.bullets.append(Bullet(pygame.Rect(x, y, w, h), speed, 0, b_type="laser"))
            else:
                w, h = self.battle_box.width, 24
                x = self.battle_box.left
                y = random.randint(self.battle_box.top, self.battle_box.bottom - h)
                self.bullets.append(Bullet(pygame.Rect(x, y, w, h), 0, speed, b_type="laser"))
                
        # Random Particles
        # Fire rapidly (every 5 frames)
        if "random_particles" in self.active_skills and time_elapsed % 5 == 0:
            # Generate position away from player
            safe_radius = 60
            for _ in range(10): # Try 10 times to find a safe spot
                bx = random.randint(self.battle_box.left, self.battle_box.right - 10)
                by = random.randint(self.battle_box.top, self.battle_box.bottom - 10)
                # Distance check
                dx = bx - self.heart_rect.centerx
                dy = by - self.heart_rect.centery
                if (dx*dx + dy*dy) > safe_radius*safe_radius:
                    break
            
            vx = random.uniform(-2, 2) * self.bullet_speed_multiplier
            vy = random.uniform(-2, 2) * self.bullet_speed_multiplier
            self.bullets.append(Bullet(pygame.Rect(bx, by, 8, 8), vx, vy, (255, 255, 255), b_type="normal"))
            
        # Blue Spheres (formerly Cube)
        # Fire at Frame 1, 121, 241... (Every 2s)
        if "cube" in self.active_skills and time_elapsed % 120 == 1:
            # Refresh 3 blue spheres, size 1/3 of original (80/3 approx 26)
            size = 26 
            for _ in range(3):
                start_x = self.battle_box.left + random.randint(0, 100)
                start_y = self.battle_box.top + random.randint(0, 100)
                
                target_x = self.battle_box.right - size - random.randint(0, 100)
                target_y = self.battle_box.bottom - size - random.randint(0, 100)
                
                duration = 120
                vx = ((target_x - start_x) / duration) * self.bullet_speed_multiplier
                vy = ((target_y - start_y) / duration) * self.bullet_speed_multiplier
                
                self.bullets.append(Bullet(pygame.Rect(start_x, start_y, size, size), vx, vy, (0, 100, 255), b_type="blue_sphere"))
            
        # Circle Burst
        if "circle" in self.active_skills and self.enemy_turn_timer % 12 == 0:
            center_x, center_y = self.enemy_rect.center
            angle_offset = (self.enemy_turn_timer // 12) * 10 
            for i in range(12):
                angle = (360 / 12) * i + angle_offset
                rad = math.radians(angle)
                speed = 4 * self.bullet_speed_multiplier
                vx = math.cos(rad) * speed
                vy = math.sin(rad) * speed
                self.bullets.append(Bullet(pygame.Rect(center_x, center_y, 6, 6), vx, vy, (255, 200, 100), b_type="normal"))
                
        # Ruin Cutting Sequence
        if "ruin_cutting_sequence" in self.active_skills:
            if time_elapsed % 40 == 0:
                cycle = time_elapsed // 40
                blade_width, blade_height = 150, 40
                speed = 6 * self.bullet_speed_multiplier
                spawn_y = random.randint(self.battle_box.top + 5, self.battle_box.bottom - blade_height - 5)
                if cycle % 2 == 0:
                    start_x = self.battle_box.left - blade_width
                    direction = 1
                else:
                    start_x = self.battle_box.right
                    direction = -1
                self.bullets.append(PlasmaBlade(start_x, spawn_y, blade_width, blade_height, speed, direction))
                
        # Laser Network
        if "laser_network" in self.active_skills:
            if time_elapsed % 140 == 10: 
                x_steps = list(range(self.battle_box.left + 40, self.battle_box.right - 40, 60))
                y_steps = list(range(self.battle_box.top + 40, self.battle_box.bottom - 40, 60))
                cols = random.sample(x_steps, min(len(x_steps), random.randint(2, 3))) if x_steps else []
                rows = random.sample(y_steps, min(len(y_steps), random.randint(2, 3))) if y_steps else []
                for x in cols:
                    self.bullets.append(LaserNetworkLine(pygame.Rect(x - 15, self.battle_box.top, 30, self.battle_box.height), 'v'))
                for y in rows:
                    self.bullets.append(LaserNetworkLine(pygame.Rect(self.battle_box.left, y - 15, self.battle_box.width, 30), 'h'))

        # Ghost Slash (Purple Plasma Blades)
        if "ghost_slash" in self.active_skills:
            if time_elapsed % 45 == 0: # Slightly slower than ruin cutting
                cycle = time_elapsed // 45
                blade_width, blade_height = 150, 40
                speed = 7 * self.bullet_speed_multiplier
                spawn_y = random.randint(self.battle_box.top + 5, self.battle_box.bottom - blade_height - 5)
                
                # Dark Purple Colors
                c_outer = (138, 43, 226) # Blue Violet
                c_inner = (230, 230, 250) # Lavender
                
                if cycle % 2 == 0:
                    start_x = self.battle_box.left - blade_width
                    direction = 1
                else:
                    start_x = self.battle_box.right
                    direction = -1
                self.bullets.append(PlasmaBlade(start_x, spawn_y, blade_width, blade_height, speed, direction, color=c_outer, inner_color=c_inner))

        # Dark Orb (Homing Dark Spheres)
        if "dark_orb" in self.active_skills:
            if not hasattr(self, 'orb_spawn_timer'): self.orb_spawn_timer = 0
            self.orb_spawn_timer += 1
            
            # Increased fire rate (20 -> 15)
            if self.orb_spawn_timer % 15 == 0:
                # Spawn from corners
                corners = [
                    (self.battle_box.left, self.battle_box.top),
                    (self.battle_box.right, self.battle_box.top),
                    (self.battle_box.left, self.battle_box.bottom),
                    (self.battle_box.right, self.battle_box.bottom)
                ]
                start_pos = random.choice(corners)
                
                # Target player
                target_x, target_y = self.heart_rect.center
                dx = target_x - start_pos[0]
                dy = target_y - start_pos[1]
                dist = math.hypot(dx, dy)
                speed = 4 * self.bullet_speed_multiplier
                vx = (dx / dist) * speed
                vy = (dy / dist) * speed
                
                # Dark Orb (Purple Sphere)
                self.bullets.append(Bullet(pygame.Rect(start_pos[0], start_pos[1], 16, 16), vx, vy, (75, 0, 130), b_type="blue_sphere"))

        # Samurai Fire Walls (Skill B)
        if "samurai_fire_walls" in self.active_skills:
            
            # 3 Waves: Increased intervals (60, 180, 300) to fill the turn and reduce difficulty
            if time_elapsed in [60, 180, 300]:
                bullet_size = 16
                bullet_gap = 16 # Dense
                speed = 3 * self.bullet_speed_multiplier
                
                # Choose ONE safe direction for this wave
                safe_direction = random.choice(["LEFT", "RIGHT", "TOP", "BOTTOM"])
                
                # Define Wall Functions
                def create_wall(side, start_x, start_y, is_vertical, move_x, move_y):
                    length = self.battle_box.height if is_vertical else self.battle_box.width
                    count = length // bullet_gap
                    
                    indices_to_skip = []
                    
                    opp_map = {"LEFT":"RIGHT", "RIGHT":"LEFT", "TOP":"BOTTOM", "BOTTOM":"TOP"}
                    
                    # Logic for Gaps
                    if side == safe_direction:
                        # Exit Wall: Center Gap (Exit Hole)
                        center = count // 2
                        indices_to_skip = [center-1, center, center+1, center+2]
                    elif side == opp_map[safe_direction]:
                        # Opposite Wall: Solid
                        pass
                    else:
                        # Adjacent Walls: Clear the Safe Half to allow access to Exit
                        # If Safe is LEFT (Low X), Top/Bottom (Horizontal) must clear Low X.
                        if safe_direction == "LEFT": 
                             indices_to_skip = list(range(0, count // 2))
                        elif safe_direction == "RIGHT":
                             indices_to_skip = list(range(count // 2, count))
                        # If Safe is TOP (Low Y), Left/Right (Vertical) must clear Low Y.
                        elif safe_direction == "TOP": 
                             indices_to_skip = list(range(0, count // 2))
                        elif safe_direction == "BOTTOM":
                             indices_to_skip = list(range(count // 2, count))

                    for i in range(count):
                        if i in indices_to_skip: continue
                        
                        # Structured Pattern: 4 Solid, 2 Empty (32px Gap)
                        # Improves aesthetics and ensures survival space > 1 bullet
                        if (i % 6) >= 4: continue
                        
                        if is_vertical:
                            bx = start_x
                            by = self.battle_box.top + i * bullet_gap
                        else:
                            bx = self.battle_box.left + i * bullet_gap
                            by = start_y
                        self.bullets.append(Bullet(pygame.Rect(bx, by, bullet_size, bullet_size), move_x, move_y, (255, 69, 0), b_type="fire"))

                # Left Wall (Move Right)
                create_wall("LEFT", self.battle_box.left - 20, 0, True, speed, 0)
                # Right Wall (Move Left)
                create_wall("RIGHT", self.battle_box.right + 20, 0, True, -speed, 0)
                # Top Wall (Move Down)
                create_wall("TOP", 0, self.battle_box.top - 20, False, 0, speed)
                # Bottom Wall (Move Up)
                create_wall("BOTTOM", 0, self.battle_box.bottom + 20, False, 0, -speed)

        # Samurai Gravity Jump (Skill C)
        if "samurai_gravity_jump" in self.active_skills:
             
             # Fire Pillars
             if time_elapsed % 60 == 0: # Every second
                 # Pillars from both sides
                 speed = 4 * self.bullet_speed_multiplier
                 
                 # Calculate gap Y
                 # Jump Peak: h = v^2 / 2g. (-9)^2 / 1.2 = 81 / 1.2 = 67.5
                 # So gap should be around bottom - 67.5
                 jump_peak = (self.jump_strength * self.jump_strength) / (2 * self.gravity)
                 gap_center_y = (self.battle_box.bottom - 5) - jump_peak
                 gap_height = 50 # Size of gap
                 
                 # Function to create pillar
                 def create_pillar(start_x, move_x):
                     # Iterate vertical positions
                     step = 16
                     for y in range(self.battle_box.top, self.battle_box.bottom, step):
                         # Check gap
                         if gap_center_y - gap_height/2 < y < gap_center_y + gap_height/2:
                             continue
                         
                         b = Bullet(pygame.Rect(start_x, y, 16, 16), move_x, 0, (255, 69, 0), b_type="fire")
                         self.bullets.append(b)
                 
                 create_pillar(self.battle_box.left - 20, speed)
                 create_pillar(self.battle_box.right + 20, -speed)

        # Flash Cut (Fast Lasers)
        if "flash_cut" in self.active_skills:
            # Warning at 0, Fire at 40.
            # Multiple cuts
            if time_elapsed % 60 == 0:
                # Horizontal or Vertical cut
                if random.random() < 0.5:
                    # Horizontal
                    y = random.randint(self.battle_box.top, self.battle_box.bottom - 20)
                    rect = pygame.Rect(self.battle_box.left, y, self.battle_box.width, 20)
                    self.bullets.append(Bullet(rect, 0, 0, b_type="laser", active_color=(148, 0, 211))) # Dark Violet
                else:
                    # Vertical
                    x = random.randint(self.battle_box.left, self.battle_box.right - 20)
                    rect = pygame.Rect(x, self.battle_box.top, 20, self.battle_box.height)
                    self.bullets.append(Bullet(rect, 0, 0, b_type="laser", active_color=(148, 0, 211)))

        # Escape Dust (Skill A for Abandoned Robot)
        if "escape_dust" in self.active_skills:
            # Spawn 5 Dusts at the beginning (Frame 1)
            if time_elapsed == 1:
                self.dusts = [] # Clear previous if any
                for _ in range(5):
                    # Random position within box (safe margin)
                    rx = random.randint(self.battle_box.left + 30, self.battle_box.right - 30)
                    ry = random.randint(self.battle_box.top + 30, self.battle_box.bottom - 30)
                    self.dusts.append(BattleDust(rx, ry))
            
            # Check Victory Condition - REMOVED per user request
            # Instead, we check at the end of the turn (timer <= 0) if any dusts remain uncollected.
            pass
