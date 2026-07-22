import pygame
import random
import math
import os
from engine.utils import resource_path, get_font
from engine.config import *
from engine.audio import load_bgm
from entities.bullets import Bullet, PlasmaBlade, LaserNetworkLine, YellowBullet

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

class BattleManager:
    def __init__(self, screen):
        self.screen = screen
        self.running = False
        self.player = None
        self.enemy_data = None
        
        # Resources
        self.font = get_font(24)
        self.btn_font = get_font(24)
        self.dialog_font = get_font(20)
        self.damage_font = get_font(36)
        
        # Battle State Constants
        self.PHASE_MENU = 0
        self.PHASE_PLAYER_ANIM = 1
        self.PHASE_ENEMY_TURN = 2
        self.PHASE_ITEM_SELECT = 3
        self.PHASE_ACT_SELECT = 4
        self.PHASE_QTE = 5
        self.PHASE_MERCY_SELECT = 6
        self.PHASE_FLEE_SELECT = 7
        self.PHASE_VICTORY = 8
        
        # State Variables
        self.current_phase = self.PHASE_ENEMY_TURN
        self.next_phase_after_anim = self.PHASE_ENEMY_TURN
        self.turn_count = 0
        self.selected_btn_idx = 0
        self.item_selection_idx = 0
        self.act_selection_idx = 0
        self.mercy_selection_idx = 0
        self.flee_selection_idx = 0
        
        self.dialog_text = ""
        self.action_text = ""
        self.action_timer = 0
        self.is_attack_anim = False
        self.should_exit_battle = False
        
        # QTE Variables
        self.battle_box = pygame.Rect(0, 250, 400, 300)
        self.battle_box.centerx = SCREEN_WIDTH // 2
        
        self.qte_rect = pygame.Rect(self.battle_box.left + 50, self.battle_box.top + 120, 300, 20)
        self.qte_needle_x = 0
        self.qte_needle_speed = 0
        self.qte_target_zone = pygame.Rect(0, 0, 0, 0)
        self.qte_perfect_zone = pygame.Rect(0, 0, 0, 0)
        self.damage_multiplier = 0.0
        
        # Combat Entities
        self.damage_popups = []
        self.bullets = []
        self.magnets = []
        self.enemy_turn_timer = 0
        self.ENEMY_TURN_DURATION = 60 * 8
        self.damage_flash_timer = 0
        
        # Battle Result
        self.battle_result = None
        
        # AI Variables
        self.shake_intensity = 0
        self.shake_offset = [0, 0]
        self.active_skills = []
        self.wind_force = [0, 0]
        self.hack_count = 0
        self.bullet_speed_multiplier = 1.0
        
        # Enemy Visuals
        self.enemy_frames = []
        self.enemy_anim_index = 0
        self.enemy_anim_timer = 0
        self.ENEMY_ANIM_SPEED = 6
        self.enemy_img = None
        self.enemy_rect = None
        self.enemy_hp = 50
        self.enemy_max_hp = 50
        
        # Heart (Player Soul)
        self.heart_img = None
        self.heart_rect = None
        self.heart_pos = [0.0, 0.0]
        self.heart_speed = 4
        
        # Audio
        self.calibration_sfx = None
        
        # Death Sequence State
        self.death_sequence_active = False
        self.death_timer = 0
        self.DEATH_FREEZE_DURATION = 120 # 2 seconds at 60 FPS
        self.death_triggered = False # Prevent double death processing
        
        self.load_common_resources()

    def load_common_resources(self):
        try:
            self.heart_img = pygame.image.load(resource_path("ui/backgrounds/mechanical_heart.jpeg")).convert()
            self.heart_img.set_colorkey((255, 255, 255))
            self.heart_img = pygame.transform.scale(self.heart_img, (32, 32))
        except:
            self.heart_img = pygame.Surface((32, 32))
            self.heart_img.fill((255, 0, 0))
            
        try:
            if os.path.exists(resource_path("audio/sfx/attack_success.wav")):
                self.calibration_sfx = pygame.mixer.Sound(resource_path("audio/sfx/attack_success.wav"))
                self.calibration_sfx.set_volume(0.5)
        except Exception as e:
            print(f"Failed to load calibration sfx: {e}")

    def start_battle(self, player, enemy_data=None):
        self.player = player
        self.enemy_data = enemy_data if enemy_data else {
            "name": "变量",
            "hp": 50,
            "skills": ["laser", "cube", "circle", "thrust"],
            "acts": []
        }
        self.running = True
        self.should_exit_battle = False # Reset exit flag
        self.battle_result = None # Reset result
        self.death_triggered = False # Reset death flag for new battle
        
        # Reset State
        # Always make Player go first (PHASE_MENU)
        enemy_name = self.enemy_data.get("name", "")
        
        self.current_phase = self.PHASE_MENU
        if enemy_name:
             self.dialog_text = f"* {enemy_name} 阻挡了你的去路。"
        else:
             self.dialog_text = "* 敌人阻挡了你的去路。"
        
        self.next_phase_after_anim = self.PHASE_ENEMY_TURN
        self.turn_count = 0
        self.selected_btn_idx = 0
        self.bullets = []
        self.dusts = []
        self.debris_particles = []
        self.damage_popups = []
        self.magnets = []
        self.hack_count = 0
        self.bullet_speed_multiplier = 1.0
        self.shake_intensity = 0
        self.active_skills = []
        self.wind_force = [0, 0]
        
        # Reset Battle Box & Shield Mode
        self.battle_box = pygame.Rect(0, 250, 400, 300)
        self.battle_box.centerx = self.screen.get_width() // 2
        self.is_shield_mode = False
        self.shield_arrows = []
        
        self.enemy_hp = self.enemy_data.get("hp", 50)
        self.enemy_max_hp = self.enemy_hp
        self.enemy_turn_timer = self.ENEMY_TURN_DURATION
        
        # Setup Heart
        self.heart_rect = self.heart_img.get_rect(center=self.battle_box.center)
        self.heart_pos = [float(self.heart_rect.x), float(self.heart_rect.y)]
        
        # Load Enemy Visuals
        self.load_enemy_visuals()
        
        # BGM
        try:
            self.current_bgm_pos = pygame.mixer.music.get_pos() / 1000.0
        except:
            self.current_bgm_pos = 0.0
            
        bgm_file = self.enemy_data.get("bgm", "monster_song.mp3")
        bgm_start = self.enemy_data.get("bgm_start", 0.0)
        bgm_volume = self.enemy_data.get("bgm_volume", 1.0)
        
        load_bgm(bgm_file, start_pos=bgm_start)
        pygame.mixer.music.set_volume(bgm_volume)

        # FailureEnemy Logic Update:
        # Player MUST go first (PHASE_MENU is already set above)
        # Death logic moved to handle_enemy_turn / update
        if "failure_enemy" in self.enemy_data.get("id", ""):
            # Ensure normal start, death happens later
            self.death_sequence_active = False 
            self.death_timer = 0
            pass

    def load_enemy_visuals(self):
        self.enemy_frames = []
        img_folder = self.enemy_data.get("image_folder", "variable_anim")
        img_prefix = self.enemy_data.get("image_prefix", "variable")
        is_grid_anim = self.enemy_data.get("is_grid", False)
        self.ENEMY_ANIM_SPEED = self.enemy_data.get("anim_speed", 6)
        static_battle = self.enemy_data.get("static_battle", False)
        
        # FailureEnemy Special Sprite Logic
        if "failure_enemy" in self.enemy_data.get("id", ""):
            # Load 02.png (or 2.png) specifically
            found_path = resource_path("assetsDB/失败之作")
            if not os.path.exists(found_path): found_path = resource_path("assets/失败之作")
            
            p = os.path.join(found_path, "02.png")
            if not os.path.exists(p): p = os.path.join(found_path, "2.png")
            
            try:
                img = pygame.image.load(p).convert_alpha()
                # Scale to reasonable battle size (e.g. 150x150 or 200 high)
                # Let's target height 200 to match other enemies
                target_h = 200
                scale = target_h / img.get_height()
                new_w = int(img.get_width() * scale)
                img = pygame.transform.scale(img, (new_w, target_h))
                self.enemy_frames = [img]
            except Exception as e:
                print(f"Failed to load failure enemy battle sprite: {e}")
                self.enemy_frames = [pygame.Surface((100, 100))]
                self.enemy_frames[0].fill((150, 0, 0))
            
            self.enemy_img = self.enemy_frames[0]
            self.enemy_rect = self.enemy_img.get_rect(midtop=(self.screen.get_width() // 2, 20))
            return
        
        try:
            # Resolve path (Folder or Single File)
            is_single_file = False
            base_path = resource_path(img_folder)
            
            # Check direct file existence
            if os.path.isfile(base_path):
                is_single_file = True
            elif not os.path.exists(base_path):
                 # Check assets/
                 temp_path = resource_path(os.path.join("assets", img_folder))
                 if os.path.isfile(temp_path):
                     base_path = temp_path
                     is_single_file = True
                 elif not os.path.exists(temp_path):
                     # Check assetsDB/
                     temp_path = resource_path(os.path.join("assetsDB", img_folder))
                     if os.path.isfile(temp_path):
                         base_path = temp_path
                         is_single_file = True
                     elif os.path.exists(temp_path):
                         base_path = temp_path # It is a folder in assetsDB

            if is_single_file:
                # Load Single SpriteSheet
                try:
                    sheet = pygame.image.load(base_path).convert_alpha()
                    sheet_w, sheet_h = sheet.get_size()
                    
                    if is_grid_anim:
                        # Assume 4x4 Grid for Battle (Standard Walking/Idle Grid)
                        # Or just use the whole sheet as frames if it's a strip?
                        # User said "new animation texture" which implies the same 4x4 sheet.
                        cell_w = sheet_w // 4
                        cell_h = sheet_h // 4
                        for row in range(4):
                            for col in range(4):
                                rect = pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)
                                img = sheet.subsurface(rect)
                                
                                # Scale for Battle (Max height 200)
                                if img.get_height() > 200:
                                    scale = 200 / img.get_height()
                                    img = pygame.transform.scale(img, (int(img.get_width() * scale), 200))
                                
                                self.enemy_frames.append(img)
                    else:
                        # Single image fallback
                        if sheet.get_height() > 200:
                            scale = 200 / sheet.get_height()
                            sheet = pygame.transform.scale(sheet, (int(sheet.get_width() * scale), 200))
                        self.enemy_frames.append(sheet)
                        
                except Exception as e:
                    print(f"Failed to load spritesheet {base_path}: {e}")
            
            else:
                # Folder Loading Logic
                if is_grid_anim:
                    for row in range(1, 5):
                        for col in range(1, 5):
                            fname = f"{img_prefix}_{row}_{col}.png"
                            full_path = os.path.join(base_path, fname)
                            if os.path.exists(full_path):
                                img = pygame.image.load(full_path).convert_alpha()
                                if img.get_height() > 200:
                                    scale = 200 / img.get_height()
                                    img = pygame.transform.scale(img, (int(img.get_width() * scale), 200))
                                self.enemy_frames.append(img)
                else:
                    for i in range(1, 17):
                        fname = f"{img_prefix}_{i}.png"
                        full_path = os.path.join(base_path, fname)
                        if os.path.exists(full_path):
                            img = pygame.image.load(full_path).convert_alpha()
                            if img.get_height() > 200:
                                scale = 200 / img.get_height()
                                img = pygame.transform.scale(img, (int(img.get_width() * scale), 200))
                            self.enemy_frames.append(img)
            
            if not self.enemy_frames:
                # Fallback check for folder as file path logic from original code?
                # The original code had a check here, but we handled it above with is_single_file
                raise Exception("No frames loaded")
        
        except Exception as e:
            print(f"Failed to load enemy animation: {e}")
            fallback = pygame.Surface((100, 100))
            fallback.fill((100, 100, 100))
            self.enemy_frames = [fallback]

        # Check for flip
        if self.enemy_data.get("flip", False):
            self.enemy_frames = [pygame.transform.flip(img, True, False) for img in self.enemy_frames]
        
        if static_battle and self.enemy_frames:
            self.enemy_frames = [self.enemy_frames[0]]
            
        self.enemy_img = self.enemy_frames[0]
        self.enemy_rect = self.enemy_img.get_rect(midtop=(SCREEN_WIDTH // 2, 20))

    def handle_input(self, event):
        if not self.running: return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Debug exit or menu cancel
                if self.current_phase == self.PHASE_MENU:
                    self.running = False # Or pause menu
                elif self.current_phase in [self.PHASE_ACT_SELECT, self.PHASE_ITEM_SELECT, self.PHASE_MERCY_SELECT]:
                    self.current_phase = self.PHASE_MENU
            
            # Phase: Menu
            if self.current_phase == self.PHASE_MENU:
                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    self.selected_btn_idx = (self.selected_btn_idx - 1) % 4
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    self.selected_btn_idx = (self.selected_btn_idx + 1) % 4
                elif event.key == pygame.K_z or event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.confirm_menu_selection()
            
            # Phase: QTE
            elif self.current_phase == self.PHASE_QTE:
                if event.key == pygame.K_SPACE:
                    self.resolve_qte()
            
            # Phase: ACT Select
            elif self.current_phase == self.PHASE_ACT_SELECT:
                self.handle_act_input(event)
                
            # Phase: ITEM Select
            elif self.current_phase == self.PHASE_ITEM_SELECT:
                self.handle_item_input(event)
                
            # Phase: MERCY Select
            elif self.current_phase == self.PHASE_MERCY_SELECT:
                self.handle_mercy_input(event)

            # Phase: FLEE Select
            elif self.current_phase == self.PHASE_FLEE_SELECT:
                self.handle_flee_input(event)
                
            # Phase: VICTORY
            elif self.current_phase == self.PHASE_VICTORY:
                if event.key == pygame.K_z or event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.running = False

    def confirm_menu_selection(self):
        if self.selected_btn_idx == 0: # FIGHT
            self.start_qte()
        elif self.selected_btn_idx == 1: # ACT
            self.current_phase = self.PHASE_ACT_SELECT
            self.act_selection_idx = 0
        elif self.selected_btn_idx == 2: # ITEM
            self.current_phase = self.PHASE_ITEM_SELECT
            self.item_selection_idx = 0
        elif self.selected_btn_idx == 3: # MERCY
            self.current_phase = self.PHASE_MERCY_SELECT
            self.mercy_selection_idx = 0

    def start_qte(self):
        self.current_phase = self.PHASE_QTE
        start_side = random.choice(["left", "right"])
        qte_speed_val = 8
        
        if start_side == "left":
            self.qte_needle_x = self.qte_rect.left
            self.qte_needle_speed = qte_speed_val
        else:
            self.qte_needle_x = self.qte_rect.right
            self.qte_needle_speed = -qte_speed_val
            
        # Optimization: Increase area by 10% (80 -> 88)
        zone_width = 88
        
        # Limit to middle 70% (15% margin on each side)
        # This prevents the zone from being too close to the start/end points
        margin = int(self.qte_rect.width * 0.15)
        
        min_x = self.qte_rect.left + margin
        max_x = self.qte_rect.right - margin - zone_width
        
        # Safety check
        if max_x < min_x:
            max_x = min_x
            
        zone_x = random.randint(min_x, max_x)
        self.qte_target_zone = pygame.Rect(zone_x, self.qte_rect.y, zone_width, self.qte_rect.height)
        
        perfect_width = 24
        perfect_x = zone_x + (zone_width - perfect_width) // 2
        self.qte_perfect_zone = pygame.Rect(perfect_x, self.qte_rect.y, perfect_width, self.qte_rect.height)

    def resolve_qte(self):
        hit_x = self.qte_needle_x
        needle_rect = pygame.Rect(int(hit_x), self.qte_rect.y, 4, self.qte_rect.height)
        
        if needle_rect.colliderect(self.qte_perfect_zone):
            self.damage_multiplier = 1.5
            if self.calibration_sfx: self.calibration_sfx.play()
        elif needle_rect.colliderect(self.qte_target_zone):
            self.damage_multiplier = 1.0
            if self.calibration_sfx: self.calibration_sfx.play()
        else:
            self.damage_multiplier = 0.0
            
        base_damage = 10
        if self.player and hasattr(self.player, "attack"):
            base_damage = self.player.attack
            
        final_damage = int(base_damage * self.damage_multiplier)
        
        if final_damage > 0:
            self.enemy_hp -= final_damage
            self.damage_popups.append({
                'val': str(final_damage),
                'color': (255, 0, 0),
                'pos': [self.enemy_rect.centerx, self.enemy_rect.top - 30],
                'timer': 90
            })
        else:
            self.damage_popups.append({
                'val': "MISS",
                'color': (150, 150, 150),
                'pos': [self.enemy_rect.centerx, self.enemy_rect.top - 30],
                'timer': 90
            })
            
        if self.enemy_hp < 0: self.enemy_hp = 0
        
        self.is_attack_anim = True
        self.current_phase = self.PHASE_PLAYER_ANIM
        self.next_phase_after_anim = self.PHASE_ENEMY_TURN
        self.action_timer = 60

    def get_act_options(self):
        return ["取消", "骇入", "逃跑"]

    def handle_act_input(self, event):
        display_actions = self.get_act_options()
        
        if event.key == pygame.K_x or event.key == pygame.K_ESCAPE:
            self.current_phase = self.PHASE_MENU
            self.act_selection_idx = 0
        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
            self.act_selection_idx = (self.act_selection_idx - 1) % len(display_actions)
        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
            self.act_selection_idx = (self.act_selection_idx + 1) % len(display_actions)
        elif event.key == pygame.K_UP or event.key == pygame.K_w:
            self.act_selection_idx = (self.act_selection_idx - 2) % len(display_actions)
        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
            self.act_selection_idx = (self.act_selection_idx + 2) % len(display_actions)
        elif event.key == pygame.K_z or event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            selected_act = display_actions[self.act_selection_idx]
            if selected_act == "取消":
                self.current_phase = self.PHASE_MENU
                self.act_selection_idx = 0
            elif selected_act == "骇入":
                self.do_hack()
            elif selected_act == "逃跑":
                self.action_text = "* 你逃跑了。"
                self.current_phase = self.PHASE_PLAYER_ANIM
                self.should_exit_battle = True
                self.action_timer = 90
                self.player.battle_cooldown = 180
                self.player.rect.y += 128
            else:
                 self.action_text = f"* 你进行了 {selected_act}。"
                 self.current_phase = self.PHASE_PLAYER_ANIM
                 self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                 self.action_timer = 60

    def do_hack(self):
        if self.hack_count < 5:
            self.hack_count += 1
            # Increased slow-down effect from 10% to 15% per hack based on user feedback
            factor = 0.85 
            self.bullet_speed_multiplier *= factor
            for b in self.bullets:
                if hasattr(b, 'vx'): b.vx *= factor
                if hasattr(b, 'vy'): b.vy *= factor
                if hasattr(b, 'speed'): b.speed *= factor
                # Fix for YellowBullet in WAIT state
                if hasattr(b, 'target_vx'): b.target_vx *= factor
                if hasattr(b, 'target_vy'): b.target_vy *= factor
            
            # Also slow down shield arrows if active
            if hasattr(self, 'shield_arrows'):
                for arrow in self.shield_arrows:
                    if 'speed' in arrow:
                        arrow['speed'] *= factor
                        
            self.action_text = f"* 骇入成功！弹幕速度降低15% (剩余次数: {5 - self.hack_count})"
        else:
            self.action_text = "* 骇入次数已耗尽。"
        
        self.current_phase = self.PHASE_PLAYER_ANIM
        self.next_phase_after_anim = self.PHASE_ENEMY_TURN
        self.action_timer = 60

    def handle_item_input(self, event):
        # Consolidate inventory to merge duplicates before filtering
        if hasattr(self.player, 'consolidate_inventory'):
            self.player.consolidate_inventory()

        # Filter consumables only (exclude materials/key_items)
        # Also include "battery" type as "投掷电池" is defined as battery type in some places
        consumables = [item for item in self.player.inventory if item.get("type") in ["consumable", "battery"]]
        
        display_names = []
        for item in consumables:
            name = item.get("name", "Unknown")
            count = item.get("count", 1)
            if count > 1:
                display_names.append(f"{name} x{count}")
            else:
                display_names.append(name)
        
        display_items = ["取消", f"能量电池 x{self.player.battery_count}"] + display_names
        
        if event.key == pygame.K_x or event.key == pygame.K_ESCAPE:
            self.current_phase = self.PHASE_MENU
            self.item_selection_idx = 0
        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
            self.item_selection_idx = (self.item_selection_idx - 1) % len(display_items)
        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
            self.item_selection_idx = (self.item_selection_idx + 1) % len(display_items)
        elif event.key == pygame.K_UP or event.key == pygame.K_w:
            self.item_selection_idx = (self.item_selection_idx - 2) % len(display_items)
        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
            self.item_selection_idx = (self.item_selection_idx + 2) % len(display_items)
        elif event.key == pygame.K_z or event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            self.use_item(display_items, consumables)

    def use_item(self, display_items, consumables_list=None):
        if self.item_selection_idx == 0: # Cancel
            self.current_phase = self.PHASE_MENU
            self.item_selection_idx = 0
        elif self.item_selection_idx == 1: # Battery
            if self.player.battery_count > 0:
                if self.player.hp < self.player.max_hp:
                    self.player.hp = min(self.player.hp + 10, self.player.max_hp)
                    self.player.battery_count -= 1
                    self.action_text = "* 你使用了能量电池。 HP +10。"
                    self.current_phase = self.PHASE_PLAYER_ANIM
                    self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                    self.action_timer = 60
                    self.item_selection_idx = 0
                else:
                    self.action_text = "* 你的HP已满。"
                    self.current_phase = self.PHASE_PLAYER_ANIM
                    self.next_phase_after_anim = self.PHASE_MENU
                    self.action_timer = 60
            else:
                self.action_text = "* 你没有能量电池了。"
                self.current_phase = self.PHASE_PLAYER_ANIM
                self.next_phase_after_anim = self.PHASE_MENU
                self.action_timer = 60
        else:
            # Other items from filtered consumables list
            real_item_idx = self.item_selection_idx - 2
            
            # Use passed consumables list if available, otherwise fallback
            target_list = consumables_list if consumables_list is not None else self.player.inventory
            
            if 0 <= real_item_idx < len(target_list):
                item = target_list[real_item_idx]
                item_name = item.get("name", "Unknown")
                
                # Use Logic
                if item_name == "投掷电池":
                     damage = 20
                     self.enemy_hp -= damage
                     self.damage_popups.append({
                        'val': str(damage),
                        'color': (255, 0, 0),
                        'pos': [self.enemy_rect.centerx, self.enemy_rect.top - 30],
                        'timer': 90
                     })
                     if self.enemy_hp < 0: self.enemy_hp = 0
                     
                     # Decrement/Remove
                     if hasattr(self.player, 'remove_item'):
                         self.player.remove_item(item_name, 1)
                     else:
                         if item in self.player.inventory:
                             self.player.inventory.remove(item)
                         
                     self.action_text = f"* 你投掷了电池！对敌人造成了 {damage} 点伤害。"
                     
                     self.current_phase = self.PHASE_PLAYER_ANIM
                     self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                     self.action_timer = 90
                     self.item_selection_idx = 0
                else:
                    self.action_text = f"* 使用了 {item_name}，但什么也没发生。"
                    self.current_phase = self.PHASE_PLAYER_ANIM
                    self.next_phase_after_anim = self.PHASE_MENU
                    self.action_timer = 60
                    self.item_selection_idx = 0

    def handle_mercy_input(self, event):
        display_mercy = ["取消", "宽恕"]
        if event.key == pygame.K_x or event.key == pygame.K_ESCAPE:
            self.current_phase = self.PHASE_MENU
            self.mercy_selection_idx = 0
        elif event.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
             self.mercy_selection_idx = (self.mercy_selection_idx + 1) % 2
        elif event.key in [pygame.K_z, pygame.K_RETURN, pygame.K_SPACE]:
            if self.mercy_selection_idx == 0:
                self.current_phase = self.PHASE_MENU
                self.mercy_selection_idx = 0
            else:
                self.action_text = f"* 你原谅了 {self.enemy_data.get('name', '敌人')}。"
                self.current_phase = self.PHASE_PLAYER_ANIM
                self.should_exit_battle = True
                self.action_timer = 90
                self.player.battle_cooldown = 180
                self.player.rect.y += 128

    def handle_flee_input(self, event):
        display_flee = ["取消", "逃跑"]
        if event.key == pygame.K_x or event.key == pygame.K_ESCAPE:
            self.current_phase = self.PHASE_MENU
            self.flee_selection_idx = 0
        elif event.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
             self.flee_selection_idx = (self.flee_selection_idx + 1) % 2
        elif event.key in [pygame.K_z, pygame.K_RETURN, pygame.K_SPACE]:
            if self.flee_selection_idx == 0:
                self.current_phase = self.PHASE_MENU
                self.flee_selection_idx = 0
            else:
                self.action_text = "* 你逃跑了。"
                self.current_phase = self.PHASE_PLAYER_ANIM
                self.should_exit_battle = True
                self.action_timer = 90
                self.player.battle_cooldown = 180
                self.player.rect.y += 128

    def update(self):
        if not self.running: return
        
        # Enemy Animation
        self.enemy_anim_timer += 1
        if self.enemy_anim_timer >= self.ENEMY_ANIM_SPEED:
            self.enemy_anim_timer = 0
            self.enemy_anim_index = (self.enemy_anim_index + 1) % len(self.enemy_frames)
            self.enemy_img = self.enemy_frames[self.enemy_anim_index]

        # QTE Update
        if self.current_phase == self.PHASE_QTE:
            self.qte_needle_x += self.qte_needle_speed
            if (self.qte_needle_speed > 0 and self.qte_needle_x > self.qte_rect.right) or \
               (self.qte_needle_speed < 0 and self.qte_needle_x < self.qte_rect.left):
                self.damage_multiplier = 0.0
                self.damage_popups.append({
                    'val': "MISS",
                    'color': (150, 150, 150),
                    'pos': [self.enemy_rect.centerx, self.enemy_rect.top - 30],
                    'timer': 90
                })
                self.is_attack_anim = True
                self.current_phase = self.PHASE_PLAYER_ANIM
                self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                self.action_timer = 60

        # Player Anim / Text Phase
        elif self.current_phase == self.PHASE_PLAYER_ANIM:
            self.action_timer -= 1
            if self.action_timer <= 0:
                self.is_attack_anim = False
                if self.should_exit_battle:
                    self.running = False
                elif self.enemy_hp <= 0:
                    self.battle_result = "win"
                    self.current_phase = self.PHASE_VICTORY
                    self.process_victory()
                else:
                    self.current_phase = self.next_phase_after_anim
                    if self.current_phase == self.PHASE_ENEMY_TURN:
                        self.start_enemy_turn()

        # Enemy Turn (Bullets)
        elif self.current_phase == self.PHASE_ENEMY_TURN:
            self.update_enemy_turn()

        # Update Damage Popups
        for popup in self.damage_popups[:]:
            popup['timer'] -= 1
            popup['pos'][1] -= 0.5
            if popup['timer'] <= 0:
                self.damage_popups.remove(popup)

    def process_victory(self):
        self.victory_messages = []
        enemy_name = self.enemy_data.get("name", "")
        
        # Determine drops
        exp_gain = 0
        items_gained = []
        
        if "黑游侠" in enemy_name:
            items_gained.append("黑色游侠的动力炉")
            exp_gain = 5
            # Add item to player inventory
            self.player.inventory.append({"name": "黑色游侠的动力炉", "type": "key_item", "description": "黑游侠的核心部件"})
            
        elif "变量" in enemy_name:
            exp_gain = 5
            
        elif "机凯种" in enemy_name:
            exp_gain = 5
            items_gained.append("投掷电池")
            self.player.inventory.append({"name": "投掷电池", "type": "consumable", "description": "一次性电池"})
            
        elif "义军" in enemy_name or "admin" in enemy_name.lower():
            exp_gain = 10
            items_gained.append("投掷电池")
            self.player.inventory.append({"name": "投掷电池", "type": "consumable", "description": "一次性电池"})

        elif "废弃机器人" in enemy_name:
            exp_gain = 10
            
        elif "鬼武士" in enemy_name:
            exp_gain = 20
            items_gained.append("鬼武士的断刃")
            self.player.inventory.append({"name": "鬼武士的断刃", "type": "key_item", "description": "散发着不详气息的断刃"})
            
        # Apply EXP
        if hasattr(self.player, "gain_exp"):
            self.player.gain_exp(exp_gain)
        elif hasattr(self.player, "exp"):
            self.player.exp += exp_gain
            
        # Generate Messages
        if items_gained:
            for item in items_gained:
                self.victory_messages.append(f"获得了 {item}！")
        if exp_gain > 0:
            self.victory_messages.append(f"获得了 {exp_gain} EXP！")
            
    def start_enemy_turn(self):
        self.turn_count += 1
        
        # Reset Shield Mode
        if hasattr(self, 'is_shield_mode') and self.is_shield_mode:
            self.is_shield_mode = False
            self.battle_box = self.original_battle_box
            self.heart_pos = [float(self.battle_box.centerx - self.heart_rect.width/2), 
                              float(self.battle_box.centery - self.heart_rect.height/2)]
            self.heart_rect.x = int(self.heart_pos[0])
            self.heart_rect.y = int(self.heart_pos[1])

        # Reset Screen Inversion
        if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
            self.is_screen_inverted = False
            
        # Reset Battle Box if shrunk (for Skill C)
        if "black_ranger_c" in self.active_skills or "black_ranger_b" in self.active_skills:
             # Already handled by is_shield_mode for B, but C needs manual reset?
             # C doesn't use is_shield_mode.
             # So we must reset battle_box if it was modified.
             # Check if we have original box
             if hasattr(self, 'original_battle_box') and self.original_battle_box:
                 self.battle_box = self.original_battle_box
                 self.heart_pos = [float(self.battle_box.centerx - self.heart_rect.width/2), 
                                  float(self.battle_box.centery - self.heart_rect.height/2)]
                 self.heart_rect.x = int(self.heart_pos[0])
                 self.heart_rect.y = int(self.heart_pos[1])

        self.enemy_turn_timer = self.ENEMY_TURN_DURATION
        self.bullets = []
        self.laser_warnings = []
        self.lasers = []
        self.heart_rect.center = self.battle_box.center
        self.heart_pos = [float(self.heart_rect.x), float(self.heart_rect.y)]
        
        # First turn: No attack (Observation) - REMOVED as per request
        # if self.turn_count == 1:
        #    self.active_skills = []
        #    self.dialog_text = "* 机凯种正在观察战场，未发动攻击。"
        #    self.enemy_turn_timer = 120 
        #    return

        # Mode A: Blue Spheres + Lasers
        # Mode B: White Particles
        enemy_name = self.enemy_data.get("name", "")
        
        # FailureEnemy Special Death Logic (Triggered on Enemy Turn Start)
        if "failure_enemy" in self.enemy_data.get("id", ""):
            self.handle_player_death()
            return

        if "变量" in enemy_name:
            if random.random() < 0.5:
                self.active_skills = ["laser", "cube"]
                self.dialog_text = "* 变量启动了歼灭模式 (Laser + Sphere)。"
            else:
                self.active_skills = ["random_particles"]
                self.dialog_text = "* 变量启动了散布模式 (Particles)。"
        elif "机凯种" in enemy_name or "义军士兵" in enemy_name:
             if random.random() < 0.5:
                self.active_skills = ["ruin_cutting_sequence"]
                self.dialog_text = f"* {enemy_name} 启动了切割序列。"
             else:
                self.active_skills = ["laser_network"]
                self.dialog_text = f"* {enemy_name} 启动了激光网格。"
        # Black Ranger EX Logic
        elif "黑游侠" in enemy_name:
            # Clear previous test skills
            # Randomly select one skill from A, B, C
            
            # Prevent Anti-Gravity (Skill B) on first turn
            available_skills = ["black_ranger_a", "black_ranger_b", "black_ranger_c"]
            if self.turn_count == 1:
                available_skills = ["black_ranger_a", "black_ranger_c"]
                
            skill_choice = random.choice(available_skills)
            self.active_skills = [skill_choice]
            
            if skill_choice == "black_ranger_a":
                self.dialog_text = "* 黑游侠EX 启动了全方位射击。"
                self.bullet_spawn_timer = 0
            elif skill_choice == "black_ranger_b":
                self.dialog_text = "* 黑游侠EX 启动了反重力装置。"
                self.is_screen_inverted = True
                
                # Reuse Admin Shield Logic
                self.is_shield_mode = True
                self.shield_dir = "UP"
                self.shield_arrows = []
                self.shield_broken_timer = 0
                
                # Shrink Battle Box (Same as Admin Shield)
                if not hasattr(self, 'original_battle_box'):
                    self.original_battle_box = self.battle_box.copy()
                self.battle_box = pygame.Rect(0, 0, 100, 100)
                self.battle_box.center = self.original_battle_box.center
                
                self.heart_pos = [float(self.battle_box.centerx - self.heart_rect.width/2), 
                                  float(self.battle_box.centery - self.heart_rect.height/2)]
                self.heart_rect.x = int(self.heart_pos[0])
                self.heart_rect.y = int(self.heart_pos[1])
                
            elif skill_choice == "black_ranger_c":
                self.dialog_text = "* 黑游侠EX 启动了火力压制。"
                
                # Shrink Battle Box to Small Size (Width 120, Height Normal)
                if not hasattr(self, 'original_battle_box'):
                    self.original_battle_box = self.battle_box.copy()
                
                new_h = self.original_battle_box.height
                self.battle_box = pygame.Rect(0, 0, 120, new_h) 
                self.battle_box.center = self.original_battle_box.center
                
                self.heart_pos = [float(self.battle_box.centerx - self.heart_rect.width/2), 
                                  float(self.battle_box.centery - self.heart_rect.height/2)]
                self.heart_rect.x = int(self.heart_pos[0])
                self.heart_rect.y = int(self.heart_pos[1])
                self.bullet_spawn_timer = 0
            
        elif "admin" in enemy_name.lower():
            # 1. Shield Mini-game
            # 2. Laser + Ruin Cutting
            # 3. Particles + Spheres
            r = random.random()
            if r < 0.33:
                self.active_skills = ["admin_shield"]
                self.dialog_text = "* Admin 启动了能量强袭。"
                # Setup Shield Mode
                self.is_shield_mode = True
                self.shield_dir = "UP"
                self.shield_arrows = []
                # Shrink Battle Box
                self.original_battle_box = self.battle_box.copy()
                self.battle_box = pygame.Rect(0, 0, 100, 100)
                self.battle_box.center = self.original_battle_box.center
                # Reset Heart to Center
                self.heart_pos = [float(self.battle_box.centerx - self.heart_rect.width/2), 
                                  float(self.battle_box.centery - self.heart_rect.height/2)]
                self.heart_rect.x = int(self.heart_pos[0])
                self.heart_rect.y = int(self.heart_pos[1])
            elif r < 0.66:
                self.active_skills = ["laser", "ruin_cutting_sequence"]
                self.dialog_text = "* Admin 启动了混合歼灭模式 (Laser + Cut)。"
            else:
                self.active_skills = ["random_particles", "cube"]
                self.dialog_text = "* Admin 启动了粒子风暴模式 (Particle + Sphere)。"
        elif "鬼武士" in enemy_name:
             r = random.random()
             if r < 0.33:
                 self.active_skills = ["dark_orb"]
                 self.dialog_text = "* 鬼武士 释放了暗影球。"
             elif r < 0.66:
                 self.active_skills = ["samurai_fire_walls"]
                 self.dialog_text = "* 鬼武士 释放了业火阵。"
             else:
                 self.active_skills = ["samurai_gravity_jump"]
                 self.dialog_text = "* 鬼武士 释放了重力压制。"
                 self.heart_vy = 0
                 self.gravity = 0.6
                 self.jump_strength = -9
                 self.on_ground = True
        else:
             # Default behavior for other enemies (if any)
             self.active_skills = self.enemy_data.get("skills", [])
             self.dialog_text = f"* {enemy_name} 发起了攻击！"
        
        if "thrust" in self.active_skills:
            self.wind_force = [1.5, 0] if random.random() > 0.5 else [-1.5, 0]
        else:
            self.wind_force = [0, 0]
            
        self.magnets = []
        if "magnet" in self.active_skills:
            for _ in range(3):
                mx = random.randint(self.battle_box.left + 50, self.battle_box.right - 50)
                my = random.randint(self.battle_box.top + 50, self.battle_box.bottom - 50)
                self.magnets.append({'pos': [mx, my], 'rect': pygame.Rect(mx-10, my-10, 20, 20)})

    def update_enemy_turn(self):
        self.enemy_turn_timer -= 1
        if self.enemy_turn_timer <= 0:
            # Check Escape Dust Punishment (Skill A for Abandoned Robot)
            if "escape_dust" in self.active_skills:
                uncollected_count = len([d for d in self.dusts if not d.is_collected])
                if uncollected_count > 0:
                    # Punishment: 5 DMG
                    self.player.take_damage(5)
                    self.damage_popups.append({'val': str(5), 'color': (255, 0, 0), 'pos': list(self.heart_rect.topright), 'timer': 60})
                    self.shake_intensity = 10
                    # Check death immediately?
                    if self.player.hp <= 0:
                        self.handle_player_death()
                        return

            # Reset Shield Mode immediately if active
            if hasattr(self, 'is_shield_mode') and self.is_shield_mode:
                self.is_shield_mode = False
                self.battle_box = self.original_battle_box
                self.heart_pos = [float(self.battle_box.centerx - self.heart_rect.width/2), 
                                  float(self.battle_box.centery - self.heart_rect.height/2)]
                self.heart_rect.x = int(self.heart_pos[0])
                self.heart_rect.y = int(self.heart_pos[1])
            
            # Reset Screen Inversion
            if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
                self.is_screen_inverted = False
            
            # Reset Battle Box for Skill C (if it was shrunk and not shield mode)
            if "black_ranger_c" in self.active_skills and hasattr(self, 'original_battle_box'):
                 self.battle_box = self.original_battle_box
                 self.heart_pos = [float(self.battle_box.centerx - self.heart_rect.width/2), 
                                  float(self.battle_box.centery - self.heart_rect.height/2)]
                 self.heart_rect.x = int(self.heart_pos[0])
                 self.heart_rect.y = int(self.heart_pos[1])
            
            self.current_phase = self.PHASE_MENU
            self.bullets = []
            self.dusts = []
            self.debris_particles = []
            self.wind_force = [0, 0]
            if self.enemy_hp < 20:
                self.dialog_text = "* 机器人的核心正在过载。"
            else:
                self.dialog_text = f"* {self.enemy_data.get('name', '变量')} 正在重新编译攻击算法。"
            return

        # Death Sequence Update
        if self.death_sequence_active:
            if self.death_timer > 0:
                self.death_timer -= 1
                return # Freeze logic
            else:
                # Timer done, show YOU DIED
                self.battle_result = "defeat"
                self.running = False
                return

        # Player Movement
        keys = pygame.key.get_pressed()
        
        if self.is_shield_mode:
            # Shield Control
            # Check for inversion (Skill B)
            is_inverted = hasattr(self, 'is_screen_inverted') and self.is_screen_inverted
            
            if is_inverted:
                # Inverted Controls: UP->DOWN, DOWN->UP, LEFT->RIGHT, RIGHT->LEFT
                if keys[pygame.K_UP] or keys[pygame.K_w]: self.shield_dir = "DOWN"
                elif keys[pygame.K_DOWN] or keys[pygame.K_s]: self.shield_dir = "UP"
                elif keys[pygame.K_LEFT] or keys[pygame.K_a]: self.shield_dir = "RIGHT"
                elif keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.shield_dir = "LEFT"
            else:
                # Normal Controls
                if keys[pygame.K_UP] or keys[pygame.K_w]: self.shield_dir = "UP"
                elif keys[pygame.K_DOWN] or keys[pygame.K_s]: self.shield_dir = "DOWN"
                elif keys[pygame.K_LEFT] or keys[pygame.K_a]: self.shield_dir = "LEFT"
                elif keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.shield_dir = "RIGHT"
            
            # Lock Heart
            self.heart_rect.center = self.battle_box.center
            self.heart_pos = [float(self.heart_rect.x), float(self.heart_rect.y)]
            dx, dy = 0, 0
        else:
            dx = 0
            dy = 0
            
            if "samurai_gravity_jump" in self.active_skills:
                # Horizontal
                if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -self.heart_speed
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = self.heart_speed
                
                # Gravity & Jump
                if not hasattr(self, 'heart_vy'): self.heart_vy = 0
                if not hasattr(self, 'gravity'): self.gravity = 0.6
                if not hasattr(self, 'jump_strength'): self.jump_strength = -9
                
                if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and self.on_ground:
                    self.heart_vy = self.jump_strength
                    self.on_ground = False
                
                self.heart_vy += self.gravity
                dy = self.heart_vy
            else:
                if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -self.heart_speed
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = self.heart_speed
                if keys[pygame.K_UP] or keys[pygame.K_w]: dy = -self.heart_speed
                if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy = self.heart_speed
        
        # Thrust Debris
        if "thrust" in self.active_skills and self.enemy_turn_timer % 15 == 0:
            debris_x = random.randint(self.battle_box.left + 10, self.battle_box.right - 10)
            debris_y = random.randint(self.battle_box.top + 10, self.battle_box.bottom - 10)
            if abs(debris_x - self.heart_rect.centerx) > 50 or abs(debris_y - self.heart_rect.centery) > 50:
                debris_rect = pygame.Rect(debris_x, debris_y, 5, 5)
                target_x, target_y = self.heart_rect.center
                dx_debris = target_x - debris_x
                dy_debris = target_y - debris_y
                dist = math.hypot(dx_debris, dy_debris)
                if dist != 0:
                    speed = 3 * self.bullet_speed_multiplier
                    vx = (dx_debris / dist) * speed
                    vy = (dy_debris / dist) * speed
                    self.bullets.append(Bullet(debris_rect, vx, vy, (255, 255, 255), b_type="normal"))

        # Apply Movement
        # Invert Controls if Screen is Inverted
        if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
             # If screen is inverted, visual is flipped.
             # User said: "Completely flip screen".
             # If visual is flipped, standard controls (Up moves visual Up) mean Up key -> dy < 0.
             # But if screen is flipped, "Up" on screen is "Down" in world?
             # Usually, if screen is flipped 180, Up becomes Down.
             # But user said "Anti-gravity... screen completely flip... ensures controls...?"
             # No, user just said "Screen completely flip".
             # If I flip the drawing, I don't need to invert controls logic IF the flip is purely visual.
             # BUT, if the player sees "Up" and presses "Up", they expect to go "Up" relative to their view.
             # If screen is flipped, "Up" in world is "Down" on screen.
             # So if I press "Up" (W), I want to go "Up" on screen.
             # Since "Up" on screen is "Down" in world, I should move "Down" in world.
             # So I should invert controls to match visual flip?
             # Or maybe "Anti-gravity" implies controls are messed up?
             # "Same as Rebel's Blue Shield...". That's Admin Shield logic.
             # Admin Shield uses Arrow Keys to rotate shield.
             # Skill B description: "Attacks are same as Rebel Blue Shield...". 
             # Wait, "Attack method is same as Rebel... Blue Shield blocking bullets".
             # That IS the Shield Minigame (is_shield_mode).
             # In Shield Minigame, player DOES NOT MOVE. They only rotate shield.
             # So movement logic (dx, dy) is ignored anyway!
             # See lines 717-727: if self.is_shield_mode: dx, dy = 0.
             # So I don't need to worry about movement controls for Skill B!
             # Just need to ensure `is_screen_inverted` affects `draw()`.
             pass
        
        self.heart_pos[0] += dx + self.wind_force[0]
        self.heart_pos[1] += dy + self.wind_force[1]
        self.heart_pos[0] = max(self.battle_box.left + 5, min(self.heart_pos[0], self.battle_box.right - self.heart_rect.width - 5))
        
        bottom_limit = self.battle_box.bottom - self.heart_rect.height - 5
        self.heart_pos[1] = max(self.battle_box.top + 5, min(self.heart_pos[1], bottom_limit))

        if "samurai_gravity_jump" in self.active_skills:
             if self.heart_pos[1] >= bottom_limit - 1:
                 self.on_ground = True
                 self.heart_vy = 0
             elif self.heart_pos[1] <= self.battle_box.top + 5:
                 self.heart_vy = 0
        self.heart_rect.x = int(self.heart_pos[0])
        self.heart_rect.y = int(self.heart_pos[1])
        
        # Track if player moved for Yellow Mechanic
        self.player_moved_this_frame = (dx != 0 or dy != 0)

        # Bullet Spawning (Simplified for brevity, copying main logic)
        self.spawn_bullets()
        
        # Shield Mode Update
        if self.is_shield_mode:
            self.update_shield_minigame()
        
        # Bullet Updates & Collision
        enable_reroute = "reroute" in self.active_skills
        reroute_box = self.battle_box if enable_reroute else None
        
        for b in self.bullets[:]:
            b.update(target_rect=self.heart_rect, battle_box=reroute_box)
            
            # Clean up out of bounds
            if b.type != "laser":
                safe_area = self.battle_box.inflate(800, 800)
                if not safe_area.contains(b.rect):
                    self.bullets.remove(b)
                    continue
            
            if b.type == "laser" and b.timer > 100:
                self.bullets.remove(b)
                continue
                
            if hasattr(b, 'alive') and not b.alive:
                self.bullets.remove(b)
                continue
                
            # Collision
            check_rect = b.rect
            if hasattr(b, 'get_hitbox'):
                check_rect = b.get_hitbox()
            
            # Depixelator (Keep as Rect check for now, or adapt?)
            if "depixelator" in self.active_skills:
                dist = math.hypot(b.rect.centerx - self.heart_rect.centerx, b.rect.centery - self.heart_rect.centery)
                if dist < 120:
                    check_rect = b.rect.inflate(-b.rect.width * 0.5, -b.rect.height * 0.5)
            
            # --- Circular Collision Detection ---
            # 1. Calculate distance between Player Heart Center and Bullet Center
            # Use self.player.hitbox_radius (defined in Player) and b.radius (defined in Bullet)
            
            # Ensure bullet has radius (fallback if not present)
            b_radius = getattr(b, 'radius', max(b.rect.width, b.rect.height) / 2)
            
            # Player Hitbox Radius
            p_radius = getattr(self.player, 'hitbox_radius', 4)
            
            # Calculate Centers
            # Note: For Laser, we might stick to Rect collision or treat as line?
            # User instruction: "Stop using colliderect for bullets" -> implies circular for projectiles
            # Lasers are usually rects. Let's keep rect for lasers, circle for others.
            
            is_hit = False
            
            if b.type == "laser" or b.type == "plasma_blade" or b.type == "laser_network":
                 # Rect collision for lasers/blades
                 if self.heart_rect.colliderect(check_rect):
                     is_hit = True
            else:
                 # Circular collision for projectiles
                 dx = self.heart_rect.centerx - b.rect.centerx
                 dy = self.heart_rect.centery - b.rect.centery
                 distance = math.hypot(dx, dy)
                 
                 if distance < (p_radius + b_radius):
                     is_hit = True
            
            if b.damaging and is_hit:
                # Check for Yellow Mechanic (Damage only if moving)
                damage_allowed = True
                if b.type == "yellow_line":
                    # Check if player moved in this frame
                    # We need to track player movement. 
                    # Assuming self.player_moved_this_frame is set in update_heart()
                    if not getattr(self, 'player_moved_this_frame', False):
                        damage_allowed = False
                
                # Blue bullets logic removed to restore damage


                if damage_allowed:
                    self.player.hp -= getattr(b, 'damage', 1)
                    if self.player.hp < 0: self.player.hp = 0 # Clamp HP
                    
                    self.shake_intensity = 10
                    self.damage_flash_timer = 6
                    if b.type != "laser":
                        self.bullets.remove(b)
                    
                    if self.player.hp <= 0:
                        self.handle_player_death()

        # Update Dusts (Skill A)
        if "escape_dust" in self.active_skills:
            for dust in self.dusts:
                dust.update(self.heart_rect, self.battle_box)
                # Collision Check
                if not dust.is_collected and self.heart_rect.colliderect(dust.rect):
                    dust.is_collected = True
                    # Spawn Particles
                    for _ in range(5):
                        self.debris_particles.append(DebrisParticle(dust.rect.centerx, dust.rect.centery))
        
        # Update Debris Particles
        for p in self.debris_particles[:]:
            p.update()
            if p.timer <= 0:
                self.debris_particles.remove(p)

    def update_shield_minigame(self):
        # Shield Recovery
        if hasattr(self, 'shield_broken_timer') and self.shield_broken_timer > 0:
             self.shield_broken_timer -= 1

        # Calculate spawn interval based on progress (Accelerating)
        # Timer: 480 -> 0. 
        # Progress: 0.0 -> 1.0
        progress = 1.0 - (self.enemy_turn_timer / self.ENEMY_TURN_DURATION)
        
        # Interval: Starts at 40, drops to 10
        spawn_interval = int(40 - (30 * progress))
        spawn_interval = max(18, spawn_interval) # Increased min interval to avoid undodgeable clusters
        
        if self.enemy_turn_timer % spawn_interval == 0: 
            # Spawn Arrow
            valid_dirs = ["UP", "DOWN", "LEFT", "RIGHT"]
            
            # If inverted, Top (Visual) is Coordinate Bottom (DOWN). Disable it.
            if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
                if "DOWN" in valid_dirs: valid_dirs.remove("DOWN")

            direction = random.choice(valid_dirs)
            start_pos = [0, 0]
            cx, cy = self.heart_rect.centerx, self.heart_rect.centery
            dist = 300 # Start from far away
            
            if direction == "UP": start_pos = [cx, cy - dist]
            elif direction == "DOWN": start_pos = [cx, cy + dist]
            elif direction == "LEFT": start_pos = [cx - dist, cy]
            elif direction == "RIGHT": start_pos = [cx + dist, cy]
            
            # Determine Type
            arrow_type = 'white'
            # 30% Chance for Blue if Inverted (Skill B)
            if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
                 # Initialize pity counter if not present
                 if not hasattr(self, 'blue_pity_counter'):
                     self.blue_pity_counter = 0
                 
                 # Logic: Base 35% chance OR Force if pity >= 3 (Guarantee at least 1 in 4)
                 is_blue = False
                 if self.blue_pity_counter >= 3:
                     is_blue = True
                     # print("Blue Bullet Forced by Pity System")
                 elif random.random() < 0.35: 
                     is_blue = True
                 
                 if is_blue:
                     arrow_type = 'blue'
                     self.blue_pity_counter = 0
                 else:
                     self.blue_pity_counter += 1
            
            # Apply speed multiplier
            arrow_speed = 5 * self.bullet_speed_multiplier
            self.shield_arrows.append({'pos': start_pos, 'dir': direction, 'speed': arrow_speed, 'type': arrow_type})
            
        # Update Arrows
        for arrow in self.shield_arrows[:]:
            cx, cy = self.heart_rect.centerx, self.heart_rect.centery
            arrow_type = arrow.get('type', 'white')
            
            # Move IN to center (Both White and Blue now spawn from outside)
            dx = cx - arrow['pos'][0]
            dy = cy - arrow['pos'][1]
            dist_to_center = math.hypot(dx, dy)
            
            if dist_to_center > 0:
                arrow['pos'][0] += (dx / dist_to_center) * arrow['speed']
                arrow['pos'][1] += (dy / dist_to_center) * arrow['speed']
            
            # Collision Check
            # Check if hitting shield (Only if shield is active/not broken)
            is_shield_active = True
            if hasattr(self, 'shield_broken_timer') and self.shield_broken_timer > 0:
                is_shield_active = False

            if is_shield_active:
                arrow_rect = pygame.Rect(arrow['pos'][0]-5, arrow['pos'][1]-5, 10, 10)
                
                # Simple check: if close to center and direction matches shield direction
                hit_shield = False
                if dist_to_center < 35: # Close to shield radius
                    if arrow['dir'] == self.shield_dir:
                        hit_shield = True
                
                if hit_shield:
                    if arrow_type == 'blue':
                        # Blue Bullet -> Breaks Shield
                        self.shield_broken_timer = 180 # 3 seconds
                        self.shield_arrows.remove(arrow)
                        if self.calibration_sfx: 
                             self.calibration_sfx.set_volume(0.8)
                             self.calibration_sfx.play()
                    else:
                        # White Bullet -> Blocked
                        self.shield_arrows.remove(arrow)
                        # Play block sound
                        if self.calibration_sfx:
                            self.calibration_sfx.set_volume(0.5)
                            self.calibration_sfx.play()
                    continue
                
            # Check if hitting heart
            if dist_to_center < 10:
                self.shield_arrows.remove(arrow)
                
                # Blue bullets do NO damage (only shield break effect)
                if arrow_type != 'blue':
                    self.player.hp -= 2 
                    self.damage_flash_timer = 5
                    if self.player.hp <= 0:
                        self.handle_player_death()
                continue

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
            time_elapsed = self.ENEMY_TURN_DURATION - self.enemy_turn_timer
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
            time_elapsed = self.ENEMY_TURN_DURATION - self.enemy_turn_timer
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
            time_elapsed = self.ENEMY_TURN_DURATION - self.enemy_turn_timer
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
            time_elapsed = self.ENEMY_TURN_DURATION - self.enemy_turn_timer
            
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
             time_elapsed = self.ENEMY_TURN_DURATION - self.enemy_turn_timer
             
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
            time_elapsed = self.ENEMY_TURN_DURATION - self.enemy_turn_timer
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
            time_elapsed = self.ENEMY_TURN_DURATION - self.enemy_turn_timer
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
                
    def handle_player_death(self):
        if self.death_triggered:
            return
        self.death_triggered = True
        
        self.player.hp = 0
        pygame.mixer.music.stop()
        self.battle_result = "lost"
        self.running = False

    def draw(self):
        if not self.running: return
        
        # Shake
        if self.shake_intensity > 0:
            self.shake_offset = [random.randint(-5, 5), random.randint(-5, 5)]
            self.shake_intensity -= 1
        else:
            self.shake_offset = [0, 0]

        # Render to temp surface for potential inversion
        render_surface = pygame.Surface(self.screen.get_size())
        render_surface.fill((0, 0, 0))
        
        # All drawing goes to render_surface instead of self.screen
        # Replace all self.screen with render_surface in this method block
        # Or just draw normally and flip self.screen at the end? 
        # But self.screen is the display surface. Flipping it using transform is expensive but works.
        # Actually, if I draw to self.screen, I can't flip it easily in place.
        # Better to draw everything to self.screen, then capture it, flip it, and blit back?
        # Or draw to a temp surface.
        # Since this method is long, replacing all 'self.screen' is risky/tedious with SearchReplace.
        # Let's try drawing to self.screen normally, and at the end of draw(), 
        # if inverted, copy screen to surface, flip, and blit back.
        
        self.screen.fill((0, 0, 0))
        
        # Draw Enemy
        enemy_draw_pos = self.enemy_rect.move(self.shake_offset)
        self.screen.blit(self.enemy_img, enemy_draw_pos)
        
        # Draw Energy Shield (REMOVED as per request - Legacy Effect)
        # if self.is_shield_active:
        #      # Draw blue circle/ellipse around enemy
        #      shield_rect = enemy_draw_pos.inflate(20, 20)
        #      pygame.draw.ellipse(self.screen, (0, 200, 255), shield_rect, 4)
        #      pygame.draw.ellipse(self.screen, (0, 255, 255), shield_rect.inflate(-10, -10), 1)

        
        # Draw Enemy HP Bar
        enemy_hp_bar_w, enemy_hp_bar_h = 100, 10
        enemy_hp_x = enemy_draw_pos.right + 20
        enemy_hp_y = enemy_draw_pos.centery
        if enemy_hp_x + enemy_hp_bar_w > SCREEN_WIDTH:
            enemy_hp_x = enemy_draw_pos.centerx - enemy_hp_bar_w // 2
            enemy_hp_y = enemy_draw_pos.bottom + 10
        pygame.draw.rect(self.screen, (100, 0, 0), (enemy_hp_x, enemy_hp_y, enemy_hp_bar_w, enemy_hp_bar_h))
        current_enemy_hp_w = int((self.enemy_hp / self.enemy_max_hp) * enemy_hp_bar_w)
        if current_enemy_hp_w > 0:
            pygame.draw.rect(self.screen, (0, 255, 0), (enemy_hp_x, enemy_hp_y, current_enemy_hp_w, enemy_hp_bar_h))
            
        # Draw Battle Box
        box_draw_rect = self.battle_box.move(self.shake_offset)
        box_color = (0, 255, 255) if "reroute" in self.active_skills else (255, 255, 255)
        pygame.draw.rect(self.screen, box_color, box_draw_rect, 4)
        
        # Draw Magnets
        for magnet in self.magnets:
             m_rect = magnet['rect'].move(self.shake_offset)
             pygame.draw.ellipse(self.screen, (100, 100, 100), m_rect)
             pygame.draw.ellipse(self.screen, (200, 200, 200), m_rect, 2)
        
        # Draw UI
        self.draw_ui(box_draw_rect)
        
        # Draw Phase Content
        if self.current_phase == self.PHASE_MENU:
            text_surf = self.dialog_font.render(self.dialog_text, True, (255, 255, 255))
            self.screen.blit(text_surf, (box_draw_rect.x + 20, box_draw_rect.y + 20))
            
        elif self.current_phase == self.PHASE_ACT_SELECT:
            self.draw_list_selection(box_draw_rect, self.get_act_options(), self.act_selection_idx)
            
        elif self.current_phase == self.PHASE_ITEM_SELECT:
            # Consolidate inventory to ensure display matches logic
            if hasattr(self.player, 'consolidate_inventory'):
                self.player.consolidate_inventory()
                
            consumables = [item for item in self.player.inventory if item.get("type") in ["consumable", "battery"]]
            display_names = []
            for item in consumables:
                name = item.get("name", "Unknown")
                count = item.get("count", 1)
                if count > 1:
                    display_names.append(f"{name} x{count}")
                else:
                    display_names.append(name)
            
            self.draw_list_selection(box_draw_rect, ["取消", f"能量电池 x{self.player.battery_count}"] + display_names, self.item_selection_idx)
            
        elif self.current_phase == self.PHASE_MERCY_SELECT:
            self.draw_list_selection(box_draw_rect, ["取消", "宽恕"], self.mercy_selection_idx)
            
        elif self.current_phase == self.PHASE_FLEE_SELECT:
            self.draw_list_selection(box_draw_rect, ["取消", "逃跑"], self.flee_selection_idx)
            
        elif self.current_phase == self.PHASE_QTE:
            pygame.draw.rect(self.screen, (50, 50, 50), self.qte_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.qte_target_zone)
            pygame.draw.rect(self.screen, (255, 255, 0), self.qte_perfect_zone)
            pygame.draw.rect(self.screen, (255, 255, 255), self.qte_rect, 2)
            needle_draw_x = int(self.qte_needle_x)
            pygame.draw.line(self.screen, (255, 0, 0), (needle_draw_x, self.qte_rect.top), (needle_draw_x, self.qte_rect.bottom), 4)
            
        elif self.current_phase == self.PHASE_PLAYER_ANIM:
            if not self.is_attack_anim:
                text_surf = self.dialog_font.render(self.action_text, True, (255, 255, 255))
                self.screen.blit(text_surf, (box_draw_rect.x + 20, box_draw_rect.y + 20))
                
        elif self.current_phase == self.PHASE_ENEMY_TURN:
            for b in self.bullets:
                b.draw(self.screen, offset=self.shake_offset)

            # Draw Dusts (Skill A)
            if "escape_dust" in self.active_skills:
                for dust in self.dusts:
                    dust.draw(self.screen)

            # Draw Debris Particles
            for p in self.debris_particles:
                p.draw(self.screen)
            
            # Draw Shield and Arrows
            if hasattr(self, 'is_shield_mode') and self.is_shield_mode:
                # Shield
                shield_dist = 25
                shield_len = 32
                shield_thick = 5
                
                cx, cy = self.heart_rect.centerx + self.shake_offset[0], self.heart_rect.centery + self.shake_offset[1]
                shield_rect = pygame.Rect(0, 0, 0, 0)
                
                if self.shield_dir == "UP":
                    shield_rect = pygame.Rect(cx - shield_len//2, cy - shield_dist - shield_thick, shield_len, shield_thick)
                elif self.shield_dir == "DOWN":
                    shield_rect = pygame.Rect(cx - shield_len//2, cy + shield_dist, shield_len, shield_thick)
                elif self.shield_dir == "LEFT":
                    shield_rect = pygame.Rect(cx - shield_dist - shield_thick, cy - shield_len//2, shield_thick, shield_len)
                elif self.shield_dir == "RIGHT":
                    shield_rect = pygame.Rect(cx + shield_dist, cy - shield_len//2, shield_thick, shield_len)
                
                # Shield Color: Deep Blue normally, Light Blue if recovering (broken)
                shield_color = (0, 100, 255)
                if hasattr(self, 'shield_broken_timer') and self.shield_broken_timer > 0:
                    shield_color = (135, 206, 250) # Light Sky Blue
                
                pygame.draw.rect(self.screen, shield_color, shield_rect)
                self.current_shield_rect = shield_rect
                
                # Arrows
                for arrow in self.shield_arrows:
                    p = list(arrow['pos'])
                    p[0] += self.shake_offset[0]
                    p[1] += self.shake_offset[1]
                    
                    size = 10
                    points = []
                    arrow_type = arrow.get('type', 'white')
                    color = (255, 255, 255)
                    if arrow_type == 'blue':
                        color = (0, 191, 255) # Deep Sky Blue
                    
                    if arrow['dir'] == "UP": 
                        points = [[p[0], p[1]+size], [p[0]-size/2, p[1]-size], [p[0]+size/2, p[1]-size]]
                    elif arrow['dir'] == "DOWN": 
                        points = [[p[0], p[1]-size], [p[0]-size/2, p[1]+size], [p[0]+size/2, p[1]+size]]
                    elif arrow['dir'] == "LEFT": 
                        points = [[p[0]+size, p[1]], [p[0]-size, p[1]-size/2], [p[0]-size, p[1]+size/2]]
                    elif arrow['dir'] == "RIGHT": 
                        points = [[p[0]-size, p[1]], [p[0]+size, p[1]-size/2], [p[0]+size, p[1]+size/2]]
                    
                    # Color based on type
                    color = (255, 255, 255)
                    if arrow.get('type') == 'blue':
                        color = (0, 100, 255) # Same as energy shield color
                    
                    pygame.draw.polygon(self.screen, color, points)

            if self.damage_flash_timer > 0:
                self.damage_flash_timer -= 1
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                flash_surf.fill((255, 0, 0))
                flash_surf.set_alpha(100)
                self.screen.blit(flash_surf, (0, 0))
            self.screen.blit(self.heart_img, self.heart_rect.move(self.shake_offset))
            
            # --- Debug Draw Circular Hitbox ---
            # Toggle this via a flag if needed, currently always drawing for verification as requested
            heart_draw_pos = self.heart_rect.move(self.shake_offset)
            pygame.draw.circle(self.screen, (0, 255, 0), heart_draw_pos.center, getattr(self.player, 'hitbox_radius', 4), 1)
            # ----------------------------------
            
        # Draw Damage Popups
        for popup in self.damage_popups:
            text_str, color, pos = popup['val'], popup['color'], popup['pos']
            stroke_color = (0, 0, 0)
            for dx in [-2, 0, 2]:
                for dy in [-2, 0, 2]:
                    self.screen.blit(self.damage_font.render(text_str, True, stroke_color), (pos[0] + dx, pos[1] + dy))
            self.screen.blit(self.damage_font.render(text_str, True, color), pos)

        # DEBUG OVERLAY
        # if "变量" in self.enemy_data.get("name", ""):
        #     debug_str = f"Phase: {self.current_phase} (0=MENU, 2=ENEMY)"
        #     debug_surf = self.font.render(debug_str, True, (0, 255, 0))
        #     self.screen.blit(debug_surf, (10, 10))
            
        # Handle Screen Inversion (Skill B)
        # Capture the screen, flip it, and blit it back
        if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
             # This is expensive, but effective for "completely flip screen"
             # Copy current display
             screen_copy = self.screen.copy()
             # Flip (180 degrees = flip x and y)
             flipped = pygame.transform.flip(screen_copy, True, True)
             self.screen.blit(flipped, (0, 0))

    def draw_ui(self, box_draw_rect):
        status_y = 620
        btn_y = 650
        
        if self.current_phase == self.PHASE_VICTORY:
             # Draw black box at bottom
             dialog_rect = pygame.Rect(50, 600, SCREEN_WIDTH - 100, 150)
             pygame.draw.rect(self.screen, (0, 0, 0), dialog_rect)
             pygame.draw.rect(self.screen, (255, 255, 255), dialog_rect, 2)
             
             # Draw messages
             start_y = 620
             for i, msg in enumerate(self.victory_messages):
                 text_surf = self.dialog_font.render(msg, True, (255, 255, 255))
                 self.screen.blit(text_surf, (80, start_y + i * 30))
             
             # Draw "Press SPACE to continue"
             cont_surf = self.font.render("[SPACE] Continue", True, (150, 150, 150))
             self.screen.blit(cont_surf, (dialog_rect.right - 150, dialog_rect.bottom - 30))
             return
             
        name_surf = self.font.render(f"ANTHE   LV 1", True, (255, 255, 255))
        self.screen.blit(name_surf, (box_draw_rect.left, status_y))
        
        hp_bar_width, hp_bar_height = 100, 20
        hp_x = box_draw_rect.left + 150
        pygame.draw.rect(self.screen, (255, 0, 0), (hp_x, status_y, hp_bar_width, hp_bar_height))
        current_hp_width = int((self.player.hp / self.player.max_hp) * hp_bar_width)
        if current_hp_width > 0:
            pygame.draw.rect(self.screen, (255, 255, 0), (hp_x, status_y, current_hp_width, hp_bar_height))
        hp_text = self.font.render(f"HP {self.player.hp} / {self.player.max_hp}", True, (255, 255, 255))
        self.screen.blit(hp_text, (hp_x + hp_bar_width + 20, status_y))
        
        buttons = ["FIGHT", "ACT", "ITEM", "MERCY"]
        btn_width = 150
        start_x = (SCREEN_WIDTH - (btn_width * 4 + 30)) // 2
        for i, btn_text in enumerate(buttons):
            btn_rect = pygame.Rect(start_x + i * (btn_width + 10), btn_y, btn_width, 40)
            color = (255, 255, 0) if self.current_phase == self.PHASE_MENU and i == self.selected_btn_idx else (255, 165, 0)
            width = 4 if self.current_phase == self.PHASE_MENU and i == self.selected_btn_idx else 2
            pygame.draw.rect(self.screen, color, btn_rect, width)
            text_surf = self.font.render(btn_text, True, color)
            text_rect = text_surf.get_rect(center=btn_rect.center)
            self.screen.blit(text_surf, text_rect)

    def draw_list_selection(self, box_rect, items, selected_idx):
        start_x = box_rect.x + 40
        start_y = box_rect.y + 20
        for i, item in enumerate(items):
            col = i % 2
            row = i // 2
            x = start_x + col * 200
            y = start_y + row * 30
            prefix = "* " if i == selected_idx else "  "
            text_surf = self.dialog_font.render(prefix + item, True, (255, 255, 255))
            self.screen.blit(text_surf, (x, y))
            if i == selected_idx:
                pygame.draw.rect(self.screen, (255, 0, 0), (x - 20, y + 5, 10, 10))
