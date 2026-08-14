import pygame
import random
import math
from engine.utils import resource_path, get_font
from engine.config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_SNOW, COLOR_SHADOW, COLOR_WHITE

class FogGate:
    def __init__(self, rect):
        self.rect = rect
        self.particles = []
        self.max_particles = 80
        self.timer = 0
        
        # Pre-render fog drop (Radial Gradient)
        self.base_size = 64
        self.fog_surface = pygame.Surface((self.base_size, self.base_size), pygame.SRCALPHA)
        center = (self.base_size // 2, self.base_size // 2)
        max_radius = self.base_size // 2
        
        # Draw radial gradient
        for r in range(max_radius, 0, -1):
            # Alpha fade from center (approx 150) to edge (0)
            alpha = int(150 * (1 - (r / max_radius)**2)) # Quadratic falloff for softer edge
            color = (180, 200, 220, alpha) # Misty Blue-Grey
            pygame.draw.circle(self.fog_surface, color, center, r)

    def update(self):
        # Time progression
        self.timer += 0.05
        
        # Maintain particle count
        while len(self.particles) < self.max_particles:
            # Random position within rect
            x = random.randint(self.rect.left, self.rect.right)
            y = random.randint(self.rect.top, self.rect.bottom)
            
            # Properties: [base_x, y, speed_factor, phase_offset, size_scale]
            speed = random.uniform(0.5, 2.0)
            offset = random.uniform(0, 6.28)
            scale = random.uniform(0.6, 1.2)
            
            self.particles.append([x, y, speed, offset, scale])

    def draw(self, screen, camera):
        for p in self.particles:
            base_x, y, speed, offset, scale = p
            
            # 1. Breathing Effect (Alpha)
            # sin varies -1 to 1. Normalize to 0 to 1.
            alpha_factor = (math.sin(self.timer * speed + offset) + 1) / 2
            # Min alpha threshold to prevent total invisibility if desired, or let it fade out completely
            current_alpha = int(255 * alpha_factor)
            
            # 2. Turbulence (X Position)
            # Oscillate around base_x
            x_wobble = math.sin(self.timer * 2 + offset) * 8 # +/- 8 pixels
            current_x = base_x + x_wobble
            
            # Apply Camera
            # Assuming camera.camera is the Rect with offset
            screen_x = current_x + camera.camera.x
            screen_y = y + camera.camera.y
            
            # Check if on screen (Optimization)
            if -self.base_size < screen_x < SCREEN_WIDTH and -self.base_size < screen_y < SCREEN_HEIGHT:
                # Set Alpha
                self.fog_surface.set_alpha(current_alpha)
                
                # Draw (centered)
                # We could scale here if needed, but simple blit is faster
                # If we want scale, we need transform.scale
                if scale != 1.0:
                    scaled_size = int(self.base_size * scale)
                    # Scaling every frame is costly. For 80 particles it might be okay.
                    # Let's try to avoid it if possible, or accept the cost.
                    # Given the constraints, let's just use the base surface to ensure high FPS.
                    # Or do a cheap scale?
                    # Let's skip scaling for now to ensure "No lag" / safety. 
                    # The user asked for "Particle animation" not "scaling animation".
                    pass
                
                dest_x = screen_x - self.base_size // 2
                dest_y = screen_y - self.base_size // 2
                screen.blit(self.fog_surface, (dest_x, dest_y))

class FogWall(FogGate):
    def __init__(self, rect, visible=True):
        super().__init__(rect)
        self.visible = visible
        self.max_particles = 100
        
        # Override fog_surface with BLACK gradient
        self.fog_surface = pygame.Surface((self.base_size, self.base_size), pygame.SRCALPHA)
        center = (self.base_size // 2, self.base_size // 2)
        max_radius = self.base_size // 2
        
        for r in range(max_radius, 0, -1):
            alpha = int(40 * (1 - (r / max_radius)**2)) 
            color = (10, 10, 10, alpha) # Dark Black
            pygame.draw.circle(self.fog_surface, color, center, r)

    def update(self):
        if not self.visible:
            return
        super().update()

    def draw(self, screen, camera):
        if not self.visible:
            return
        super().draw(screen, camera)

class SnowFlake:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.speed = random.randint(1, 3)
        self.size = random.randint(1, 3)

    def update(self):
        self.y += self.speed
        if self.y > SCREEN_HEIGHT:
            self.y = 0
            self.x = random.randint(0, SCREEN_WIDTH)

    def draw(self, surface):
        pygame.draw.circle(surface, COLOR_SNOW, (self.x, self.y), self.size)

class DataDust:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        # Bias towards bottom: random^0.5 or similar, or just uniform for now and handle fade
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.speed_y = random.uniform(0.2, 0.5) # Slow rise
        self.speed_x = random.uniform(-0.2, 0.2) # Horizontal drift
        self.size = random.randint(1, 3) # 1-3 pixels
        # Pale Cyan (175, 238, 238) to White
        if random.random() > 0.8:
            self.color = (255, 255, 255) # Highlight
        else:
            self.color = (175, 238, 238) # Pale Cyan
            
        self.base_alpha = random.randint(50, 150)
        self.image = pygame.Surface((self.size, self.size))
        self.image.fill(self.color)

    def update(self):
        self.y -= self.speed_y
        self.x += self.speed_x
        
        # Reset if out of bounds (Top)
        if self.y < 0:
            self.y = SCREEN_HEIGHT
            self.x = random.randint(0, SCREEN_WIDTH)
            
        # Wrap horizontal
        if self.x < 0: self.x = SCREEN_WIDTH
        elif self.x > SCREEN_WIDTH: self.x = 0

    def draw(self, surface):
        # Calculate alpha based on height (fades as it goes up)
        # Bottom (Height) -> Alpha = Base
        # Top (0) -> Alpha = 0
        height_factor = self.y / SCREEN_HEIGHT
        current_alpha = int(self.base_alpha * height_factor)
        
        if current_alpha > 0:
            self.image.set_alpha(current_alpha)
            surface.blit(self.image, (self.x, self.y))

class AreaTitle:
    def __init__(self, screen, text):
        self.screen = screen
        self.text = text
        try:
            self.font = get_font(80)
        except:
            self.font = pygame.font.Font(None, 80)
            
        self.surf = self.font.render(text, True, COLOR_WHITE)
        self.rect = self.surf.get_rect(center=(screen.get_width()//2, screen.get_height()//2))
        
        self.timer = 0
        self.duration = 240 # 4 seconds
        self.fade_in = 60
        self.hold = 120
        self.fade_out = 60
        self.active = False
        
        # Animation params
        self.slide_distance = 100 # Slide from left (-100px)
        
        # Sound Effect
        try:
            # User noted "Map broadcast SFX" missing. 
            # 'new map.mp3' is located in audio/bgm/ according to file list
            self.sound = pygame.mixer.Sound(resource_path("audio/bgm/new_map.mp3"))
            self.sound.set_volume(0.5)
        except Exception as e:
            print(f"Warning: Failed to load new map sound: {e}")
            self.sound = None
        
    def set_text(self, text):
        self.text = text
        self.surf = self.font.render(text, True, COLOR_WHITE)
        self.rect = self.surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2))
        # Reset animation state
        self.timer = 0
        if self.active:
            # If already active, restart animation (fade in)
            pass
        else:
            self.active = True # Only if we want to show it immediately? Usually show() is called after.
        
        # Actually, show() sets active=True and timer=0. 
        # But if we change text while active, we probably want to restart animation.
        # Let's make set_text just update text, and rely on show() to trigger.
        # BUT load_map calls set_text then show.
        # If we overlap, load_map calls set_text (updates text) then show (resets timer).
        # So overlapping should work if show() resets timer.
        
    def show(self):
        self.active = True
        self.timer = 0
        if self.sound:
            self.sound.stop()
            self.sound.play()

    def hide(self):
        self.active = False
        if self.sound:
            self.sound.stop()
        
    def update(self):
        if self.active:
            self.timer += 1
            if self.timer >= self.duration:
                self.active = False
                
    def draw(self):
        if self.active:
            alpha = 255
            offset_x = 0
            
            # Animation Logic
            if self.timer < self.fade_in:
                # Fade In + Slide In
                progress = self.timer / self.fade_in
                alpha = int(255 * progress)
                # Ease out cubic for slide: 1 - (1-t)^3
                slide_progress = 1 - pow(1 - progress, 3)
                offset_x = -self.slide_distance * (1 - slide_progress)
            elif self.timer > self.duration - self.fade_out:
                # Fade Out
                remaining = self.duration - self.timer
                alpha = int(255 * (remaining / self.fade_out))
            
            # 1. Background Strip
            strip_height = 80
            strip_y = self.rect.centery - strip_height // 2
            strip_surf = pygame.Surface((self.screen.get_width(), strip_height))
            strip_surf.fill((0, 0, 0))
            # Strip alpha should be lower than text (e.g., max 150), and fade with it
            strip_alpha = int(150 * (alpha / 255)) 
            strip_surf.set_alpha(strip_alpha)
            self.screen.blit(strip_surf, (0, strip_y))
            
            # 2. Text Drawing
            current_x = self.rect.x + offset_x
            current_y = self.rect.y
            
            # Create temp surfaces for alpha
            text_surf = self.surf.copy()
            text_surf.set_alpha(alpha)
            
            shadow_surf = self.font.render(self.text, True, COLOR_SHADOW)
            shadow_surf.set_alpha(alpha)
            
            # Draw Shadow (Offset +2)
            self.screen.blit(shadow_surf, (current_x + 2, current_y + 2))
            
            # Draw Main Text
            self.screen.blit(text_surf, (current_x, current_y))


class ExitGlow:
    """出口「数据缝」微光 + 朝出口飘的数据粒子，标识可通行方向。

    edge: "left" / "right" / "top" / "bottom"
    start, end: 该边上可通行段的起止坐标（6x6 地图无滚动，屏幕坐标==世界坐标）
    locked: True 显示红色（锁门，需液氮核心），否则蓝青色
    """
    GLOW_COLOR = (0, 200, 255)     # 蓝青（可走出口）
    LOCKED_COLOR = (255, 80, 80)   # 红（锁门，未解锁）
    THICKNESS = 40                 # 微光向内延伸的宽度（px）
    MAX_ALPHA = 90                 # 普通出口最亮处的 alpha
    LOCKED_MAX_ALPHA = 170         # 锁门更亮，作为醒目的警告

    def __init__(self, edge, start=0, end=SCREEN_HEIGHT, locked=False):
        self.edge = edge
        self.start = start
        self.end = end
        self.locked = locked
        self.color = self.LOCKED_COLOR if locked else self.GLOW_COLOR
        self.max_alpha = self.LOCKED_MAX_ALPHA if locked else self.MAX_ALPHA
        self.timer = 0.0
        self.particles = []
        self.max_particles = 36
        self.glow_surface = self._build_glow()

    def _build_glow(self):
        length = self.end - self.start
        if self.edge in ("right", "left"):
            w, h = self.THICKNESS, length
        else:
            w, h = length, self.THICKNESS

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(self.THICKNESS):
            t = (i + 1) / self.THICKNESS          # 0..1，越靠近边缘越大
            alpha = int(self.max_alpha * t * t)   # 二次衰减，边缘最亮、向内柔和
            color = self.color + (alpha,)
            if self.edge == "right":
                pygame.draw.line(surf, color, (i, 0), (i, h))
            elif self.edge == "left":
                pygame.draw.line(surf, color, (self.THICKNESS - 1 - i, 0), (self.THICKNESS - 1 - i, h))
            elif self.edge == "bottom":
                pygame.draw.line(surf, color, (0, i), (w, i))
            else:  # top
                pygame.draw.line(surf, color, (0, self.THICKNESS - 1 - i), (w, self.THICKNESS - 1 - i))
        return surf

    def _pos(self):
        if self.edge == "right":
            return (SCREEN_WIDTH - self.THICKNESS, self.start)
        if self.edge == "left":
            return (0, self.start)
        if self.edge == "bottom":
            return (self.start, SCREEN_HEIGHT - self.THICKNESS)
        return (self.start, 0)  # top

    def _spawn_particle(self):
        size = random.randint(1, 3)
        img = pygame.Surface((size, size), pygame.SRCALPHA)
        img.fill(self.color)
        if self.edge in ("right", "left"):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(self.start, self.end)
        else:
            x = random.randint(self.start, self.end)
            y = random.randint(0, SCREEN_HEIGHT)
        return {
            "x": float(x), "y": float(y), "img": img,
            "speed": random.uniform(0.8, 2.2),
            "phase": random.uniform(0, 6.28),
            "base_alpha": random.randint(40, 90),
        }

    def update(self):
        self.timer += 0.05
        while len(self.particles) < self.max_particles:
            self.particles.append(self._spawn_particle())

        for p in self.particles:
            if self.edge == "right":
                p["x"] += p["speed"]
                if p["x"] > SCREEN_WIDTH:
                    p["x"] = 0.0
                    p["y"] = float(random.randint(self.start, self.end))
            elif self.edge == "left":
                p["x"] -= p["speed"]
                if p["x"] < 0:
                    p["x"] = float(SCREEN_WIDTH)
                    p["y"] = float(random.randint(self.start, self.end))
            elif self.edge == "bottom":
                p["y"] += p["speed"]
                if p["y"] > SCREEN_HEIGHT:
                    p["y"] = 0.0
                    p["x"] = float(random.randint(self.start, self.end))
            else:  # top
                p["y"] -= p["speed"]
                if p["y"] < 0:
                    p["y"] = float(SCREEN_HEIGHT)
                    p["x"] = float(random.randint(self.start, self.end))

    def draw(self, screen):
        surf = self.glow_surface
        if self.locked:
            # 锁门呼吸闪烁，吸引注意；拿到核心解锁后自动停（变稳定蓝光）
            pulse = int(200 + 55 * math.sin(self.timer * 2))
            surf.set_alpha(pulse)
        else:
            surf.set_alpha(255)
        screen.blit(surf, self._pos())
        for p in self.particles:
            alpha = int(p["base_alpha"] * (0.5 + 0.5 * math.sin(self.timer * 2 + p["phase"])))
            if alpha > 0:
                p["img"].set_alpha(alpha)
                screen.blit(p["img"], (int(p["x"]), int(p["y"])))
