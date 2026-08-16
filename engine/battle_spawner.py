import pygame
import random
import math
from engine.config import *
from entities.bullets import Bullet, PlasmaBlade, LaserNetworkLine, YellowBullet, UfoLaserColumn, ConveyorScrap, VerticalScrap, GhostSlashZone
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

        # Ghost Slash (幽灵斩：半场预警斩杀 + 横向紫色激光增加躲避难度)
        if "ghost_slash" in self.active_skills:
            if time_elapsed == 1:
                self.bullets.append(GhostSlashZone(self.battle_box, "left"))
            # 横向紫色激光（复用原幽灵斩弹幕，持续压制）
            if time_elapsed % 45 == 0:
                cycle = time_elapsed // 45
                blade_width, blade_height = 150, 40
                speed = 7 * self.bullet_speed_multiplier
                spawn_y = random.randint(self.battle_box.top + 5, self.battle_box.bottom - blade_height - 5)
                c_outer = (138, 43, 226)   # Blue Violet
                c_inner = (230, 230, 250)   # Lavender
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

        # Samurai Gravity Jump (Skill C) — 跳火：双缺口轮换（普通跳/蓄力跳）+ 单侧缺口
        if "samurai_gravity_jump" in self.active_skills:

             # Fire Pillars
             if time_elapsed % 60 == 0: # Every second
                 wave = time_elapsed // 60
                 speed = 4 * self.bullet_speed_multiplier

                 # 红心贴地时中心距底边 = 心高32/2 + 边距5 = 21
                 GROUND_CENTER = 21
                 # 普通跳峰值：v=-9 → 81/1.2 = 67.5；蓄满跳峰值：v=-12 → 144/1.2 = 120
                 normal_peak = (9 * 9) / (2 * self.gravity)
                 charge_peak = (12 * 12) / (2 * self.gravity)

                 # 缺口高度轮换：奇数波低缺口（普通跳）、偶数波高缺口（蓄满跳）
                 if wave % 2 == 1:
                     gap_center_y = (self.battle_box.bottom - GROUND_CENTER) - normal_peak
                 else:
                     gap_center_y = (self.battle_box.bottom - GROUND_CENTER) - charge_peak
                 gap_height = 50 # Size of gap

                 # 单侧缺口：每 3 波出现一次单侧柱（左/右交替），其余双侧
                 spawn_left = True
                 spawn_right = True
                 if wave % 3 == 0:
                     if (wave // 3) % 2 == 0:
                         spawn_right = False  # 只留左侧柱
                     else:
                         spawn_left = False   # 只留右侧柱

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

                 if spawn_left:
                     create_pillar(self.battle_box.left - 20, speed)
                 if spawn_right:
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

        # UFO 牵引：激光列固定，喷完就在同列再喷一次（变速/假动作）；重力列由回合逻辑决定
        if "ufo_tractor" in self.active_skills:
            if not hasattr(self, 'ufo_laser_col'):
                self.ufo_laser_col = random.choice([0, 2])
            if not hasattr(self, 'ufo_gravity_col'):
                self.ufo_gravity_col = random.randint(0, 2)
            if not hasattr(self, 'ufo_purple_timer'):
                self.ufo_purple_timer = 0

            # 只有当上一列喷完（无存活 UfoLaserColumn）才在同列再喷
            laser_alive = any(isinstance(b, UfoLaserColumn) and b.alive for b in self.bullets)
            if not laser_alive:
                col_w = self.battle_box.width // 3
                col_rect = pygame.Rect(
                    self.battle_box.left + self.ufo_laser_col * col_w, self.battle_box.top,
                    col_w, self.battle_box.height)

                # 随机口味：变速（前摇时长变） vs 假动作（喷→停→再喷）
                if random.random() < 0.5:
                    warn = random.choice([30, 120])  # 变速：前摇快 0.5s / 慢 2s
                    self.bullets.append(UfoLaserColumn(col_rect, warning_duration=warn, active_duration=60, pulses=1))
                else:
                    self.bullets.append(UfoLaserColumn(col_rect, warning_duration=60, active_duration=60, pause_duration=60, pulses=2))

            # 安全列（非激光、非重力）刷新紫色竖线子弹，消除「绝对安全区」
            self.ufo_purple_timer += 1
            if self.ufo_purple_timer % 40 == 0:
                safe_cols = [c for c in range(3) if c != self.ufo_laser_col and c != self.ufo_gravity_col]
                if safe_cols:
                    sc = random.choice(safe_cols)
                    col_w = self.battle_box.width // 3
                    col_left = self.battle_box.left + sc * col_w
                    bar_w, bar_h = 12, 36
                    bx = random.randint(col_left + 6, col_left + col_w - bar_w - 6)
                    if random.random() < 0.5:
                        # 自上向下
                        by = self.battle_box.top - bar_h
                        vy = 4
                    else:
                        # 自下向上
                        by = self.battle_box.bottom
                        vy = -4
                    self.bullets.append(Bullet(pygame.Rect(bx, by, bar_w, bar_h), 0, vy, (190, 90, 255), b_type="normal"))

        # 废料传送带（轨道跑酷）：三条虚线轨道，废料沿轨道从左侧横飞，红心上下切轨躲避
        if "conveyor_belt" in self.active_skills:
            if not hasattr(self, 'conveyor_rail_ys'):
                lane_h = self.battle_box.height // 3
                self.conveyor_rail_ys = [self.battle_box.top + lane_h * (i + 0.5) for i in range(3)]
            if not hasattr(self, 'conveyor_spawn_timer'):
                self.conveyor_spawn_timer = 0
            self.conveyor_spawn_timer += 1

            # 公平车流：始终留出至少 1 条空轨保证无伤可能，其余轨按占用情况补料
            if self.conveyor_spawn_timer % 16 == 0:
                # 统计被占用轨道（已驶入或即将驶入的废料所在轨）
                occupied = set()
                for b in self.bullets:
                    if getattr(b, 'type', '') == "conveyor_scrap":
                        for idx, ry in enumerate(self.conveyor_rail_ys):
                            if abs(b.rect.centery - ry) < 10:
                                occupied.add(idx)
                free_rails = [i for i in range(3) if i not in occupied]
                if free_rails:
                    max_n = min(2, len(free_rails) - 1)  # 最多占 2 条，永远留 1 条空
                    n = random.randint(1, max_n) if max_n >= 1 else 0
                    for rail_idx in random.sample(free_rails, n):
                        rail_y = self.conveyor_rail_ys[rail_idx]
                        scrap_w = random.randint(40, 60)
                        scrap_h = 18
                        y = rail_y - scrap_h // 2
                        x = self.battle_box.left - scrap_w
                        speed = random.uniform(4.0, 6.5)
                        self.bullets.append(ConveyorScrap(
                            pygame.Rect(x, y, scrap_w, scrap_h), speed,
                            self.battle_box.left, self.battle_box.right))

        # 单摆（重力摆锤）：废料从顶部下落 / 底部上升，无轨迹线，红心沿圆形轨道摆动躲避
        if "pendulum" in self.active_skills:
            if not hasattr(self, 'pendulum_spawn_timer'):
                self.pendulum_spawn_timer = 0
            self.pendulum_spawn_timer += 1
            if self.pendulum_spawn_timer % 22 == 0:
                if not hasattr(self, 'pend_col_xs'):
                    self.pend_col_xs = [self.battle_box.left + self.battle_box.width * k / 6 for k in range(1, 6)]
                scrap_w = random.randint(16, 24)   # 窄废料
                scrap_h = random.randint(40, 60)
                # 首块废料强制走中间列，逼迫玩家起摆；之后两侧为主、间隙偶尔
                if getattr(self, 'pend_first_scrap', True):
                    lane_cx = self.pend_col_xs[2]  # 中间列
                    self.pend_first_scrap = False
                else:
                    r = random.random()
                    if r < 0.30:
                        lane_cx = self.pend_col_xs[0]  # 列1（左）
                    elif r < 0.60:
                        lane_cx = self.pend_col_xs[4]  # 列3（右）
                    elif r < 0.80:
                        lane_cx = self.pend_col_xs[2]  # 列2（中）
                    elif r < 0.90:
                        lane_cx = self.pend_col_xs[1]  # 间隙 1-2
                    else:
                        lane_cx = self.pend_col_xs[3]  # 间隙 2-3
                sx = lane_cx - scrap_w // 2
                if random.random() < 0.5:
                    # 从顶部下落
                    sy = self.battle_box.top - scrap_h
                    vy = random.uniform(3.0, 5.0)
                else:
                    # 从底部上升
                    sy = self.battle_box.bottom
                    vy = -random.uniform(3.0, 5.0)
                self.bullets.append(VerticalScrap(
                    pygame.Rect(sx, sy, scrap_w, scrap_h), vy,
                    self.battle_box.top, self.battle_box.bottom))

        # 弹簧振子：屏幕上下飞来的竖直激光线（复用机凯种·常量的 LaserNetworkLine，贯穿原战斗框高度）
        if "spring_oscillator" in self.active_skills:
            if not hasattr(self, 'spring_spawn_timer'):
                self.spring_spawn_timer = 0
            self.spring_spawn_timer += 1
            if self.spring_spawn_timer % 70 == 0:
                x = random.randint(self.battle_box.left + 20, self.battle_box.right - 40)
                if hasattr(self, 'original_battle_box') and self.original_battle_box:
                    full_top = self.original_battle_box.top
                    full_h = self.original_battle_box.height
                else:
                    full_top = self.battle_box.top
                    full_h = self.battle_box.height
                self.bullets.append(LaserNetworkLine(
                    pygame.Rect(x - 15, full_top, 30, full_h), 'v'))
