import pygame
import math
from engine.utils import resource_path
from engine.config import RENDER_TILE_SIZE

class Collectible(pygame.sprite.Sprite):
    def __init__(self, x, y, anim_folder_name, sound_file=None, item_id=None, item_data=None, scale=1.0):
        super().__init__()
        self.x = x
        self.y = y
        self.item_id = item_id # Unique ID for persistence
        self.item_data = item_data # Data for inventory (e.g. {"name": "Battery", "type": "consumable", "effect": ...})
        self.width = int(RENDER_TILE_SIZE * scale)
        self.height = int(RENDER_TILE_SIZE * scale)
        self.rect = pygame.Rect(x, y, self.width, self.height)
        
        # Correction for centering if scaled (Optional, but fixes "offset" issues)
        if scale != 1.0:
             # Center within the tile if it was placed at tile origin
             # Assumption: x, y passed are top-left of the TILE.
             # But main.py passes 128*2, 128*5.
             # If we just shrink rect, it stays at top-left.
             # Center offset: (TileSize - ItemSize) / 2
             offset = (RENDER_TILE_SIZE - self.width) // 2
             self.rect.x += offset
             self.rect.y += offset
        
        # Animation
        self.frames = []
        self.frame_index = 0
        self.animation_speed = 0.15
        self.last_update_time = pygame.time.get_ticks()
        
        self.load_animation(anim_folder_name)
        
        if self.frames:
            self.image = self.frames[0].copy()
        else:
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill((0, 255, 255)) # Cyan placeholder
            
        # Pulse Effect
        self.pulse_timer = 0
            
        # Sound
        self.sound_file = sound_file
        self.sound = None
        if sound_file:
            try:
                self.sound = pygame.mixer.Sound(resource_path(sound_file))
            except Exception as e:
                print(f"Failed to load item sound: {e}")

        self.collected = False

    def load_animation(self, folder_name):
        try:
            path = resource_path(folder_name)
            import os
            if os.path.exists(path):
                files = sorted([f for f in os.listdir(path) if f.endswith('.png')])
                for f in files:
                    img = pygame.image.load(os.path.join(path, f)).convert_alpha()
                    img = pygame.transform.scale(img, (self.width, self.height))
                    self.frames.append(img)
            else:
                print(f"Collectible animation folder not found: {path}")
        except Exception as e:
            print(f"Error loading collectible animation: {e}")

    def update(self):
        if self.collected:
            self.kill()
            return

        # Animation loop
        if self.frames:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_update_time > self.animation_speed * 1000:
                self.frame_index = (self.frame_index + 1) % len(self.frames)
                self.last_update_time = current_time
            
            # Base image from animation
            base_image = self.frames[self.frame_index].copy()
            
            # Pulse Effect
            self.pulse_timer += 0.1
            # Sin wave: -1 to 1 -> 0 to 1 -> 0 to max_alpha
            pulse_val = (math.sin(self.pulse_timer) + 1) * 0.5 
            max_alpha = 150 # Max added brightness (0-255)
            alpha = int(pulse_val * max_alpha)
            
            if alpha > 0:
                # Create a mask from the base image (perfect silhouette)
                mask = pygame.mask.from_surface(base_image)
                # Convert mask to a white surface with the calculated alpha
                flash_surf = mask.to_surface(setcolor=(255, 255, 255, alpha), unsetcolor=(0, 0, 0, 0))
                # Blit the flash surface onto the base image
                base_image.blit(flash_surf, (0, 0))
            
            self.image = base_image

    def interact(self):
        if not self.collected:
            self.collected = True
            if self.sound:
                self.sound.play()
            print(f"Collected item at {self.rect}")
            # Add specific logic here (e.g. add to inventory) if needed later
