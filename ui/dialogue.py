import pygame
from engine.utils import resource_path, get_font
from engine import config

class DialogueSystem:
    def __init__(self):
        self.active = False
        self.text_lines = []
        self.current_line_index = 0
        self.font = get_font(24)
        
        # Load Assets
        try:
            self.portrait_img = pygame.image.load(resource_path("ui/portraits/anthe_portrait.png")).convert_alpha()
            # self.box_img is deprecated as per user request
            self.frame_img = pygame.image.load(resource_path("ui/portraits/portrait_frame.png")).convert_alpha()
        except Exception as e:
            print(f"Error loading dialogue assets: {e}")
            # Fallbacks
            self.portrait_img = pygame.Surface((80, 80))
            self.portrait_img.fill((200, 200, 200))
            self.frame_img = pygame.Surface((100, 100))
            self.frame_img.set_colorkey((0,0,0)) 
            pygame.draw.rect(self.frame_img, (100, 100, 100), (0,0,100,100), 5)

        # Setup Layout
        self.setup_layout()

    def setup_layout(self):
        screen_w = config.SCREEN_WIDTH
        screen_h = config.SCREEN_HEIGHT
        
        # 1. Main Container Height: Bottom 1/4 of screen
        container_h = screen_h // 4
        container_y = screen_h - container_h
        
        # 2. Avatar Frame Setup
        # Scale frame to fit comfortably within the height (e.g., 90% of container height)
        f_target_h = int(container_h * 0.9)
        f_rect = self.frame_img.get_rect()
        f_scale = f_target_h / f_rect.height
        f_new_w = int(f_rect.width * f_scale)
        f_new_h = int(f_rect.height * f_scale)
        
        self.frame_surf = pygame.transform.scale(self.frame_img, (f_new_w, f_new_h))
        
        # Position Frame: Left margin, vertically centered in container
        margin_left = 30 # Symmetric margin
        frame_x = margin_left
        frame_y = container_y + (container_h - f_new_h) // 2
        self.frame_rect = self.frame_surf.get_rect(topleft=(frame_x, frame_y))
        
        # 3. Portrait Setup
        # Scale portrait to fit frame, then reduce by 15%
        p_rect = self.portrait_img.get_rect()
        
        # Fit portrait to frame rect
        p_scale_w = self.frame_rect.width / p_rect.width
        p_scale_h = self.frame_rect.height / p_rect.height
        base_scale = min(p_scale_w, p_scale_h)
        
        # Apply additional 5% reduction (multiply by 0.80)
        final_scale = base_scale * 0.80
        
        p_new_w = int(p_rect.width * final_scale)
        p_new_h = int(p_rect.height * final_scale)
        
        self.portrait_surf = pygame.transform.scale(self.portrait_img, (p_new_w, p_new_h))
        self.portrait_rect = self.portrait_surf.get_rect(center=self.frame_rect.center)
        
        # 4. Text Area Background (Black Box)
        # Position: Right of frame
        # Height: Similar to frame (let's match frame height or container height? User said "similar range")
        # Let's use container height for better visual grounding, or match frame height.
        # User said "height and avatar frame covered range similar".
        # Let's match the frame height.
        bg_height = f_new_h
        bg_y = frame_y # Align with frame top
        
        # Width: Symmetric margin on the right. 
        # Left side starts at frame_rect.right + gap? Or attached?
        # User said "generate black background on the right side of avatar frame".
        # User said "margin and avatar frame left side symmetric".
        # This implies: Right Margin = Left Margin = 30.
        
        bg_x = self.frame_rect.right
        bg_width = screen_w - bg_x - margin_left
        
        self.text_bg_rect = pygame.Rect(bg_x, bg_y, bg_width, bg_height)
        
        # Text Area inside the black box
        self.text_area_rect = self.text_bg_rect.copy()

    def start_dialogue(self, text_list):
        self.text_lines = text_list
        self.current_line_index = 0
        self.active = True
        
    def handle_event(self, event):
        if not self.active:
            return False
            
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                self.current_line_index += 1
                if self.current_line_index >= len(self.text_lines):
                    self.active = False
                return True
        return False

    def draw(self, surface):
        # 物理保险：如果没有台词，绝对不允许处于 active 状态
        if not self.text_lines or self.current_line_index >= len(self.text_lines):
            self.active = False
            return

        if not self.active:
            return
            
        # 1. Draw Text Background (Black Box)
        pygame.draw.rect(surface, (0, 0, 0), self.text_bg_rect)
        
        # 2. Draw Frame (Bottom Layer, if portrait needs to be on top)
        # User said "Portrait layer is covered by frame", implying they want portrait VISIBLE.
        # So we draw frame first (background), then portrait on top?
        # Or if frame is a border, portrait should be inside.
        # But if frame covers portrait, maybe portrait is too big or frame center is opaque.
        # To be safe and ensure portrait is seen: Draw Frame -> Draw Portrait.
        surface.blit(self.frame_surf, self.frame_rect)
        
        # 3. Draw Portrait (Top Layer)
        surface.blit(self.portrait_surf, self.portrait_rect)
        
        # 4. Draw Text
        if self.text_lines and self.current_line_index < len(self.text_lines):
            text = self.text_lines[self.current_line_index]
            text_surf = self.font.render(text, True, (255, 255, 255))
            
            # Position text: Inside Text Area, with padding
            text_x = self.text_area_rect.left + 20
            text_y = self.text_area_rect.top + 20
            
            surface.blit(text_surf, (text_x, text_y))
