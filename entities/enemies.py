import pygame
import os
import random
import math
from engine.utils import resource_path
from engine.config import RENDER_TILE_SIZE, ENEMY_ANIM_SPEED

class OverworldEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y, folder_name="characters/enemies/variable_anim", file_prefix="variable", is_grid=False, flip_on_load=False, anim_speed_factor=1.0, custom_size=None, is_static=False):
        super().__init__()
        self.custom_size = custom_size
        self.is_static = is_static
        self.file_prefix = file_prefix
        self.is_chasing = False
        self.default_facing = "right"
        self.frames = []
        self.load_frames(folder_name, file_prefix, is_grid, flip_on_load)
        
        # New: Idle Frames Logic (Optional)
        self.frames_idle = []
        if "rebel_leader" in folder_name:
            self.load_idle_frames(folder_name)
        
        self.frame_index = 0
        self.image = self.frames[0] if self.frames else pygame.Surface((64, 64))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.pos = [float(self.rect.x), float(self.rect.y)]
        self.anim_timer = 0
        self.ANIM_SPEED = int(ENEMY_ANIM_SPEED * anim_speed_factor)

    def load_idle_frames(self, folder_name):
        try:
            base_path = resource_path(folder_name)
            if not os.path.exists(base_path):
                 base_path = resource_path(os.path.join("assetsDB", folder_name))
            
            prefix = "c4502f3ac15a46aea1d3e088e3375afd"
            for row in range(2, 4):
                for col in range(1, 5):
                    fname = f"{prefix}_{row}_{col}.png"
                    full_path = os.path.join(base_path, fname)
                    if os.path.exists(full_path):
                        img = pygame.image.load(full_path).convert_alpha()
                        target_w, target_h = 94, 140
                        target_w *= 2 
                        target_h = int(target_h * 1.25)
                        target_w = int(target_w * 0.8)
                        target_h = int(target_h * 0.8)
                        img = pygame.transform.scale(img, (target_w, target_h))
                        self.frames_idle.append(img)
        except Exception as e:
            print(f"Error loading idle frames: {e}")

    def load_frames(self, folder_name, file_prefix, is_grid, flip_on_load=False):
        try:
            is_single_file = False
            base_path = resource_path(folder_name)
            
            if os.path.isfile(base_path):
                is_single_file = True
            elif not os.path.exists(base_path):
                 temp_path = resource_path(os.path.join("assets", folder_name))
                 if os.path.exists(temp_path):
                     base_path = temp_path
                     if os.path.isfile(temp_path):
                        is_single_file = True
                 else:
                     temp_path = resource_path(os.path.join("assetsDB", folder_name))
                     if os.path.exists(temp_path):
                         base_path = temp_path
                         if os.path.isfile(temp_path):
                             is_single_file = True
                     elif os.path.exists(temp_path):
                         base_path = temp_path

            if is_single_file:
                try:
                    sheet = pygame.image.load(base_path).convert_alpha()
                    sheet_w, sheet_h = sheet.get_size()
                    
                    if is_grid:
                        cell_w = sheet_w // 4
                        cell_h = sheet_h // 4
                        for row in range(4):
                            for col in range(4):
                                rect = pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)
                                img = sheet.subsurface(rect)
                                
                                target_w, target_h = RENDER_TILE_SIZE, RENDER_TILE_SIZE
                                if self.custom_size:
                                    target_w, target_h = self.custom_size
                                elif "最后一版" in file_prefix:
                                     target_w, target_h = 94, 140
                                
                                img = pygame.transform.scale(img, (target_w, target_h))
                                if flip_on_load:
                                    img = pygame.transform.flip(img, True, False)
                                self.frames.append(img)
                    else:
                        if flip_on_load:
                            sheet = pygame.transform.flip(sheet, True, False)
                        self.frames.append(sheet)
                except Exception as e:
                    print(f"Failed to load spritesheet {base_path}: {e}")
                return

            if not os.path.exists(base_path):
                return

            if is_grid:
                for row in range(1, 5):
                    for col in range(1, 5):
                        fname = f"{file_prefix}_{row}_{col}.png"
                        full_path = os.path.join(base_path, fname)
                        if os.path.exists(full_path):
                            img = pygame.image.load(full_path).convert_alpha()
                            
                            target_w = RENDER_TILE_SIZE
                            target_h = RENDER_TILE_SIZE
                            
                            if self.custom_size:
                                target_w, target_h = self.custom_size
                            elif "最后一版" in file_prefix:
                                target_w = 94
                                target_h = 140
                            
                            img = pygame.transform.scale(img, (target_w, target_h))
                            self.frames.append(img)
            else:
                # Primary: numbered prefix files
                loaded_any = False
                for i in range(1, 33):
                    fname = f"{file_prefix}_{i}.png" if file_prefix else f"{i}.png"
                    full_path = os.path.join(base_path, fname)
                    if os.path.exists(full_path):
                        img = pygame.image.load(full_path).convert_alpha()
                        target_w = self.custom_size[0] if self.custom_size else RENDER_TILE_SIZE
                        target_h = self.custom_size[1] if self.custom_size else RENDER_TILE_SIZE
                        img = pygame.transform.scale(img, (target_w, target_h))
                        self.frames.append(img)
                        loaded_any = True
                # Fallback: load all pngs in folder sorted
                if not loaded_any:
                    try:
                        files = sorted([f for f in os.listdir(base_path) if f.lower().endswith(".png")])
                        for f in files:
                            fp = os.path.join(base_path, f)
                            img = pygame.image.load(fp).convert_alpha()
                            target_w = self.custom_size[0] if self.custom_size else RENDER_TILE_SIZE
                            target_h = self.custom_size[1] if self.custom_size else RENDER_TILE_SIZE
                            img = pygame.transform.scale(img, (target_w, target_h))
                            self.frames.append(img)
                    except Exception as e:
                        print(f"Folder load failed for {base_path}: {e}")
        except Exception as e:
            print(f"Error loading frames for {folder_name}: {e}")

    def set_wander_behavior(self, min_x, max_x, speed=0.5):
        self.wander_min_x = min_x
        self.wander_max_x = max_x
        self.wander_speed = speed
        self.is_wandering = True
        self.facing_right = True
        self.wander_pos_x = float(self.rect.centerx)

    def update(self, player=None):
        if self.is_static:
            return
        
        if player and getattr(self, 'can_chase', False):
            dist = math.hypot(player.rect.centerx - self.rect.centerx, player.rect.centery - self.rect.centery)
            vr = getattr(self, 'vision_range', 300)
            self.is_chasing = dist < vr
        else:
            self.is_chasing = False

        current_frames = self.frames
        if getattr(self, 'frames_idle', []) and not self.is_chasing and not getattr(self, 'is_wandering', False):
            current_frames = self.frames_idle
        
        # Safety Check: Ensure frame_index is within bounds of current_frames
        if current_frames and self.frame_index >= len(current_frames):
            self.frame_index = 0
            
        self.anim_timer += 1
        if self.anim_timer >= self.ANIM_SPEED:
            self.anim_timer = 0
            if current_frames:
                self.frame_index = (self.frame_index + 1) % len(current_frames)

        if current_frames:
            base_image = current_frames[self.frame_index]
            if self.is_chasing and player:
                if getattr(self, "default_facing", "right") == "right":
                    if player.rect.centerx < self.rect.centerx:
                        self.image = pygame.transform.flip(base_image, True, False)
                    else:
                        self.image = base_image
                else:
                    if player.rect.centerx > self.rect.centerx:
                        self.image = pygame.transform.flip(base_image, True, False)
                    else:
                        self.image = base_image
            elif getattr(self, 'is_wandering', False):
                if not self.facing_right:
                    self.image = pygame.transform.flip(base_image, True, False)
                else:
                    self.image = base_image
            else:
                self.image = base_image
        
        # Re-center rect to avoid offset when switching between idle/chase frames (different sizes)
        # Only re-center if we are not moving (pos tracking logic handles moving)
        # But wait, self.pos tracks topleft. If we change image size, center changes if topleft is constant.
        # We want CENTER to be constant.
        
        # Calculate new rect from new image
        new_rect = self.image.get_rect()
        
        # Restore center from previous rect
        new_rect.center = self.rect.center
        
        # Update rect
        self.rect = new_rect
        
        # Sync pos to new topleft (so movement logic continues from correct new topleft)
        self.pos[0] = float(self.rect.x)
        self.pos[1] = float(self.rect.y)
        
        if self.is_chasing and player:
            dist = math.hypot(player.rect.centerx - self.rect.centerx, player.rect.centery - self.rect.centery)
            if dist < getattr(self, 'vision_range', 300):
                if dist > 10:
                    dx = player.rect.centerx - self.rect.centerx
                    dy = player.rect.centery - self.rect.centery
                    angle = math.atan2(dy, dx)
                    speed = getattr(self, 'chase_speed', 2.0)
                    self.pos[0] += math.cos(angle) * speed
                    self.pos[1] += math.sin(angle) * speed
                    self.rect.x = int(self.pos[0])
                    self.rect.y = int(self.pos[1])
        elif getattr(self, 'is_wandering', False):
            if self.facing_right:
                self.pos[0] += self.wander_speed
                if self.pos[0] >= self.wander_max_x:
                    self.facing_right = False
            else:
                self.pos[0] -= self.wander_speed
                if self.pos[0] <= self.wander_min_x:
                    self.facing_right = True
            self.rect.x = int(self.pos[0])

