import pygame
import random
import math
from engine.config import SCREEN_WIDTH, SCREEN_HEIGHT


# --- Pipe Atmosphere System ---
class PipeAtmosphere:
    def __init__(self):
        self.particles = []

        # --- Horizontal Overlays (Existing) ---
        # Top Overlay: 0 to 2*TILE_SIZE (256)
        self.overlay_top = pygame.Surface((SCREEN_WIDTH, 2 * 128), pygame.SRCALPHA)
        for y in range(2 * 128):
            alpha = 220
            if y > (2 * 128 - 32):
                ratio = (y - (2 * 128 - 32)) / 32
                alpha = int(220 - (120 * ratio))
            pygame.draw.line(self.overlay_top, (0, 0, 0, alpha), (0, y), (SCREEN_WIDTH, y))

        # Bottom Overlay: 4*TILE_SIZE (512) to 6*TILE_SIZE (768)
        self.overlay_bottom = pygame.Surface((SCREEN_WIDTH, 2 * 128), pygame.SRCALPHA)
        for y in range(2 * 128):
            alpha = 220
            if y < 32:
                ratio = y / 32
                alpha = int(100 + (120 * ratio))
            pygame.draw.line(self.overlay_bottom, (0, 0, 0, alpha), (0, y), (SCREEN_WIDTH, y))

        self.overlay_middle = pygame.Surface((SCREEN_WIDTH, 2 * 128))
        self.overlay_middle.fill((0, 0, 0))
        self.overlay_middle.set_alpha(100)

        # --- Vertical Overlays (New Requirement) ---
        # Left Overlay: Cols 0-1 (x=0 to 256)
        # Alpha 240
        self.overlay_left = pygame.Surface((2 * 128, SCREEN_HEIGHT))
        self.overlay_left.fill((0, 0, 0))
        self.overlay_left.set_alpha(240)

        # Right Overlay: Cols 4-5 (x=512 to 768)
        # Alpha 240
        self.overlay_right = pygame.Surface((2 * 128, SCREEN_HEIGHT))
        self.overlay_right.fill((0, 0, 0))
        self.overlay_right.set_alpha(240)

        # Middle Vertical Darkening: Cols 2-3 (x=256 to 512)
        # Alpha 120
        self.overlay_middle_v = pygame.Surface((2 * 128, SCREEN_HEIGHT))
        self.overlay_middle_v.fill((0, 0, 0))
        self.overlay_middle_v.set_alpha(120)

    def update(self, mode="horizontal"):
        # Manage particles
        if len(self.particles) < 50:
            if pygame.time.get_ticks() % 5 == 0:
                 if mode == "horizontal":
                     # y range: 2*128 to 4*128
                     x = random.randint(0, SCREEN_WIDTH)
                     y = random.randint(2 * 128, 4 * 128)
                     vx = random.uniform(-0.5, 0.5)
                     vy = random.uniform(-0.2, 0.2)
                 else:
                     # Vertical Mode
                     # x range: 2*128 to 4*128 (256 to 512)
                     x = random.randint(2 * 128, 4 * 128)
                     y = random.randint(0, SCREEN_HEIGHT) # Full height
                     # vy > vx, gentle fall
                     vx = random.uniform(-0.2, 0.2)
                     vy = random.uniform(0.5, 1.5) # Falling down

                 self.particles.append({
                     "x": float(x),
                     "y": float(y),
                     "vx": vx,
                     "vy": vy,
                     "life": 255,
                     "radius": random.randint(1, 2)
                 })

        # Update particles
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 2 # Decay

            # Wrap or Kill? Original code kills.
            # Let's keep it consistent.
            if p["life"] <= 0:
                self.particles.remove(p)
            elif mode == "vertical":
                # Wrap vertical particles for continuous flow if they go off screen?
                # Or just let them die. The generator will replace them.
                # Just need to check bounds if we want strict containment
                pass

    def draw(self, surface, mode="horizontal"):
        if mode == "horizontal":
            # Draw overlays
            # Top: 0 to 2*TILE_SIZE (256)
            surface.blit(self.overlay_top, (0, 0))

            # Bottom: 4*TILE_SIZE (512) to 6*TILE_SIZE (768)
            surface.blit(self.overlay_bottom, (0, 4 * 128))

            # Middle Darkening
            surface.blit(self.overlay_middle, (0, 2 * 128))

        elif mode == "vertical":
            # Left: 0 to 256
            surface.blit(self.overlay_left, (0, 0))
            # Right: 512 to 768
            surface.blit(self.overlay_right, (4 * 128, 0))
            # Middle: 256 to 512
            surface.blit(self.overlay_middle_v, (2 * 128, 0))

        # Draw particles
        for p in self.particles:
            color = (0, 0, 0, p["life"]) # Black Atmospheric Dust
            # Need a surface for alpha
            s = pygame.Surface((p["radius"]*2, p["radius"]*2), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (p["radius"], p["radius"]), p["radius"])
            surface.blit(s, (int(p["x"]), int(p["y"])))


