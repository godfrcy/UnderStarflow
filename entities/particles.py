import pygame
import random
import math


class BattleDust:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 14, 14)
        self.x = float(x)
        self.y = float(y)
        self.is_collected = False
        self.shiver_offset = [0, 0]
        self.color = (169, 169, 169) # Grey

    def update(self, player_rect, battle_box):
        if self.is_collected: return

        # Distance to player
        dx = self.x - player_rect.centerx
        dy = self.y - player_rect.centery
        dist = math.hypot(dx, dy)

        # Flee logic (distance < 50)
        if dist < 50:
            speed = 3.0
            if dist > 0:
                # Move AWAY from player (minus dx/dy) -> No, vector from player TO dust is (self.x - px).
                # dx is (self.x - px). So normalizing dx gives direction AWAY from player.
                vx = (dx / dist) * speed
                vy = (dy / dist) * speed
                self.x += vx
                self.y += vy

                # Clamp
                self.x = max(battle_box.left, min(self.x, battle_box.right - self.rect.width))
                self.y = max(battle_box.top, min(self.y, battle_box.bottom - self.rect.height))

            # Shiver
            self.shiver_offset = [random.randint(-1, 1), random.randint(-1, 1)]
        else:
            self.shiver_offset = [0, 0]

        self.rect.x = int(self.x + self.shiver_offset[0])
        self.rect.y = int(self.y + self.shiver_offset[1])

    def draw(self, surface):
        if self.is_collected: return
        pygame.draw.rect(surface, self.color, self.rect)


class DebrisParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.timer = 20
        self.color = (200, 200, 200)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.timer -= 1

    def draw(self, surface):
        if self.timer > 0:
            alpha = int((self.timer / 20) * 255)
            s = pygame.Surface((4, 4))
            s.set_alpha(alpha)
            s.fill(self.color)
            surface.blit(s, (self.x, self.y))
