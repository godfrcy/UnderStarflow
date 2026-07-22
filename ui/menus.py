import pygame
from engine.utils import resource_path, get_font
import engine.config as config
from engine.config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_SNOW, COLOR_GOLD, COLOR_WHITE
from ui.effects import SnowFlake

class TitleScreen:
    def __init__(self, screen):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.running = True
        self.next_action = None
        
        # 1. 璧勬簮鍔犺浇
        try:
            self.bg_img = pygame.image.load(resource_path("ui/backgrounds/startgame.jpg")).convert()
            self.bg_img = pygame.transform.scale(self.bg_img, (self.width, self.height))
        except Exception as e:
            print(f"Warning: Could not load startgame.jpg: {e}")
            self.bg_img = pygame.Surface((self.width, self.height))
            self.bg_img.fill((20, 20, 30))
            
        # 2. 菜单设置
        self.options = ["开始新游戏", "继续旅程", "离开废墟"]
        self.selected_index = 0
        try:
            self.font = get_font(40)
            self.font_selected = get_font(48) # 选中变大
        except:
            self.font = pygame.font.Font(None, 40)
            self.font_selected = pygame.font.Font(None, 48)
            
        # 3. 绮掑瓙绯荤粺 (闆姳)
        self.snowflakes = [SnowFlake() for _ in range(50)]
        
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.next_action = "quit"
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_index = (self.selected_index - 1) % len(self.options)
                elif event.key == pygame.K_DOWN:
                    self.selected_index = (self.selected_index + 1) % len(self.options)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    if self.selected_index == 0:
                        self.next_action = "new_game"
                        self.running = False
                    elif self.selected_index == 1:
                        self.next_action = "continue"
                        self.running = False
                    elif self.selected_index == 2:
                        self.next_action = "quit"
                        self.running = False
                        
    def update(self):
        for flake in self.snowflakes:
            flake.update()
            
    def draw(self):
        # 鑳屾櫙
        self.screen.blit(self.bg_img, (0, 0))
        
        # 閬僵 (鍗婇€忔槑榛戣壊锛岃瀛楁洿娓呮)
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(100)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # 闆姳
        for flake in self.snowflakes:
            flake.draw(self.screen)
            
        # 鏍囬 (纭紪鐮佹垨鍥剧墖)
        # title_surf = self.font_selected.render("Under Starflow", True, (255, 255, 255))
        # self.screen.blit(title_surf, (self.width//2 - title_surf.get_width()//2, 100))
        
        # 閫夐」
        center_x = self.width // 2
        start_y = self.height // 2 - 150
        spacing = 60
        
        for i, text in enumerate(self.options):
            if i == self.selected_index:
                color = (255, 215, 0) # Gold
                font = self.font_selected
                # prefix = "> " 
            else:
                color = (200, 200, 200)
                font = self.font
                # prefix = "  "
                
            surf = font.render(text, True, color)
            rect = surf.get_rect(center=(center_x, start_y + i * spacing))
            
            if i == self.selected_index:
                # 钃濊壊鏂规
                box_rect = rect.inflate(40, 20)
                pygame.draw.rect(self.screen, (0, 100, 255), box_rect, 2)
            
            self.screen.blit(surf, rect)
            
        pygame.display.flip()
        
    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.handle_input()
            self.update()
            self.draw()
            clock.tick(60)
        return self.next_action