# --- Pulse Atmosphere System (Red/Blue Crisis) ---
class PulseAtmosphere:
    def __init__(self):
        self.surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.flash_timer = 0
        self.last_sign = 0

    def update(self, speed=0.002):
        current_time = pygame.time.get_ticks()
        # speed parameter is now used instead of hardcoded variable

        # Sin Wave: -1 to 1
        raw_val = math.sin(current_time * speed)

        # Determine Color and Alpha
        # Red Phase: Positive
        # Blue Phase: Negative
        if raw_val >= 0:
            color = (200, 0, 0)
        else:
            color = (0, 0, 200)

        # Alpha: 60 - 120 based on amplitude (abs(raw_val))
        # 0 -> 60, 1 -> 120
        alpha = int(60 + abs(raw_val) * 60)

        # Fill Surface
        self.surface.fill(color)
        self.surface.set_alpha(alpha)

        # White Flash Logic (Simulate Short Circuit)
        # Detect sign change (Zero Crossing)
        current_sign = 1 if raw_val >= 0 else -1
        if self.last_sign != 0 and current_sign != self.last_sign:
            # Trigger Flash (1-2 frames)
            self.flash_timer = random.randint(1, 2)

        self.last_sign = current_sign

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))

        # Draw Flash
        if self.flash_timer > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash_surf.fill((255, 255, 255))
            flash_surf.set_alpha(30)
            screen.blit(flash_surf, (0, 0))
            self.flash_timer -= 1


# --- Fog Maze System (Pipe Nightmare 1-3) ---
class FogMaze:
    def __init__(self):
        self.fog_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.light_mask = self._generate_light_mask()
        self.fog_texture = self._generate_fog_texture()

    def _generate_light_mask(self):
        size = 300
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))

        center = (size // 2, size // 2)
        max_radius = size // 2

        # Create gradient mask
        for x in range(size):
            for y in range(size):
                dx = x - center[0]
                dy = y - center[1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < max_radius:
                    ratio = dist / max_radius
                    # Alpha 0 at center (transparent in result), 255 at edge (opaque in result)
                    alpha = int(255 * (ratio ** 2))
                    surf.set_at((x, y), (255, 255, 255, alpha))
        return surf

    def _generate_fog_texture(self):
        # Generate a static fog texture resembling the FogWall (black particles)
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        # Fill with a base dark semi-transparent black
        surf.fill((0, 0, 0, 240))

        # Add some "cloud" texture using particles logic (static)
        base_size = 64
        particle_surf = pygame.Surface((base_size, base_size), pygame.SRCALPHA)
        center = (base_size // 2, base_size // 2)
        max_radius = base_size // 2

        # Draw one particle template (Black Gradient)
        for r in range(max_radius, 0, -1):
            alpha = int(40 * (1 - (r / max_radius)**2))
            color = (10, 10, 10, alpha) # Dark Black
            pygame.draw.circle(particle_surf, color, center, r)

        # Scatter them across the screen to create texture
        for _ in range(200):
            x = random.randint(-50, SCREEN_WIDTH + 50)
            y = random.randint(-50, SCREEN_HEIGHT + 50)
            surf.blit(particle_surf, (x, y))

        return surf

    def draw(self, screen, player_rect_screen):
        # 0. Clear Surface
        self.fog_surface.fill((0, 0, 0, 0))

        # 1. Use the pre-generated Fog Texture
        self.fog_surface.blit(self.fog_texture, (0, 0))

        # 2. Blit Light Mask at Player Position using MIN
        dest_x = player_rect_screen.centerx - self.light_mask.get_width() // 2
        dest_y = player_rect_screen.centery - self.light_mask.get_height() // 2

        self.fog_surface.blit(self.light_mask, (dest_x, dest_y), special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(self.fog_surface, (0, 0))
