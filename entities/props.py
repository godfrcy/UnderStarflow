import pygame
import os
from engine.utils import resource_path


class Prop(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, scale=1.0, hitbox_shrink=None):
        super().__init__()
        try:
            full_path = resource_path(image_path)
            if not os.path.exists(full_path):
                 # Fallback to check assetsDB in root if not found
                 root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                 alt_path = os.path.join(root_dir, image_path)
                 if os.path.exists(alt_path):
                     full_path = alt_path

            self.image = pygame.image.load(full_path).convert_alpha()
            if scale != 1.0:
                self.image = pygame.transform.scale(self.image, (int(self.image.get_width() * scale), int(self.image.get_height() * scale)))
            self.rect = self.image.get_rect()
            self.rect.center = (x, y)

            if hitbox_shrink:
                # shrink is (w_shrink, h_shrink)
                # inflate by negative values to shrink
                self.hitbox = self.rect.inflate(-hitbox_shrink[0], -hitbox_shrink[1])
            else:
                self.hitbox = self.rect.copy() # For collision
        except Exception as e:
            print(f"Error loading prop {image_path}: {e}")
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 0, 255)) # Magenta placeholder
            self.rect = self.image.get_rect()
            self.rect.center = (x, y)
            self.hitbox = self.rect
