import pygame
import random
import math
import os
from engine.utils import resource_path, get_font
from engine.config import *
from engine.audio import load_bgm
from engine.pattern_loader import PatternRunner, load_pattern
from entities.bullets import Bullet, PlasmaBlade, LaserNetworkLine, YellowBullet
from entities.particles import BattleDust, DebrisParticle
from engine.battle_spawner import BulletSpawnMixin
from engine.battle_menus import MenuMixin
from engine.battle_shield import ShieldMixin
from engine.battle_render import RenderMixin

class BattleManager(BulletSpawnMixin, MenuMixin, ShieldMixin, RenderMixin):
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

        # Pattern System (JSON-based bullet patterns)
        self.pattern_runner = PatternRunner(self)
        self._has_pattern_skills = False

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

        # FailureEnemy EMP State
        self.game_state = None # 由 Game 注入，用于读取/写入失败之作的秒杀机制是否已瓦解
        self.failure_emp_used = False
        self.anthe_glitch_timer = 0 # 「明日指针」金瞳故障闪屏计时（EMP 瓦解失败之作后触发）
        self.silent_streak = 0 # 变量「静默」彩蛋计数（三回合静默解锁宽恕）
        
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

    # ============================================================
    # 共享辅助方法（去重：心居中 / 缩框 / 退出战斗 / 消耗品列表 / 伤害飘字）
    # ============================================================
    def _recenter_heart(self):
        self.heart_pos = [float(self.battle_box.centerx - self.heart_rect.width / 2),
                          float(self.battle_box.centery - self.heart_rect.height / 2)]
        self.heart_rect.x = int(self.heart_pos[0])
        self.heart_rect.y = int(self.heart_pos[1])

    def _shrink_box(self, w, h=None):
        if not hasattr(self, 'original_battle_box'):
            self.original_battle_box = self.battle_box.copy()
        if h is None:
            h = self.original_battle_box.height
        self.battle_box = pygame.Rect(0, 0, w, h)
        self.battle_box.center = self.original_battle_box.center

    def _exit_battle(self):
        self.current_phase = self.PHASE_PLAYER_ANIM
        self.should_exit_battle = True
        self.action_timer = 90
        self.player.battle_cooldown = 180
        self.player.rect.y += 128

    def _build_consumable_list(self):
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
        display_items = ["取消", f"能量电池 x{self.player.battery_count}"] + display_names
        return display_items, consumables

    def _spawn_damage_popup(self, val, color, pos, timer=90):
        self.damage_popups.append({'val': str(val), 'color': color, 'pos': list(pos), 'timer': timer})

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
        self.silent_streak = 0
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
            # 读取持久化的「电磁脉冲已使用」状态：已瓦解则本场不再有秒杀
            self.failure_emp_used = False
            if self.game_state is not None:
                self.failure_emp_used = getattr(self.game_state, "failure_emp_used", False)

            # Ensure normal start, death happens later
            self.death_sequence_active = False
            self.death_timer = 0

            if not self.failure_emp_used:
                self.dialog_text = "* 失败之作的杀意如实质般压来……只有电磁脉冲能瓦解它的秒杀机制。"
            else:
                self.dialog_text = "* 失败之作 阻挡了你的去路。"

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
            found_path = resource_path("characters/enemies/failure_boss")
            if not os.path.exists(found_path): found_path = resource_path("characters/enemies/failure_boss")
            
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

        # 弃用（跳过）有抠图瑕疵的帧：不删除图片文件，只在动画序列里剔除对应帧（保险起见）
        skip_frames = self.enemy_data.get("skip_frames", [])
        if skip_frames and len(self.enemy_frames) > len(skip_frames):
            skip_set = set(skip_frames)
            self.enemy_frames = [img for i, img in enumerate(self.enemy_frames) if i not in skip_set]

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
                self._spawn_damage_popup("MISS", (150, 150, 150), [self.enemy_rect.centerx, self.enemy_rect.top - 30])
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
            self.player.inventory.append({"name": "黑色游侠的动力炉", "type": "key_item", "description": "黑游侠的核心部件", "tag": "boss_trophy"})
            
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
            items_gained.append("鬼武士的动力炉")
            self.player.inventory.append({"name": "鬼武士的动力炉", "type": "key_item", "description": "鬼武士的核心部件", "tag": "boss_trophy"})
            
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
            self._recenter_heart()

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
                 self._recenter_heart()

        self.enemy_turn_timer = self.ENEMY_TURN_DURATION
        self.bullets = []
        self.laser_warnings = []
        self.lasers = []
        self._recenter_heart()
        
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
            # 若玩家已用电磁脉冲瓦解其秒杀机制，则不再即死，转而走普通攻击
            if not self.failure_emp_used:
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
                self._shrink_box(100, 100)
                
                self._recenter_heart()
                
            elif skill_choice == "black_ranger_c":
                self.dialog_text = "* 黑游侠EX 启动了火力压制。"
                
                # Shrink Battle Box to Small Size (Width 120, Height Normal)
                self._shrink_box(120)
                
                self._recenter_heart()
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
                self._shrink_box(100, 100)
                # Reset Heart to Center
                self._recenter_heart()
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

        # ─── Pattern Loader Integration ───
        # Check for @pattern_name skills and load them
        self._has_pattern_skills = False
        for skill in list(self.active_skills):
            if skill.startswith("@"):
                pattern_name = skill[1:]  # Remove @ prefix
                pattern_data = load_pattern(pattern_name)
                if pattern_data:
                    self.pattern_runner.load(pattern_data)
                    self._has_pattern_skills = True
                    # Replace @pattern skill with a placeholder for tracking
                    self.active_skills.remove(skill)
                    self.active_skills.append("_pattern_loaded")
                else:
                    print(f"Warning: Pattern '{pattern_name}' not found, skipping.")
                    self.active_skills.remove(skill)

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
                    self._spawn_damage_popup(5, (255, 0, 0), self.heart_rect.topright, timer=60)
                    self.shake_intensity = 10
                    # Check death immediately?
                    if self.player.hp <= 0:
                        self.handle_player_death()
                        return

            # Reset Shield Mode immediately if active
            if hasattr(self, 'is_shield_mode') and self.is_shield_mode:
                self.is_shield_mode = False
                self.battle_box = self.original_battle_box
                self._recenter_heart()
            
            # Reset Screen Inversion
            if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
                self.is_screen_inverted = False
            
            # Reset Battle Box for Skill C (if it was shrunk and not shield mode)
            if "black_ranger_c" in self.active_skills and hasattr(self, 'original_battle_box'):
                 self.battle_box = self.original_battle_box
                 self._recenter_heart()
            
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
            self._recenter_heart()
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

        # Pattern Runner (JSON-based bullet patterns)
        if self._has_pattern_skills:
            self.pattern_runner.update()

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


                
    def handle_player_death(self):
        if self.death_triggered:
            return
        self.death_triggered = True
        
        self.player.hp = 0
        pygame.mixer.music.stop()
        self.battle_result = "lost"
        self.running = False