class Bonfire(OverworldEnemy):
    def __init__(self, x, y):
        super().__init__(x, y, "assetsDB/objects/bonfire", "bonfire", is_grid=False)
        self.ANIM_SPEED = 10
        # Reduce hitbox to a small center point to prevent accidental interaction
        # rect is typically 64x64 or 128x128 depending on scale
        self.hitbox = pygame.Rect(0, 0, 10, 10) 
        self.hitbox.center = self.rect.center

    def update(self, player=None):
        self.anim_timer += 1
        if self.anim_timer >= self.ANIM_SPEED:
            self.anim_timer = 0
            if self.frames:
                self.frame_index = (self.frame_index + 1) % len(self.frames)
                self.image = self.frames[self.frame_index]
        
        # Sync hitbox to center
        self.hitbox.center = self.rect.center

class FailureEnemy(OverworldEnemy):
    def __init__(self, x, y, custom_size=None, is_static=False):
        super().__init__(x, y, "assetsDB/失败之作", "", is_grid=False, custom_size=custom_size, is_static=is_static)
        self.can_chase = True
        self.vision_range = 50 # 接触范围
        self.chase_speed = 4.0
        self.default_facing = "left"
        
        try:
            base_path = resource_path("assetsDB/失败之作")
            files = []
            for i in range(1, 13):
                fname = f"{i:02d}.png"
                p = os.path.join(base_path, fname)
                if os.path.exists(p):
                    files.append(p)
            loaded = []
            for fp in files:
                img = pygame.image.load(fp).convert_alpha()
                target_w = custom_size[0] if custom_size else RENDER_TILE_SIZE
                target_h = custom_size[1] if custom_size else RENDER_TILE_SIZE
                img = pygame.transform.scale(img, (target_w, target_h))
                loaded.append(img)
            if loaded:
                self.frames_idle = [loaded[0]]
                self.frames = loaded[2:12] if len(loaded) >= 12 else loaded[2:]
                if self.frames_idle:
                    self.image = self.frames_idle[0]
        except Exception:
            pass

    def update(self, player=None):
        # Dynamic Vision Range Logic
        # If noise is high, expand vision range to map-wide to force chase
        # Otherwise, revert to touch range (50)
        base_vision = 50
        if player and hasattr(player, 'noise_level') and hasattr(player, 'noise_threshold'):
            if player.noise_level > player.noise_threshold:
                self.vision_range = 2000 # "Hear" the player everywhere
            else:
                self.vision_range = base_vision
                
        # Base update handles movement, animation switching, and flip
        super().update(player)