class ConfirmDialog:
    def __init__(self, screen, text="确认返回标题界面？"):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.text = text
        self.options = ["是", "否"]
        self.selected_index = 1 # Default to No
        try:
            self.font = get_font(32)
        except:
            self.font = pygame.font.Font(None, 32)

    def set_text(self, text):
        self.text = text

    def run(self, bg_surface):
        clock = pygame.time.Clock()
        running = True
        result = False
        
        while running:
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    return False # Treat quit as No/Cancel in dialog
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                        self.selected_index = (self.selected_index + 1) % 2
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        if self.selected_index == 0: # Yes
                            result = True
                        else: # No
                            result = False
                        running = False
                    elif event.key == pygame.K_ESCAPE:
                        result = False
                        running = False
            
            # Draw
            self.screen.blit(bg_surface, (0, 0))
            
            # Dialog Box
            box_width, box_height = 400, 200
            box_x = (self.width - box_width) // 2
            box_y = (self.height - box_height) // 2
            
            # Semi-transparent background
            s = pygame.Surface((box_width, box_height))
            s.set_alpha(200)
            s.fill((0, 0, 0))
            self.screen.blit(s, (box_x, box_y))
            
            # Border
            pygame.draw.rect(self.screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 2)
            
            # Text
            text_surf = self.font.render(self.text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(self.width//2, box_y + 60))
            self.screen.blit(text_surf, text_rect)
            
            # Options
            opt_y = box_y + 130
            opt_spacing = 150
            start_x = self.width // 2 - opt_spacing // 2
            
            for i, opt in enumerate(self.options):
                color = (255, 215, 0) if i == self.selected_index else (200, 200, 200)
                prefix = "> " if i == self.selected_index else ""
                opt_surf = self.font.render(prefix + opt, True, color)
                # "鏄? at left, "鍚? at right
                pos_x = start_x if i == 0 else start_x + opt_spacing
                opt_rect = opt_surf.get_rect(center=(pos_x, opt_y))
                self.screen.blit(opt_surf, opt_rect)
                
            pygame.display.flip()
            clock.tick(60)
            
        return result

class BonfireMenu:
    def __init__(self, screen):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.options = ["存档", "传送", "离开"]
        self.selected_index = 0
        try:
            self.font = get_font(28)
        except:
            self.font = pygame.font.Font(None, 28)
            
    def run(self, bg_surface):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    return "leave"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.selected_index = (self.selected_index - 1) % len(self.options)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.selected_index = (self.selected_index + 1) % len(self.options)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_z:
                        if self.options[self.selected_index] == "存档":
                            return "save"
                        elif self.options[self.selected_index] == "传送":
                            return "teleport"
                        elif self.options[self.selected_index] == "离开":
                            return "leave"
                    elif event.key == pygame.K_ESCAPE or event.key == pygame.K_x:
                        return "leave"

            # Draw
            self.screen.blit(bg_surface, (0, 0))
            
            # Menu Box (Vertical, Bottom Right)
            # Original: 160, 200. Reduced by 10% -> ~144, 180
            box_width, box_height = 144, 180
            box_x = self.width - box_width - 30
            box_y = self.height - box_height - 30
            
            # Semi-transparent BG
            s = pygame.Surface((box_width, box_height))
            s.set_alpha(230) # Darker
            s.fill((0, 0, 0))
            self.screen.blit(s, (box_x, box_y))
            
            # Border
            pygame.draw.rect(self.screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 2)
            
            # Options
            # Even distribution
            # Available height = box_height - top_padding - bottom_padding
            # Let's say padding 20
            content_height = box_height - 40
            item_spacing = content_height // len(self.options)
            
            start_x = box_x + 40
            start_y = box_y + 20 + (item_spacing // 2) # Center first item in its slot
            
            for i, opt in enumerate(self.options):
                color = (255, 215, 0) if i == self.selected_index else (255, 255, 255)
                text_surf = self.font.render(opt, True, color)
                # Centered vertically in its slot
                current_y = box_y + 20 + i * item_spacing + (item_spacing - text_surf.get_height()) // 2
                
                text_rect = text_surf.get_rect(topleft=(start_x, current_y))
                self.screen.blit(text_surf, text_rect)
                
                # Selection Marker (Yellow Triangle)
                if i == self.selected_index:
                    marker_x = start_x - 20
                    marker_y = text_rect.centery
                    p1 = (marker_x, marker_y - 6)
                    p2 = (marker_x, marker_y + 6)
                    p3 = (marker_x + 10, marker_y)
                    pygame.draw.polygon(self.screen, (255, 215, 0), [p1, p2, p3])
                
            pygame.display.flip()
            clock.tick(60)
        return "leave"

class TeleportMenu:
    def __init__(self, screen, current_map_name, valid_destinations):
        """
        valid_destinations: list of dicts {"id": "start", "name": "鏃犱富闆湴"}
        """
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.current_map_name = current_map_name
        # Filter out current map
        self.options = [d for d in valid_destinations if d["name"] != current_map_name]
        
        self.selected_index = 0
        try:
            self.font = get_font(28)
        except:
            self.font = pygame.font.Font(None, 28)

    def run(self, bg_surface):
        clock = pygame.time.Clock()
        running = True
        selected_dest_id = None
        
        while running:
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    return None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.selected_index = (self.selected_index - 1) % len(self.options) if self.options else 0
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.selected_index = (self.selected_index + 1) % len(self.options) if self.options else 0
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_z:
                        if self.options:
                            selected_dest_id = self.options[self.selected_index]["id"]
                            running = False
                    elif event.key == pygame.K_ESCAPE or event.key == pygame.K_x:
                        running = False
            
            # Draw
            self.screen.blit(bg_surface, (0, 0))
            
            # Teleport Menu Box (Big Black Box with White Border)
            # Size: 80% of screen width, 40% of height
            box_width = int(self.width * 0.8)
            box_height = int(self.height * 0.4)
            box_x = (self.width - box_width) // 2
            box_y = (self.height - box_height) // 2
            
            # Fill Black
            pygame.draw.rect(self.screen, (0, 0, 0), (box_x, box_y, box_width, box_height))
            # White Border (Thickness 4)
            pygame.draw.rect(self.screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 4)
            
            # Draw Options (4 per row)
            # Currently we expect few, but logic should support grid
            start_x = box_x + 50
            start_y = box_y + 50
            col_spacing = 200
            row_spacing = 60
            
            if not self.options:
                text = self.font.render("无其他可传送地点", True, (150, 150, 150))
                text_rect = text.get_rect(center=(self.width // 2, self.height // 2))
                self.screen.blit(text, text_rect)
            else:
                for i, opt in enumerate(self.options):
                    row = i // 4
                    col = i % 4
                    
                    x = start_x + col * col_spacing
                    y = start_y + row * row_spacing
                    
                    color = (255, 215, 0) if i == self.selected_index else (255, 255, 255)
                    text = self.font.render(opt["name"], True, color)
                    self.screen.blit(text, (x, y))
                    
                    # Selection Cursor (Triangle?) or just color highlight
                    if i == self.selected_index:
                         # Draw a small triangle to the left
                         p1 = (x - 15, y + 5)
                         p2 = (x - 15, y + 20)
                         p3 = (x - 5, y + 12)
                         pygame.draw.polygon(self.screen, (255, 215, 0), [p1, p2, p3])

            pygame.display.flip()
            clock.tick(60)
            
        return selected_dest_id

class PauseMenu:
    def __init__(self, screen):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        # Adjusted order: Title Screen, Stats, Volume, Backpack
        self.options = ["标题界面", "角色属性", "调整音量", "查看背包"]
        self.selected_index = 0
        try:
            self.font = get_font(28)
        except:
            self.font = pygame.font.Font(None, 28)
            
    def run(self, bg_surface):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    return "quit"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.selected_index = (self.selected_index - 1) % len(self.options)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.selected_index = (self.selected_index + 1) % len(self.options)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_z:
                        if self.options[self.selected_index] == "角色属性":
                            return "stats"
                        elif self.options[self.selected_index] == "标题界面":
                            return "title"
                        elif self.options[self.selected_index] == "调整音量":
                            return "volume"
                        elif self.options[self.selected_index] == "查看背包":
                            return "backpack"
                    elif event.key == pygame.K_ESCAPE or event.key == pygame.K_x:
                        return "resume"

            # Draw
            self.screen.blit(bg_surface, (0, 0))
            
            # Menu Box (Vertical, Center or similar style to Bonfire)
            # User said "Vertical black background menu"
            # Let's make it look like a standard pause menu in center
            box_width, box_height = 200, 200
            box_x = (self.width - box_width) // 2
            box_y = (self.height - box_height) // 2
            
            # Semi-transparent BG
            s = pygame.Surface((box_width, box_height))
            s.set_alpha(230) 
            s.fill((0, 0, 0))
            self.screen.blit(s, (box_x, box_y))
            
            # Border
            pygame.draw.rect(self.screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 2)
            
            # Options
            content_height = box_height - 40
            item_spacing = content_height // len(self.options)
            
            start_x = box_x + 50
            
            for i, opt in enumerate(self.options):
                color = (255, 215, 0) if i == self.selected_index else (255, 255, 255)
                text_surf = self.font.render(opt, True, color)
                
                # Centered vertically in its slot
                current_y = box_y + 20 + i * item_spacing + (item_spacing - text_surf.get_height()) // 2
                
                text_rect = text_surf.get_rect(topleft=(start_x, current_y))
                self.screen.blit(text_surf, text_rect)
                
                # Selection Marker (Yellow Triangle)
                if i == self.selected_index:
                    marker_x = start_x - 20
                    marker_y = text_rect.centery
                    p1 = (marker_x, marker_y - 6)
                    p2 = (marker_x, marker_y + 6)
                    p3 = (marker_x + 10, marker_y)
                    pygame.draw.polygon(self.screen, (255, 215, 0), [p1, p2, p3])
                
            pygame.display.flip()
            clock.tick(60)
        return "resume"

class BackpackMenu:
    def __init__(self, screen):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.selected_index = 0
        self.full_list = []
        
        # Safe font loading for Chinese characters
        self.font = get_font(28)

    def update_list(self, player):
        # Dynamic Options Update
        # Requirement: First option is always "任务提示"
        mission_text = "任务提示"
        inventory_items = []
        if player and hasattr(player, 'inventory'):
            # Consolidate inventory before displaying to merge duplicates
            if hasattr(player, 'consolidate_inventory'):
                player.consolidate_inventory()

            for item in player.inventory:
                if isinstance(item, dict):
                    name = item.get("name", "未知物品")
                    count = item.get("count", 1)
                    if count > 1:
                        inventory_items.append(f"{name} x{count}")
                    else:
                        inventory_items.append(name)
                else:
                    inventory_items.append("未知物品")
        
        if not inventory_items:
            inventory_items = ["(背包为空)"]
        
        self.full_list = [mission_text] + inventory_items

    def run(self, player, bg_snapshot, dialogue_system):
        # 1. Physical Clear: Force disable any blockers
        dialogue_system.active = False
        
        # 3. Fix: Event Residue Clearing (User Req)
        pygame.event.pump()
        pygame.event.clear()
        
        # Update list based on current player state
        self.update_list(player)
        
        clock = pygame.time.Clock()
        menu_running = True
        
        # Mouse visibility fix
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)
        
        while menu_running:
            # Event Loop - Strictly isolated
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
            
                # 2. Fix: Ensure loop continues regardless of result (User Req)
                result = self.handle_event(event)
                if result == "close":
                    menu_running = False
        
            # 2. Render Layer: Snapshot -> UI (Always Execute)
            self.draw(bg_snapshot)
            pygame.display.flip()
            clock.tick(60)
        
        # Cleanup
        pygame.event.pump()
        return "resume"


    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                self.selected_index = (self.selected_index - 1) % len(self.full_list)
                return "updated"
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                self.selected_index = (self.selected_index + 1) % len(self.full_list)
                return "updated"
            elif event.key == pygame.K_UP or event.key == pygame.K_w:
                self.selected_index = (self.selected_index - 2) % len(self.full_list)
                return "updated"
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                self.selected_index = (self.selected_index + 2) % len(self.full_list)
                return "updated"
            elif event.key in [pygame.K_ESCAPE, pygame.K_x, pygame.K_b, pygame.K_TAB]:
                return "close"
        return None

    def draw(self, bg_surface):
        # Ensure dimensions are up to date
        self.width = self.screen.get_width()
        self.height = self.screen.get_height()
        
        # Draw
        # Ensure we start with a clean slate if bg_surface is transparent/empty
        self.screen.fill((0, 0, 0)) 
        if bg_surface:
            self.screen.blit(bg_surface, (0, 0))
        
        # Box Style (Center Screen, Large, Grid Layout)
        # Size: 80% width, 60% height
        box_width = int(self.width * 0.8)
        box_height = int(self.height * 0.6)
        box_x = (self.width - box_width) // 2
        box_y = (self.height - box_height) // 2
        
        # Fill Black (Teleport Menu Style)
        pygame.draw.rect(self.screen, (0, 0, 0), (box_x, box_y, box_width, box_height))
        # White Border (Thickness 4)
        pygame.draw.rect(self.screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 4)
        
        # Render List (Grid Layout: 2 Columns)
        start_x = box_x + 60
        start_y = box_y + 60
        col_spacing = box_width // 2 # Half box width per column
        row_spacing = 60
        
        # Scroll Logic (if too many items)
        max_items_per_page = ((box_height - 120) // row_spacing) * 2
        if max_items_per_page < 2: max_items_per_page = 2
        
        page = self.selected_index // max_items_per_page
        display_start = page * max_items_per_page
        display_end = display_start + max_items_per_page
        display_list = self.full_list[display_start:display_end]
        
        for i, text in enumerate(display_list):
            real_idx = display_start + i
            
            # Grid Position
            row = i // 2
            col = i % 2
            
            x = start_x + col * col_spacing
            y = start_y + row * row_spacing
            
            color = (255, 215, 0) if real_idx == self.selected_index else (255, 255, 255)
            
            # Special color for Mission
            if real_idx == 0:
                color = (0, 255, 255) if real_idx != self.selected_index else (255, 215, 0)
            
            text_surf = self.font.render(text, True, color)
            self.screen.blit(text_surf, (x, y))
            
            # Selection Marker (Yellow Triangle to the left)
            if real_idx == self.selected_index:
                marker_x = x - 20
                marker_y = y + text_surf.get_height() // 2
                p1 = (marker_x, marker_y - 6)
                p2 = (marker_x, marker_y + 6)
                p3 = (marker_x + 10, marker_y)
                pygame.draw.polygon(self.screen, (255, 215, 0), [p1, p2, p3])

    def run(self, player, bg_snapshot, dialogue_system):
        # 1. Physical Clear: Force disable any blockers
        dialogue_system.active = False
        
        # 3. Fix: Event Residue Clearing (User Req)
        pygame.event.pump()
        pygame.event.clear()
        
        # Update list based on current player state
        self.update_list(player)
        
        clock = pygame.time.Clock()
        menu_running = True
        
        while menu_running:
            # Event Loop - Strictly isolated
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                
                # 2. Fix: Ensure loop continues regardless of result (User Req)
                result = self.handle_event(event)
                if result == "close":
                    menu_running = False
            
            # 2. Render Layer: Snapshot -> UI (Always Execute)
            self.draw(bg_snapshot)
            pygame.display.flip()
            clock.tick(60)
            
        return "resume"

class VolumeMenu:
    def __init__(self, screen):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.options = ["BGM", "音效"]
        self.selected_index = 0
        try:
            self.font = get_font(28)
        except:
            self.font = pygame.font.Font(None, 28)
            
    def run(self, bg_surface, update_sfx_callback=None):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.selected_index = (self.selected_index - 1) % len(self.options)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.selected_index = (self.selected_index + 1) % len(self.options)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.change_volume(self.options[self.selected_index], -0.1, update_sfx_callback)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.change_volume(self.options[self.selected_index], 0.1, update_sfx_callback)
                    elif event.key == pygame.K_ESCAPE or event.key == pygame.K_x or event.key == pygame.K_RETURN:
                        running = False
            
            # Draw
            self.screen.blit(bg_surface, (0, 0))
            
            # Menu Box (Same size as PauseMenu for consistency)
            box_width, box_height = 300, 200 # Slightly wider for sliders
            box_x = (self.width - box_width) // 2
            box_y = (self.height - box_height) // 2
            
            # Semi-transparent BG
            s = pygame.Surface((box_width, box_height))
            s.set_alpha(230) 
            s.fill((0, 0, 0))
            self.screen.blit(s, (box_x, box_y))
            
            # Border
            pygame.draw.rect(self.screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 2)
            
            # Options
            content_height = box_height - 40
            item_spacing = content_height // len(self.options)
            
            start_x = box_x + 40
            
            for i, opt in enumerate(self.options):
                color = (255, 215, 0) if i == self.selected_index else (255, 255, 255)
                text_surf = self.font.render(opt, True, color)
                
                # Centered vertically in its slot
                current_y = box_y + 20 + i * item_spacing + (item_spacing - text_surf.get_height()) // 2
                
                text_rect = text_surf.get_rect(topleft=(start_x, current_y))
                self.screen.blit(text_surf, text_rect)
                
                # Selection Marker
                if i == self.selected_index:
                    marker_x = start_x - 20
                    marker_y = text_rect.centery
                    p1 = (marker_x, marker_y - 6)
                    p2 = (marker_x, marker_y + 6)
                    p3 = (marker_x + 10, marker_y)
                    pygame.draw.polygon(self.screen, (255, 215, 0), [p1, p2, p3])
                    
                # Draw Volume Bar
                # Value
                if opt == "BGM":
                    val = config.BGM_VOLUME
                else:
                    val = config.SFX_VOLUME
                
                bar_x = start_x + 80
                bar_y = text_rect.centery - 5
                bar_width = 120
                bar_height = 10
                
                # Background Bar
                pygame.draw.rect(self.screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height))
                # Foreground Bar
                fill_width = int(bar_width * val)
                pygame.draw.rect(self.screen, color, (bar_x, bar_y, fill_width, bar_height))
                
            pygame.display.flip()
            clock.tick(60)
            
    def change_volume(self, option, delta, callback):
        if option == "BGM":
            config.BGM_VOLUME = max(0.0, min(1.0, config.BGM_VOLUME + delta))
            # Apply immediately
            try:
                pygame.mixer.music.set_volume(config.BGM_VOLUME)
            except:
                pass
        elif option == "音效":
            config.SFX_VOLUME = max(0.0, min(1.0, config.SFX_VOLUME + delta))
            if callback:
                callback()

class StatsMenu:
    def __init__(self, screen):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.font = get_font(28)
        self.title_font = get_font(36)
            
    def run(self, player, bg_surface):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_x, pygame.K_RETURN, pygame.K_SPACE, pygame.K_z]:
                        running = False
            
            # Draw
            self.screen.blit(bg_surface, (0, 0))
            
            # Box
            box_width, box_height = 400, 300
            box_x = (self.width - box_width) // 2
            box_y = (self.height - box_height) // 2
            
            s = pygame.Surface((box_width, box_height))
            s.set_alpha(230) 
            s.fill((0, 0, 0))
            self.screen.blit(s, (box_x, box_y))
            
            pygame.draw.rect(self.screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 2)
            
            # Text
            cx = self.width // 2
            start_y = box_y + 40
            line_height = 50
            
            # Title
            title = self.title_font.render("角色属性", True, (255, 215, 0))
            title_rect = title.get_rect(center=(cx, start_y))
            self.screen.blit(title, title_rect)
            
            # Stats
            lvl = getattr(player, 'level', 1)
            exp = getattr(player, 'exp', 0)
            max_exp = getattr(player, 'max_exp', 100)
            atk = getattr(player, 'attack', 10)
            
            # Draw Level and Attack
            lvl_surf = self.font.render(f"等级: {lvl}", True, (255, 255, 255))
            atk_surf = self.font.render(f"攻击力: {atk}", True, (255, 255, 255))
            
            self.screen.blit(lvl_surf, lvl_surf.get_rect(center=(cx, start_y + 70)))
            self.screen.blit(atk_surf, atk_surf.get_rect(center=(cx, start_y + 70 + line_height)))
            
            # EXP Bar
            exp_bar_y = start_y + 70 + line_height * 2
            exp_bar_width = 200
            exp_bar_height = 20
            exp_bar_x = cx - exp_bar_width // 2
            
            pygame.draw.rect(self.screen, (100, 100, 100), (exp_bar_x, exp_bar_y, exp_bar_width, exp_bar_height))
            fill_width = int(exp_bar_width * (exp / max_exp)) if max_exp > 0 else 0
            pygame.draw.rect(self.screen, (0, 200, 255), (exp_bar_x, exp_bar_y, fill_width, exp_bar_height))
            pygame.draw.rect(self.screen, (255, 255, 255), (exp_bar_x, exp_bar_y, exp_bar_width, exp_bar_height), 2)
            
            # EXP Text
            exp_text = f"经验: {exp} / {max_exp}"
            exp_surf = self.font.render(exp_text, True, (255, 255, 255))
            self.screen.blit(exp_surf, exp_surf.get_rect(center=(cx, exp_bar_y + 35)))
            
            pygame.display.flip()
            clock.tick(60)
        return "resume"

