import pygame
import random
import math
import os
from engine.utils import resource_path, get_font
from engine.config import *
from engine.audio import load_bgm
from engine.pattern_loader import PatternRunner, load_pattern
from entities.bullets import Bullet, PlasmaBlade, LaserNetworkLine, YellowBullet, DancerHead, DancerChaser, DancerRail
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
        self.PHASE_PHASE2_TRANSITION = 9
        
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
        self.difficulty = "explore"  # 难度（main.py 在 start_battle 前注入）
        self.enemy_hp_mult = 1.0     # 敌人血量倍率
        self.enemy_dmg_mult = 1.0    # 敌人伤害倍率
        
        # Combat Entities
        self.damage_popups = []
        self.bullets = []
        self.magnets = []
        self.enemy_turn_timer = 0
        self.ENEMY_TURN_DURATION = 60 * 8
        self.DANCER_DASH_FINISH_BUFFER = 90   # 二阶段技能组1切割完成后，留 1.5s 缓冲再结束回合
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

    def _setup_spring_oscillator(self):
        # 弹簧振子：红心锁定横置窄条中线，沿水平方向做简谐振动（回复力 + 外力 + 阻尼）
        self.wind_force = [0, 0]
        self.spring_center_x = self.battle_box.centerx
        self.spring_disp = 0.0       # 相对平衡位置的位移（正=向右）
        self.spring_vel = 0.0
        self.spring_k = 0.01         # 回复力系数
        self.spring_damping = 0.95   # 阻尼
        self.spring_force = 0.5      # 左右键施加的外力
        self.spring_y = self.battle_box.centery  # 红心纵坐标锁定
        self.heart_pos[0] = self.spring_center_x - self.heart_rect.width / 2.0
        self.heart_pos[1] = self.spring_y - self.heart_rect.height / 2.0
        self.heart_rect.x = int(self.heart_pos[0])
        self.heart_rect.y = int(self.heart_pos[1])

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

    def _apply_difficulty(self):
        """按难度设置敌人数值系数：标准难度 血量 ×1.5、伤害 ×3。"""
        if self.difficulty == "standard":
            self.enemy_hp_mult = 1.5
            self.enemy_dmg_mult = 3.0
        else:
            self.enemy_hp_mult = 1.0
            self.enemy_dmg_mult = 1.0

    def _enemy_damage(self, base):
        """敌人对玩家的实际伤害（标准难度 ×3，四舍五入取整）。"""
        return int(round(base * self.enemy_dmg_mult))

    def start_battle(self, player, enemy_data=None):
        self.player = player
        self.enemy_data = enemy_data if enemy_data else {
            "name": "机凯种·变量",
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
        # 失败之作专属状态也在此重置，避免上一场残留导致新战斗菜单回合丢边框/残留柱子
        self.is_dual_shield = False
        self.is_failure_gravity_hall = False
        self.is_failure_laser_grid = False
        self.failure_phase2 = False
        self.hall_pillars = []
        self.dual_bullets = []
        
        self._apply_difficulty()
        self.enemy_hp = int(round(self.enemy_data.get("hp", 50) * self.enemy_hp_mult))
        self.enemy_max_hp = self.enemy_hp
        self.enemy_turn_timer = self.ENEMY_TURN_DURATION

        # 双阶段战斗状态：血量降到 phase2_hp_ratio 阈值后进二阶段（切换 BGM 等）
        self.phase = 1
        self.phase2_triggered = False
        self.dancer_lock_round_pending = False   # 二阶段濒死锁血演出回合待触发
        self.dancer_lock_round_done = False      # 锁血演出回合已执行（只锁一次）
        self.phase2_cross_side = None

        # 纳米修复液：持续回血 buff（每回合 +regen_amount，持续 regen_turns 回合）
        self.regen_turns = 0
        self.regen_amount = 0
        
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

        if event.type == pygame.KEYUP:
            return

        if event.type == pygame.KEYDOWN:
            # 二段跳：上键第一跳（地面），空中可再跳一次（仅重力压制技能）
            if (self.current_phase == self.PHASE_ENEMY_TURN
                    and "samurai_gravity_jump" in self.active_skills
                    and event.key in (pygame.K_UP, pygame.K_w)):
                if getattr(self, 'on_ground', False):
                    self.heart_vy = getattr(self, 'jump_strength', -9)
                    self.on_ground = False
                    self.jump_count = 1
                elif getattr(self, 'jump_count', 0) < 2:
                    self.heart_vy = getattr(self, 'jump_strength', -9)
                    self.jump_count = 2
            # 重力走廊阶段3（幽灵斩）：上/左触发一次向左跳跃（一段跳，空中不可再跳）
            if (self.current_phase == self.PHASE_ENEMY_TURN
                    and getattr(self, 'is_failure_gravity_hall', False)
                    and self.enemy_turn_timer <= 180
                    and event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a)):
                if getattr(self, 'hall_on_ground', True):
                    self.hall_jump_vx = -9.0   # 朝右视角：向左跳离地面
                    self.hall_on_ground = False
            # 失败之作二阶段1技能·重力幽灵斩：右墙=上/左向左跳；左墙=右向右跳；顶部=下向下跳（一段跳）
            if (self.current_phase == self.PHASE_ENEMY_TURN
                    and getattr(self, 'is_failure_laser_grid', False)
                    and getattr(self, 'laser_gravity_phase', False)
                    and getattr(self, 'laser_slash_spawned', False)):
                if self.laser_gravity_dir == 'right':
                    if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                        if getattr(self, 'laser_on_wall', True):
                            self.laser_jump_vx = -9.0   # 向左跳离右墙
                            self.laser_on_wall = False
                elif self.laser_gravity_dir == 'left':
                    if event.key in (pygame.K_RIGHT, pygame.K_d):
                        if getattr(self, 'laser_on_wall', True):
                            self.laser_jump_vx = 9.0    # 向右跳离左墙
                            self.laser_on_wall = False
                elif self.laser_gravity_dir == 'up':
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        if getattr(self, 'laser_on_ceiling', True):
                            self.laser_jump_vy = 9.0    # 向下跳离天花板
                            self.laser_on_ceiling = False
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
                
            # Phase: Enemy Turn（轨道跑酷：上下键切换轨道）
            elif self.current_phase == self.PHASE_ENEMY_TURN:
                if "conveyor_belt" in self.active_skills:
                    idx = getattr(self, 'conveyor_rail_index', 1)
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.conveyor_rail_index = max(0, idx - 1)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.conveyor_rail_index = min(2, idx + 1)

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
                    if self._can_enter_phase2():
                        # 一阶段血条清空 → 二阶段过渡：随机给左/右舞者打红叉
                        self.phase2_cross_side = random.choice(["left", "right"])
                        self.current_phase = self.PHASE_PHASE2_TRANSITION
                        self.action_timer = 90
                        self.dialog_text = "* 双生舞怜 发生了变化！"
                    elif self._should_trigger_lock_round():
                        # 二阶段濒死：锁血为 1，进入虚弱挣扎的演出回合（锁血轮）
                        self.enemy_hp = 1
                        self.dancer_lock_round_pending = True
                        self.current_phase = self.PHASE_ENEMY_TURN
                        self.start_enemy_turn()
                    else:
                        self.battle_result = "win"
                        self.current_phase = self.PHASE_VICTORY
                        self.process_victory()
                else:
                    self.current_phase = self.next_phase_after_anim
                    if self.current_phase == self.PHASE_ENEMY_TURN:
                        self.start_enemy_turn()

        # 二阶段过渡：红叉动画结束后正式进入二阶段
        elif self.current_phase == self.PHASE_PHASE2_TRANSITION:
            self.action_timer -= 1
            if self.action_timer <= 0:
                self._begin_phase2()
                self.current_phase = self.PHASE_MENU

        # Enemy Turn (Bullets)
        elif self.current_phase == self.PHASE_ENEMY_TURN:
            self.update_enemy_turn()

        # Update Damage Popups
        for popup in self.damage_popups[:]:
            popup['timer'] -= 1
            popup['pos'][1] -= 0.5
            if popup['timer'] <= 0:
                self.damage_popups.remove(popup)

    def _can_enter_phase2(self):
        """一阶段血条清空后是否进入二阶段：仅当配置了 bgm_phase2 且尚未触发。"""
        return (self.phase == 1 and not self.phase2_triggered
                and bool(self.enemy_data) and bool(self.enemy_data.get("bgm_phase2")))

    def _should_trigger_lock_round(self):
        """二阶段濒死时是否触发锁血演出回合：仅双生舞怜，且只锁一次。"""
        return (self.phase == 2
                and "双生舞怜" in self.enemy_data.get("name", "")
                and not self.dancer_lock_round_done)

    def _begin_phase2(self):
        """正式进入二阶段：血量重置为一阶段×phase2_hp_ratio，并切换 BGM。"""
        self.phase2_triggered = True
        self.phase = 2
        ratio = self.enemy_data.get("phase2_hp_ratio", 0.75)
        self.enemy_max_hp = max(1, int(round(self.enemy_max_hp * ratio)))
        self.enemy_hp = self.enemy_max_hp
        phase2_bgm = self.enemy_data.get("bgm_phase2")
        if phase2_bgm:
            load_bgm(phase2_bgm, start_pos=self.enemy_data.get("bgm_phase2_start", 0.0))
            pygame.mixer.music.set_volume(self.enemy_data.get("bgm_volume", 1.0))

    def process_victory(self):
        self.victory_messages = []
        enemy_id = self.enemy_data.get("id") or self.enemy_data.get("boss_id", "")

        # Determine drops
        exp_gain = 0
        items_gained = []

        if enemy_id == "base_5_boss":  # 义军头目
            items_gained.append("黑色游侠的动力炉")
            exp_gain = 5
            # Add item to player inventory
            self.player.inventory.append({"name": "黑色游侠的动力炉", "type": "key_item", "description": "黑游侠的核心部件", "tag": "boss_trophy"})

        elif enemy_id in ("snow_1_2_variable", "pipe_nightmare_1_laser", "pipe_nightmare_1_jump"):
            # 机凯种·变量（含暴走特指·激光/跳跃，玩家眼里同一怪）
            exp_gain = 20

        elif enemy_id == "base_2_machine":  # 机凯种·常量
            exp_gain = 5
            items_gained.append("投掷电池")
            self.player.inventory.append({"name": "投掷电池", "type": "consumable", "description": "一次性电池"})

        elif enemy_id in ("base_3_admin", "base_4_rebel_soldier"):  # 机凯种·义军(女)/(男)
            exp_gain = 10
            items_gained.append("投掷电池")
            self.player.inventory.append({"name": "投掷电池", "type": "consumable", "description": "一次性电池"})

        elif enemy_id == "pipe_nightmare_3_1_robot_mk2":  # 废弃机器人(Ⅱ型)
            exp_gain = 35
        elif enemy_id in ("pipe_nightmare_1_3_robot", "pipe_nightmare_2_3_robot"):  # 废弃机器人(Ⅰ型)
            exp_gain = 30
        elif enemy_id == "pipe_nightmare_3_1_ufo":  # 斯普特尼克
            exp_gain = 35

        elif enemy_id == "pipe_2_2_boss":  # 旧时代智械·鬼武士
            exp_gain = 60
            items_gained.append("鬼武士的动力炉")
            self.player.inventory.append({"name": "鬼武士的动力炉", "type": "key_item", "description": "鬼武士的核心部件", "tag": "boss_trophy"})

        elif enemy_id == "pipe_nightmare_3_2_twin_dancer":  # 双生舞怜
            exp_gain = 100
            items_gained.append("双生舞怜的动力炉")
            self.player.inventory.append({"name": "双生舞怜的动力炉", "type": "key_item", "description": "双生舞怜的核心部件", "tag": "boss_trophy"})

        elif enemy_id == "failure_enemy_01":  # 失败之作
            exp_gain = 100
            items_gained.append("失败之作的破损动力炉")
            # 破损动力炉无法解析，故不加 boss_trophy 标签
            self.player.inventory.append({"name": "失败之作的破损动力炉", "type": "key_item", "description": "失败之作的核心部件（已破损，无法解析）"})

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
            
    def _apply_regen(self):
        """纳米修复液：每回合（敌方回合结束回到菜单时）结算一次持续回血。"""
        if self.regen_turns > 0 and self.player.hp > 0:
            heal = min(self.regen_amount, self.player.max_hp - self.player.hp)
            if heal > 0:
                self.player.hp += heal
                self._spawn_damage_popup(heal, (0, 255, 120), self.heart_rect.topleft, timer=60)
            self.regen_turns -= 1
            if self.regen_turns == 0:
                self.regen_amount = 0

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
        if "black_ranger_c" in self.active_skills or "black_ranger_b" in self.active_skills or "spring_oscillator" in self.active_skills:
             # Already handled by is_shield_mode for B, but C/弹簧振子 need manual reset?
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
        enemy_id = self.enemy_data.get("id") or self.enemy_data.get("boss_id", "")

        # FailureEnemy Special Death Logic (Triggered on Enemy Turn Start)
        if "failure_enemy" in self.enemy_data.get("id", "") and not self.failure_emp_used:
            # 未用电磁脉冲：杀意即死
            self.handle_player_death()
            return

        # 失败之作：血量低于 55% 转二阶段（技能组1 由镜像双心变为 5×5 激光列）
        if enemy_id == "failure_enemy_01" and not getattr(self, 'failure_phase2', False) \
                and self.enemy_hp < self.enemy_max_hp * 0.55:
            self.failure_phase2 = True
            # 二阶段切换 BGM：梦魇
            load_bgm("audio/bgm/nightmare.mp3", start_pos=0.0)
            pygame.mixer.music.set_volume(self.enemy_data.get("bgm_volume", 1.0))

        if enemy_id in ("snow_1_2_variable", "pipe_nightmare_1_laser", "pipe_nightmare_1_jump"):
            # 机凯种·变量（含暴走特指·激光/跳跃，玩家眼里同一怪）
            if random.random() < 0.5:
                self.active_skills = ["laser", "cube"]
                self.dialog_text = f"* {enemy_name} 启动了歼灭模式 (Laser + Sphere)。"
            else:
                self.active_skills = ["random_particles"]
                self.dialog_text = f"* {enemy_name} 启动了散布模式 (Particles)。"
        elif enemy_id == "failure_enemy_01":
            if getattr(self, 'failure_phase2', False):
                # 二阶段：只使用技能组1「5×5 激光列 + 重力幽灵斩」
                self.active_skills = ["failure_laser_grid"]
                self.dialog_text = "* 失败之作 展开了扫描矩阵。"
                self._setup_failure_laser_grid()
            else:
                # 一阶段轮换：1技能原版 → 走廊 → 1技能变体 → 走廊 → 循环
                mod = self.turn_count % 4
                if mod == 1:
                    self.active_skills = ["failure_dual_shield"]
                    self.dialog_text = "* 失败之作 展开了镜像护盾。"
                    self._setup_failure_dual_shield(variant=False)
                elif mod == 2:
                    self.active_skills = ["failure_gravity_hall"]
                    self.dialog_text = "* 失败之作 展开了一条重力走廊。"
                    self._setup_failure_gravity_hall()
                elif mod == 3:
                    self.active_skills = ["failure_dual_shield"]
                    self.dialog_text = "* 失败之作 展开了镜像护盾。"
                    self._setup_failure_dual_shield(variant=True)
                else:
                    self.active_skills = ["failure_gravity_hall"]
                    self.dialog_text = "* 失败之作 展开了一条重力走廊。"
                    self._setup_failure_gravity_hall()
        elif enemy_id == "base_4_rebel_soldier":
            # 男性义军：两技能组交替——奇数回合激光网格，偶数回合弹簧振子
            if self.turn_count % 2 == 1:
                self.active_skills = ["laser_network"]
                self.dialog_text = f"* {enemy_name} 启动了激光网格。"
            else:
                self.active_skills = ["spring_oscillator"]
                self.dialog_text = f"* {enemy_name} 展开了弹簧振子力场。"
                full_w = self.battle_box.width
                self._shrink_box(full_w, 64)
                self._setup_spring_oscillator()
                self.enemy_turn_timer += 3 * 60   # 弹簧回合延长 3 秒
        elif enemy_id == "base_2_machine":
             if random.random() < 0.5:
                self.active_skills = ["ruin_cutting_sequence"]
                self.dialog_text = f"* {enemy_name} 启动了切割序列。"
             else:
                self.active_skills = ["laser_network"]
                self.dialog_text = f"* {enemy_name} 启动了激光网格。"
        # Black Ranger EX Logic
        elif enemy_id == "base_5_boss":
            # Clear previous test skills
            # Randomly select one skill from A, B, C
            
            # Prevent Anti-Gravity (Skill B) on first turn
            available_skills = ["black_ranger_a", "black_ranger_b", "black_ranger_c"]
            if self.turn_count == 1:
                available_skills = ["black_ranger_a", "black_ranger_c"]
                
            skill_choice = random.choice(available_skills)
            self.active_skills = [skill_choice]
            
            if skill_choice == "black_ranger_a":
                self.dialog_text = "* 义军头目 启动了全方位射击。"
                self.bullet_spawn_timer = 0
            elif skill_choice == "black_ranger_b":
                self.dialog_text = "* 义军头目 启动了反重力装置。"
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
                self.dialog_text = "* 义军头目 启动了火力压制。"
                
                # Shrink Battle Box to Small Size (Width 120, Height Normal)
                self._shrink_box(120)
                
                self._recenter_heart()
                self.bullet_spawn_timer = 0
            
        elif enemy_id == "base_3_admin":
            # 1. Shield Mini-game
            # 2. Laser + Ruin Cutting
            # 3. Particles + Spheres
            r = random.random()
            if r < 0.33:
                self.active_skills = ["admin_shield"]
                self.dialog_text = "* 机凯种·义军(女) 启动了能量强袭。"
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
                self.dialog_text = "* 机凯种·义军(女) 启动了混合歼灭模式 (Laser + Cut)。"
            else:
                self.active_skills = ["random_particles", "cube"]
                self.dialog_text = "* 机凯种·义军(女) 启动了粒子风暴模式 (Particle + Sphere)。"
        elif enemy_id == "pipe_2_2_boss":
             # 四技能随机，但避免连续两回合重复同一招
             ghost_skills = ["dark_orb", "samurai_fire_walls", "samurai_gravity_jump", "ghost_slash"]
             chosen = random.choice(ghost_skills)
             if chosen == getattr(self, 'last_ghost_skill', None):
                 chosen = random.choice([s for s in ghost_skills if s != chosen])
             self.last_ghost_skill = chosen

             if chosen == "dark_orb":
                 self.active_skills = ["dark_orb"]
                 self.dialog_text = "* 旧时代智械·鬼武士 释放了暗影球。"
             elif chosen == "samurai_fire_walls":
                 self.active_skills = ["samurai_fire_walls"]
                 self.dialog_text = "* 旧时代智械·鬼武士 释放了业火阵。"
             elif chosen == "samurai_gravity_jump":
                 self.active_skills = ["samurai_gravity_jump"]
                 self.dialog_text = "* 旧时代智械·鬼武士 释放了重力压制。"
                 self.heart_vy = 0
                 self.gravity = 0.6
                 self.jump_strength = -9
                 self.on_ground = True
                 self.jump_count = 0
             else:
                 self.active_skills = ["ghost_slash"]
                 self.dialog_text = "* 旧时代智械·鬼武士 释放了幽灵斩。"
        elif enemy_id == "pipe_nightmare_3_1_ufo":
            self.active_skills = ["ufo_tractor"]
            if self.turn_count == 1:
                # 新战斗：激光列固定（左或右，整场不变）
                self.ufo_laser_col = random.choice([0, 2])
                # 第一回合重力固定中间，教学「紫条无害」
                self.ufo_gravity_col = 1
            else:
                # 后续回合：重力交替到另一个非激光列
                non_l = [c for c in range(3) if c != self.ufo_laser_col]
                self.ufo_gravity_col = non_l[1] if self.ufo_gravity_col == non_l[0] else non_l[0]
            self.ufo_gravity_time = 0
            self.dialog_text = "* 斯普特尼克 启动了牵引光束。"
        elif enemy_id == "pipe_nightmare_3_1_robot_mk2":
            # 两个技能组交替：奇数回合=废料传送带（切轨），偶数回合=重力摆锤（单摆）
            if self.turn_count % 2 == 1:
                self.active_skills = ["conveyor_belt"]
                self.wind_force = [0, 0]
                # 轨道跑酷：三条虚线轨道，红心挂中间轨，上下键切轨
                lane_h = self.battle_box.height // 3
                self.conveyor_rail_ys = [self.battle_box.top + lane_h * (i + 0.5) for i in range(3)]
                self.conveyor_rail_index = 1
                self.heart_pos[0] = self.battle_box.centerx - self.heart_rect.width / 2.0
                self.heart_pos[1] = self.conveyor_rail_ys[1] - self.heart_rect.height / 2.0
                self.heart_rect.x = int(self.heart_pos[0])
                self.heart_rect.y = int(self.heart_pos[1])
                self.dialog_text = "* 废弃机器人(Ⅱ型) 启动了废料传送带。"
            else:
                self.active_skills = ["pendulum"]
                self.wind_force = [0, 0]
                # 单摆：摆锤从顶部枢轴挂下，沿圆形轨道摆动，左右键施加力矩
                self.pend_pivot = (self.battle_box.centerx, self.battle_box.top)
                self.pend_len = 150
                self.pend_angle = 0.0
                self.pend_omega = 0.0
                self.pend_k = 0.004        # 重力回复强度
                self.pend_torque = 0.0025   # 玩家左右键力矩
                self.pend_damping = 0.99
                self.pend_max_angle = 1.22  # 最大摆角 ~70°
                # 不可见的垂直固定路径：3 主列 + 2 间隙列；首块废料强制走中间列逼迫起摆
                self.pend_col_xs = [self.battle_box.left + self.battle_box.width * k / 6 for k in range(1, 6)]
                self.pend_first_scrap = True
                bx = self.pend_pivot[0] + self.pend_len * math.sin(self.pend_angle)
                by = self.pend_pivot[1] + self.pend_len * math.cos(self.pend_angle)
                self.heart_pos[0] = bx - self.heart_rect.width / 2.0
                self.heart_pos[1] = by - self.heart_rect.height / 2.0
                self.heart_rect.x = int(self.heart_pos[0])
                self.heart_rect.y = int(self.heart_pos[1])
                self.dialog_text = "* 废弃机器人(Ⅱ型) 启动了重力摆锤。"
        elif enemy_id == "pipe_nightmare_3_2_twin_dancer":
            self.wind_force = [0, 0]
            # 加载单个舞者头颅像（65 开头资源），裁剪透明边后缩放（两技能共用）
            if not hasattr(self, 'dancer_head_img'):
                try:
                    hp = resource_path("characters/enemies/twin_dancer/65f5c91c41ab43abbbce7883b24bd422.png")
                    head_img = pygame.image.load(hp).convert_alpha()
                    try:
                        bbox = pygame.mask.from_surface(head_img).get_bounding_rects()[0]
                        if bbox.width > 0 and bbox.height > 0:
                            head_img = head_img.subsurface(bbox)
                    except Exception:
                        pass
                    h = 64
                    scale = h / head_img.get_height()
                    head_img = pygame.transform.scale(head_img, (int(head_img.get_width() * scale), h))
                    self.dancer_head_img = head_img
                except Exception as e:
                    print(f"Failed to load dancer head: {e}")
                    self.dancer_head_img = pygame.Surface((48, 48), pygame.SRCALPHA)
                    pygame.draw.circle(self.dancer_head_img, (200, 180, 220), (24, 24), 22)
            # 二阶段锁血演出回合：只剩一只虚弱舞者，用速度减半的斜线冲刺做最后挣扎
            if self.dancer_lock_round_pending:
                self.dancer_lock_round_pending = False
                self.dancer_lock_round_done = True
                self.active_skills = ["dancer_dash"]
                self.bullets.append(DancerHead(self.dancer_head_img, "left", self.battle_box, 0, weak=True))
                self.dialog_text = "* 双生舞怜 用尽最后的力气冲了过来。"
                return
            # 一阶段三技能循环：1=机枢舞者（斜线冲刺），2=田字格追逐，0=苏联国徽单摆
            mod = self.turn_count % 3
            if mod == 1:
                self.active_skills = ["dancer_dash"]
                if self.phase == 2:
                    # 二阶段：每次只刷新一个舞者，前摇 0.2s、速度 +20%、轨迹留红激光
                    side = random.choice(["left", "right"])
                    self.bullets.append(DancerHead(self.dancer_head_img, side, self.battle_box, 0,
                                                   phase2=True, bullets_ref=self.bullets))
                else:
                    # 左右各一只颅像，右侧延迟 60 帧（1s）错开节奏
                    self.bullets.append(DancerHead(self.dancer_head_img, "left", self.battle_box, 0))
                    self.bullets.append(DancerHead(self.dancer_head_img, "right", self.battle_box, 60))
                self.dialog_text = "* 双生舞怜 起舞了。"
            elif mod == 2:
                self.active_skills = ["dancer_chase"]
                # 田字格几何：战斗框内部一个完整独立的"田"字（外框 + 十字），四周留边距
                m = 40
                self.dancer_grid_cols = [self.battle_box.left + m, self.battle_box.centerx, self.battle_box.right - m]
                self.dancer_grid_rows = [self.battle_box.top + m, self.battle_box.centery, self.battle_box.bottom - m]
                # 玩家出生在田字格中央节点 (1,1)，之后沿虚线网格行走
                self.dancer_pgrid = (1, 1)
                self.dancer_ptarget = None
                self.heart_pos[0] = self.dancer_grid_cols[1] - self.heart_rect.width / 2.0
                self.heart_pos[1] = self.dancer_grid_rows[1] - self.heart_rect.height / 2.0
                self.heart_rect.x = int(self.heart_pos[0])
                self.heart_rect.y = int(self.heart_pos[1])
                # 燃烧路径：二阶段追击者走过的边集合（边 → 剩余燃烧帧数），玩家完整经过会一次性扣 2 血
                self.dancer_burned_edges = {}
                if self.phase == 2:
                    # 二阶段：只剩一只追击者（游荡者已败），速度 1.5 倍，走过路径燃烧
                    self.bullets.append(DancerChaser(self.dancer_head_img, self.dancer_grid_cols,
                                                     self.dancer_grid_rows, (1, 0), "chase",
                                                     phase2=True, burned_edges=self.dancer_burned_edges))
                else:
                    # 左右各一只，左追右游荡（错峰）
                    self.bullets.append(DancerChaser(self.dancer_head_img, self.dancer_grid_cols, self.dancer_grid_rows, (1, 0), "chase"))
                    self.bullets.append(DancerChaser(self.dancer_head_img, self.dancer_grid_cols, self.dancer_grid_rows, (1, 2), "wander"))
                self.dialog_text = "* 双生舞怜 摆开了阵势。"
            else:
                self.active_skills = ["soviet_emblem"]
                # 苏联国徽单摆：金色地球 + 下半圆下摆，玩家挂在摆锤上沿下摆弧摆动
                self.pend_pivot = (self.battle_box.centerx, self.battle_box.top + 90)
                self.pend_len = 120
                self.pend_angle = 0.0
                self.pend_omega = 0.0
                self.pend_damping = 0.99
                self.pend_max_angle = 1.57   # 半圆（摆到左右水平）
                if self.phase == 2:
                    # 二阶段：中央重力域（覆盖整条单摆的圆形力场），只剩一只舞者
                    self.pend_k = 0.008          # 更强重力（一阶段 0.004 的两倍）
                    self.pend_torque = 0.0025
                    self.grav_pulse_interval = 150   # 重力脉冲周期 2.5s
                    self.grav_pulse_duration = 45    # 每次脉冲持续 0.75s
                    self.grav_pulse_k_mult = 4.0     # 脉冲期间重力 ×4
                    self.grav_pulse_torque_mult = 0.35  # 脉冲期间玩家力矩 ×0.35
                    self.grav_pulse_timer = 0
                    self.grav_pulse_on = False
                else:
                    self.pend_k = 0.004
                    self.pend_torque = 0.0025
                bx = self.pend_pivot[0] + self.pend_len * math.sin(self.pend_angle)
                by = self.pend_pivot[1] + self.pend_len * math.cos(self.pend_angle)
                self.heart_pos[0] = bx - self.heart_rect.width / 2.0
                self.heart_pos[1] = by - self.heart_rect.height / 2.0
                self.heart_rect.x = int(self.heart_pos[0])
                self.heart_rect.y = int(self.heart_pos[1])
                if self.phase == 2:
                    # 二阶段：只剩一只舞者，速度 +20%，每次冲刺后横/竖轨迹交替
                    self.bullets.append(DancerRail(self.dancer_head_img, self.battle_box, "vertical", 0, phase2=True))
                else:
                    # 一阶段两个舞者：一竖轨、一横轨（横轨延迟 45 帧错峰）
                    self.bullets.append(DancerRail(self.dancer_head_img, self.battle_box, "vertical", 0))
                    self.bullets.append(DancerRail(self.dancer_head_img, self.battle_box, "horizontal", 45))
                self.dialog_text = "* 双生舞怜 铭刻了赤色纹章。"
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

    def _setup_failure_dual_shield(self, variant=False):
        """失败之作技能组1「镜像双心」：左右两个对称区域，中间挡板，各一锁心红心 + 能量护盾。
        variant=False 原版：左半场上刷、右半场右刷；variant=True 变体：左半场下刷、右半场从挡板左刷。"""
        box = self.battle_box
        side = 120   # 每个区域边长
        gap = 112    # 两个区域相隔的距离（中间挡板区）
        cy = box.centery
        left_cx = box.centerx - gap / 2.0 - side / 2.0
        right_cx = box.centerx + gap / 2.0 + side / 2.0
        self.is_dual_shield = True
        self.dual_shield_variant = variant
        # 左右两个对称区域矩形
        self.dual_left_rect = pygame.Rect(int(left_cx - side / 2.0), int(cy - side / 2.0), side, side)
        self.dual_right_rect = pygame.Rect(int(right_cx - side / 2.0), int(cy - side / 2.0), side, side)
        # 红心锁在各自区域中央
        self.dual_left_center = [float(self.dual_left_rect.centerx), float(self.dual_left_rect.centery)]
        self.dual_right_center = [float(self.dual_right_rect.centerx), float(self.dual_right_rect.centery)]
        if variant:
            self.left_shield_dir = "DOWN"   # 变体：左护盾朝下，挡从正下方刷来的箭头
            self.right_shield_dir = "LEFT"  # 变体：右护盾朝左，挡从左边挡板刷来的箭头
        else:
            self.left_shield_dir = "UP"     # 原版：左护盾朝上，挡从正上方刷来的箭头
            self.right_shield_dir = "RIGHT" # 原版：右护盾朝右，挡从正右方刷来的箭头
        self.dual_bullets = []
        self.dual_bullet_timer = 0
        self.dual_right_bullet_timer = 0   # 变体右半场独立刷新计时（减缓 25%）
        self.dual_right_next_type = 'white'  # 变体右半场下一发颜色（固定一白一蓝交替）
        self.left_shield_broken_timer = 0   # 左护盾被蓝箭头打破后的失效倒计时（3 秒）
        self.right_shield_broken_timer = 0  # 右护盾同理
        # 主红心立即锁到左心（右心由 update_failure_dual_shield 用独立坐标管理）
        self.heart_pos[0] = self.dual_left_center[0] - self.heart_rect.width / 2.0
        self.heart_pos[1] = self.dual_left_center[1] - self.heart_rect.height / 2.0
        self.heart_rect.x = int(self.heart_pos[0])
        self.heart_rect.y = int(self.heart_pos[1])

    def _dual_shield_rect(self, center, direction):
        """返回护盾矩形（复用能量护盾的视觉/尺寸），护盾挡「从该方向来」的子弹。"""
        cx, cy = center
        shield_dist = 25
        shield_len = 32
        shield_thick = 5
        if direction == "UP":
            return pygame.Rect(cx - shield_len // 2, cy - shield_dist - shield_thick, shield_len, shield_thick)
        if direction == "DOWN":
            return pygame.Rect(cx - shield_len // 2, cy + shield_dist, shield_len, shield_thick)
        if direction == "LEFT":
            return pygame.Rect(cx - shield_dist - shield_thick, cy - shield_len // 2, shield_thick, shield_len)
        return pygame.Rect(cx + shield_dist, cy - shield_len // 2, shield_thick, shield_len)

    def _dual_shield_hit(self, pos):
        """红心被白色子弹命中：扣 2 血 + 反馈。"""
        dmg = self._enemy_damage(2)
        self.player.hp -= dmg
        if self.player.hp < 0:
            self.player.hp = 0
        self.shake_intensity = 8
        self.damage_flash_timer = 5
        self._spawn_damage_popup(dmg, (255, 255, 255), pos, timer=40)
        if self.player.hp <= 0:
            self.handle_player_death()

    def update_failure_dual_shield(self):
        """双心护盾（义军头目式箭头弹幕）：箭头从足够远的地方刷来，朝对应红心飞去。
        左半场：从屏幕最上方（固定 x = 左心中心）竖直向下，单线轨迹。
        右半场：从正右方（固定 y = 右心中心）水平向左，单线轨迹。
        白色箭头：被护盾挡住，撞红心扣 2 血。
        蓝色箭头：撞护盾会打破护盾（该侧 3 秒失效），撞红心无伤害（穿过）。
        箭头随回合进度越来越快、越来越密。"""
        lcx, lcy = self.dual_left_center
        rcx, rcy = self.dual_right_center
        progress = 1.0 - (self.enemy_turn_timer / self.ENEMY_TURN_DURATION)

        # 护盾破损倒计时（左右独立，各 3 秒）
        if self.left_shield_broken_timer > 0:
            self.left_shield_broken_timer -= 1
        if self.right_shield_broken_timer > 0:
            self.right_shield_broken_timer -= 1

        # 生成箭头（从足够远的地方，固定单线轨迹）
        spawn_interval = max(25, int(47.5 - 20 * progress))
        self.dual_bullet_timer += 1
        if self.dual_bullet_timer >= spawn_interval:
            self.dual_bullet_timer = 0
            speed = 5.0 * self.bullet_speed_multiplier
            if getattr(self, 'dual_shield_variant', False):
                # 变体：左半场从最下方竖直向上（右半场独立计时、减缓 25%，见下方）
                ltype = 'blue' if random.random() < 0.25 else 'white'
                self.dual_bullets.append({'pos': [float(lcx), lcy + 300.0], 'dir': 'DOWN',
                                          'speed': speed, 'type': ltype, 'side': 'left'})
            else:
                # 原版：左半场从最上方竖直向下；右半场从正右方水平向左（同帧同速）
                ltype = 'blue' if random.random() < 0.25 else 'white'
                self.dual_bullets.append({'pos': [float(lcx), lcy - 300.0], 'dir': 'UP',
                                          'speed': speed, 'type': ltype, 'side': 'left'})
                rtype = 'blue' if random.random() < 0.25 else 'white'
                self.dual_bullets.append({'pos': [rcx + 300.0, float(rcy)], 'dir': 'RIGHT',
                                          'speed': speed, 'type': rtype, 'side': 'right'})

        # 变体右半场：独立计时，刷新间隔 +25%（减缓 25%），飞行速度 -25%，方便玩家反应
        if getattr(self, 'dual_shield_variant', False):
            self.dual_right_bullet_timer += 1
            right_interval = max(1, int(spawn_interval * 1.25))
            if self.dual_right_bullet_timer >= right_interval:
                self.dual_right_bullet_timer = 0
                speed = 5.0 * self.bullet_speed_multiplier
                # 固定一白一蓝交替，方便玩家背板
                rtype = getattr(self, 'dual_right_next_type', 'white')
                self.dual_right_next_type = 'blue' if rtype == 'white' else 'white'
                mid_x = (self.dual_left_rect.right + self.dual_right_rect.left) / 2.0
                self.dual_bullets.append({'pos': [float(mid_x), float(rcy)], 'dir': 'LEFT',
                                          'speed': speed * 0.75, 'type': rtype, 'side': 'right'})

        right_rect = pygame.Rect(int(rcx - 16), int(rcy - 16), 32, 32)

        for b in self.dual_bullets[:]:
            cx, cy = (lcx, lcy) if b['side'] == 'left' else (rcx, rcy)
            # 朝对应红心中心移动
            dx = cx - b['pos'][0]
            dy = cy - b['pos'][1]
            d0 = math.hypot(dx, dy)
            if d0 > 0:
                b['pos'][0] += (dx / d0) * b['speed']
                b['pos'][1] += (dy / d0) * b['speed']

            # 移动后重新计算到中心的距离
            dx = cx - b['pos'][0]
            dy = cy - b['pos'][1]
            dist_to_center = math.hypot(dx, dy)
            btype = b.get('type', 'white')

            if b['side'] == 'left':
                shield_dir = self.left_shield_dir
                shield_broken = self.left_shield_broken_timer > 0
            else:
                shield_dir = self.right_shield_dir
                shield_broken = self.right_shield_broken_timer > 0

            # 撞护盾（护盾未破损 + 进入护盾范围 + 方向匹配）
            if not shield_broken and dist_to_center < 35 and b['dir'] == shield_dir:
                if btype == 'blue':
                    if b['side'] == 'left':
                        self.left_shield_broken_timer = 180  # 蓝箭头破左盾
                    else:
                        self.right_shield_broken_timer = 180
                    if self.calibration_sfx:
                        self.calibration_sfx.set_volume(0.8)
                        self.calibration_sfx.play()
                else:
                    # 白箭头被护盾抵消：播放挡弹音效（与义军头目/能量护盾一致）
                    if self.calibration_sfx:
                        self.calibration_sfx.set_volume(0.5)
                        self.calibration_sfx.play()
                self.dual_bullets.remove(b)
                continue

            # 撞红心
            if dist_to_center < 10:
                self.dual_bullets.remove(b)
                if btype != 'blue':  # 蓝箭头穿心无伤害
                    hit_pos = self.heart_rect.topright if b['side'] == 'left' else right_rect.topright
                    self._dual_shield_hit(hit_pos)
                continue

    # ================= 失败之作二阶段·5×5 激光列 =================
    def _setup_failure_laser_grid(self):
        """失败之作二阶段技能组1「5×5 扫描矩阵」：战斗区域横向 5 等分，心自由移动（连续）。
        4 轮动作：1 轮激光扫射 + 3 轮重力幽灵斩（方向随机：左/右墙竖斩、顶部横斩）。
        左下/右下角感叹号频闪 2 次后，苗条竖激光条从感叹号侧快速平移，扫到绿色安全列前消失。"""
        box = self.battle_box
        self.is_failure_laser_grid = True
        self.laser_grid_rect = box.copy()
        self.laser_cell_w = box.width / 5.0   # 每列宽度（绿色安全列宽度）
        self.laser_exclaim_side = random.choice(['left', 'right'])  # 感叹号在左下/右下
        self.laser_state = 'warn'   # warn（感叹号频闪）→ active（激光条平移）
        self.laser_timer = 0
        self.laser_hit_cooldown = 0
        self.laser_bar_w = 30                # 激光条宽度（苗条）
        self.laser_bar_x = 0.0               # 激光条左边缘 x（平移位置）
        self.laser_sweep_dir = 0             # +1 向右扫 / -1 向左扫
        self.laser_sweep_speed = 11.0        # 每帧平移像素（快速，+10%）
        # 4 轮动作：激光扫射随机插在任意一次，其余为斩（左/右/上随机）
        _seq = ['slash', 'slash', 'slash', 'slash']
        _seq[random.randint(0, 3)] = 'sweep'
        self.laser_action_seq = _seq
        self.laser_action_idx = 0
        self.laser_gravity_phase = False     # 当前动作是否为斩（True=斩，False=扫射）
        self.laser_gravity_dir = None        # 斩方向：'left'/'right'/'up'
        self.laser_on_wall = True            # 水平斩：是否贴墙（左/右）
        self.laser_jump_vx = 0.0             # 水平斩：跳跃水平速度
        self.laser_on_ceiling = True         # 向上斩：是否贴顶（天花板）
        self.laser_jump_vy = 0.0             # 向上斩：跳跃垂直速度（正=向下跳离）
        self.laser_slash_spawned = False     # 当前斩是否已生成幽灵斩（吸引到位后）
        self.laser_pull_vx = 0.0             # 水平吸引速度（重力加速，负=向左）
        self.laser_pull_vy = 0.0             # 垂直吸引速度（负=向上）
        # 回合延长：4 轮动作（1 扫射 + 3 斩）
        self.enemy_turn_timer = self.ENEMY_TURN_DURATION + 8 * 60
        # 心自由移动到战斗区域中央
        self._recenter_heart()
        # 若第一个动作就是斩，需立即进入斩动作（否则会因 laser_gravity_phase 初值 False 误走激光扫射分支）
        if self.laser_action_seq[0] == 'slash':
            self._start_laser_gravity()

    def update_failure_laser_grid(self):
        """按动作序列推进：1 轮激光扫射 → 3 轮重力幽灵斩，全部完成后回合收尾。"""
        if self.laser_action_idx >= len(self.laser_action_seq):
            # 全部动作完成，回合提前收尾
            self.enemy_turn_timer = min(self.enemy_turn_timer, 15)
            return
        if not self.laser_gravity_phase:
            self._update_laser_sweep()   # 当前动作：激光扫射（单轮）
        else:
            self._update_laser_gravity()  # 当前动作：重力幽灵斩
            # 斩挥完 → 进入下一动作
            if getattr(self, 'laser_slash_spawned', False) \
                    and not any(getattr(b, 'type', '') == 'ground_slash' for b in self.bullets):
                self._next_laser_action()

    def _update_laser_sweep(self):
        """单轮激光扫射：感叹号频闪 2 次 → 苗条激光条平移扫过 → 扫完进入下一动作。"""
        box = self.battle_box
        cw = int(self.laser_cell_w)
        self.laser_timer += 1
        self.laser_hit_cooldown = max(0, self.laser_hit_cooldown - 1)
        if self.laser_state == 'warn':
            if self.laser_timer >= 72:
                # 频闪 2 次结束，激光条从感叹号那一侧刷出（绿色区的对侧）
                self.laser_state = 'active'
                self.laser_timer = 0
                self.laser_hit_cooldown = 0
                if self.laser_exclaim_side == 'left':
                    # 绿色区在右，激光条从最左向右扫
                    self.laser_bar_x = float(box.left)
                    self.laser_sweep_dir = 1
                else:
                    # 绿色区在左，激光条从最右向左扫
                    self.laser_bar_x = float(box.right - self.laser_bar_w)
                    self.laser_sweep_dir = -1
        elif self.laser_state == 'active':
            # 激光条快速平移
            self.laser_bar_x += self.laser_sweep_dir * self.laser_sweep_speed
            bar_rect = pygame.Rect(int(self.laser_bar_x), box.top, self.laser_bar_w, box.height)
            if self.heart_rect.colliderect(bar_rect) and self.laser_hit_cooldown <= 0:
                dmg = self._enemy_damage(1)
                self.player.hp -= dmg
                if self.player.hp < 0:
                    self.player.hp = 0
                self.shake_intensity = 8
                self.damage_flash_timer = 5
                self._spawn_damage_popup(dmg, (80, 160, 255), self.heart_rect.topright, timer=40)
                self.laser_hit_cooldown = 20
                if self.player.hp <= 0:
                    self.handle_player_death()
            # 激光条扫到绿色安全列边界即消失，本轮结束
            done = (self.laser_bar_x <= box.left + cw) if self.laser_sweep_dir < 0 \
                else (self.laser_bar_x + self.laser_bar_w >= box.right - cw)
            if done:
                self._next_laser_action()

    def _next_laser_action(self):
        """当前动作结束，进入下一个动作（扫射/斩）。"""
        self.laser_action_idx += 1
        if self.laser_action_idx >= len(self.laser_action_seq):
            return
        if self.laser_action_seq[self.laser_action_idx] == 'slash':
            self._start_laser_gravity()
        else:
            # 下一轮仍是扫射（当前序列不会发生，防御性处理）
            self.laser_gravity_phase = False
            self.laser_state = 'warn'
            self.laser_timer = 0
            self.laser_exclaim_side = random.choice(['left', 'right'])

    def _start_laser_gravity(self):
        """进入斩动作：设定重力方向（左/右/上），心先被重力加速吸到边缘（有过程）。"""
        box = self.battle_box
        self.laser_gravity_phase = True
        self.laser_gravity_dir = random.choice(['left', 'right', 'up'])
        self.laser_slash_spawned = False     # 幽灵斩未生成，先进入吸引阶段
        if self.laser_gravity_dir in ('left', 'right'):
            self.laser_pull_vx = 0.0         # 水平吸引速度从 0 加速
            # 垂直轴一次性居中（吸引主轴是水平）
            self.heart_pos[1] = float(box.centery - self.heart_rect.height / 2.0)
            self.heart_rect.y = int(self.heart_pos[1])
        else:
            self.laser_pull_vy = 0.0         # 向上吸引速度从 0 加速（负=向上）
            # 水平轴一次性居中（吸引主轴是垂直）
            self.heart_pos[0] = float(box.centerx - self.heart_rect.width / 2.0)
            self.heart_rect.x = int(self.heart_pos[0])

    def _spawn_laser_gravity_slash(self):
        """心被吸到边缘后刷出幽灵斩，进入贴边跳躲阶段。"""
        from entities.bullets import GroundSlash
        box = self.battle_box
        self.laser_slash_spawned = True
        if self.laser_gravity_dir == 'right':
            self.bullets.append(GroundSlash(box, side='right'))   # 右墙竖斩
            self.laser_on_wall = True
            self.laser_jump_vx = 0.0
        elif self.laser_gravity_dir == 'left':
            self.bullets.append(GroundSlash(box, side='left'))    # 左墙竖斩
            self.laser_on_wall = True
            self.laser_jump_vx = 0.0
        else:
            self.bullets.append(GroundSlash(box, side='top'))     # 顶部横斩
            self.laser_on_ceiling = True
            self.laser_jump_vy = 0.0

    def _update_laser_gravity(self):
        """斩动作：吸引期心被重力加速吸到边缘（不再瞬移），到位刷幽灵斩；贴边期跳躲（一段跳）。"""
        box = self.battle_box
        if not self.laser_slash_spawned:
            # ===== 吸引期：重力加速把心吸到边缘 =====
            if self.laser_gravity_dir in ('left', 'right'):
                sign = 1 if self.laser_gravity_dir == 'right' else -1
                self.laser_pull_vx += 0.5 * sign
                if abs(self.laser_pull_vx) > 8.0:
                    self.laser_pull_vx = 8.0 * sign
                self.heart_pos[0] += self.laser_pull_vx
                if sign > 0:
                    right_limit = float(box.right - self.heart_rect.width - 5)
                    if self.heart_pos[0] >= right_limit:
                        self.heart_pos[0] = right_limit
                        self._spawn_laser_gravity_slash()
                else:
                    left_limit = float(box.left + 5)
                    if self.heart_pos[0] <= left_limit:
                        self.heart_pos[0] = left_limit
                        self._spawn_laser_gravity_slash()
                self.heart_rect.x = int(self.heart_pos[0])
            else:  # 'up'
                self.laser_pull_vy -= 0.5
                if self.laser_pull_vy < -8.0:
                    self.laser_pull_vy = -8.0
                self.heart_pos[1] += self.laser_pull_vy
                top_limit = float(box.top + 5)
                if self.heart_pos[1] <= top_limit:
                    self.heart_pos[1] = top_limit
                    self._spawn_laser_gravity_slash()
                self.heart_rect.y = int(self.heart_pos[1])
        elif self.laser_gravity_dir in ('left', 'right'):
            # ===== 贴边期：左右墙，跳离躲竖斩 =====
            sign = 1 if self.laser_gravity_dir == 'right' else -1
            wall_limit = float(box.right - self.heart_rect.width - 5) if sign > 0 else float(box.left + 5)
            opp_limit = float(box.left + 5) if sign > 0 else float(box.right - self.heart_rect.width - 5)
            if self.laser_on_wall:
                self.heart_pos[0] = wall_limit
            else:
                self.laser_jump_vx += 0.6 * sign   # 受重力拉回墙
                self.heart_pos[0] += self.laser_jump_vx
                if (sign > 0 and self.heart_pos[0] >= wall_limit) or (sign < 0 and self.heart_pos[0] <= wall_limit):
                    self.heart_pos[0] = wall_limit
                    self.laser_jump_vx = 0.0
                    self.laser_on_wall = True
                elif (sign > 0 and self.heart_pos[0] < opp_limit) or (sign < 0 and self.heart_pos[0] > opp_limit):
                    self.heart_pos[0] = opp_limit
            self.heart_rect.x = int(self.heart_pos[0])
        else:
            # ===== 贴边期：顶部，下键跳离躲横斩 =====
            top_limit = float(box.top + 5)
            bottom_limit = float(box.bottom - self.heart_rect.height - 5)
            if self.laser_on_ceiling:
                self.heart_pos[1] = top_limit
            else:
                self.laser_jump_vy -= 0.6
                self.heart_pos[1] += self.laser_jump_vy
                if self.heart_pos[1] <= top_limit:
                    self.heart_pos[1] = top_limit
                    self.laser_jump_vy = 0.0
                    self.laser_on_ceiling = True
                elif self.heart_pos[1] > bottom_limit:
                    self.heart_pos[1] = bottom_limit
            self.heart_rect.y = int(self.heart_pos[1])

    def _setup_failure_gravity_hall(self):
        """失败之作技能组2「重力走廊」：横向长条，心向右自由落体（镜头跟随=走廊向左滚动）；
        上下柱子留缝隙，玩家上下移动穿缝；柱子在右端滚入、左端滚出，形成无限循环。"""
        self.is_failure_gravity_hall = True
        # 该技能组回合延长 16 秒（共 24 秒）：前18秒下坠穿柱 → 18~21秒坠底 → 21~24秒幽灵斩
        self.enemy_turn_timer = self.ENEMY_TURN_DURATION + 16 * 60
        hall_w, hall_h = 700, 220
        hall_x = (SCREEN_WIDTH - hall_w) // 2
        hall_y = (SCREEN_HEIGHT - hall_h) // 2
        self.hall_rect = pygame.Rect(hall_x, hall_y, hall_w, hall_h)
        # 心固定在屏幕左侧锚点（镜头跟随心：视觉上心不动、走廊向后滚动），垂直居中
        self.hall_anchor_x = float(hall_x + 140)
        self.heart_pos[0] = self.hall_anchor_x
        self.heart_pos[1] = float(self.hall_rect.centery - self.heart_rect.height / 2.0)
        self.heart_rect.x = int(self.heart_pos[0])
        self.heart_rect.y = int(self.heart_pos[1])
        self.hall_heart_img = pygame.transform.rotate(self.heart_img, 90)  # 下方朝右
        # 向右自由落体（加速度 = 镜头/柱子滚动的速度）
        self.hall_gravity_active = False
        self.hall_gravity_timer = 60          # 片刻（约 1 秒）后开始下坠
        self.hall_vx = 0.0                    # 向右下坠速度
        self.hall_gravity = 0.22              # 向右重力加速度
        self.hall_max_vx = 8.0                # 下坠速度封顶
        self.hall_gap = 22                    # 柱子世界间距（像素，密不可分）
        self.hall_gap_h = 55                  # 柱子缝隙高度
        self.hall_gap_phase = 0.0             # 缝隙中心正弦漂移相位
        self.hall_gap_amp = 18                # 缝隙中心漂移幅度（px，视觉演出）
        self.hall_gap_step = 0.18             # 每根柱子相位步进（相邻变化极小）
        # 柱子（铺满长条，从右端滚入、左端滚出）
        self.hall_pillars = []
        self._spawn_hall_pillars()
        self.hall_slash_init = False          # 幽灵斩阶段是否已初始化
        self.hall_jump_vx = 0.0               # 阶段3跳跃水平速度（朝右视角=向左跳离地面）
        self.hall_on_ground = True            # 是否在地面（贴最右边），一段跳判定

    def _next_hall_gap_top(self):
        """生成下一根柱子的缝隙顶部 y：缝隙中心沿正弦缓慢漂移，相邻柱子变化极小（偏视觉演出）。"""
        hall = self.hall_rect
        gap_h = self.hall_gap_h
        low = hall.top + 15 + gap_h / 2.0
        high = hall.bottom - 15 - gap_h / 2.0
        center_mid = (low + high) / 2.0
        amp = min(self.hall_gap_amp, (high - low) / 2.0)
        center = center_mid + math.sin(self.hall_gap_phase) * amp
        self.hall_gap_phase += self.hall_gap_step
        return center - gap_h / 2.0

    def _spawn_hall_pillars(self):
        """在长条内铺满柱子的初始屏幕 x（间隔 hall_gap，缝隙正弦微漂）。"""
        hall = self.hall_rect
        gap_h = self.hall_gap_h
        self.hall_pillars = []
        x = self.hall_anchor_x + 100   # 从心的右侧开始铺，开场心左侧不落柱
        while x < hall.right:
            gap_top = self._next_hall_gap_top()
            self.hall_pillars.append({'x': float(x), 'gap_top': gap_top, 'gap_h': gap_h})
            x += self.hall_gap

    def update_failure_gravity_hall(self):
        """重力走廊三阶段：
        阶段1（前18秒）：心向右加速自由落体（镜头跟随=走廊左滚），上下移动穿柱缝；
        阶段2（18~21秒）：柱子停止刷新，心继续向右（重力方向不变）平安落在屏幕最右边；
        阶段3（21~24秒）：幽灵斩在屏幕最右边刷（红色预警闪烁2次后挥刀），心上下移动躲过。"""
        hall = self.hall_rect
        timer = self.enemy_turn_timer

        if timer > 360:
            # ===== 阶段1：下坠穿柱 =====
            if not self.hall_gravity_active:
                self.hall_gravity_timer -= 1
                if self.hall_gravity_timer <= 0:
                    self.hall_gravity_active = True

            if self.hall_gravity_active:
                self.hall_vx += self.hall_gravity
                if self.hall_vx > self.hall_max_vx:
                    self.hall_vx = self.hall_max_vx

            # 心屏幕 x 固定（镜头跟随）；y 由上下键移动，这里 clamp 到长条内
            self.heart_pos[0] = self.hall_anchor_x
            top_limit = hall.top + 5
            bottom_limit = hall.bottom - self.heart_rect.height - 5
            if self.heart_pos[1] < top_limit:
                self.heart_pos[1] = top_limit
            elif self.heart_pos[1] > bottom_limit:
                self.heart_pos[1] = bottom_limit
            self.heart_rect.x = int(self.heart_pos[0])
            self.heart_rect.y = int(self.heart_pos[1])

            # 走廊向左滚动（速度 = 下坠速度，越来越快）
            for p in self.hall_pillars:
                p['x'] -= self.hall_vx
            self.hall_pillars = [p for p in self.hall_pillars if p['x'] >= hall.left]
            rightmost = max((p['x'] for p in self.hall_pillars), default=hall.left)
            if rightmost < hall.right - self.hall_gap:
                gap_top = self._next_hall_gap_top()
                self.hall_pillars.append({'x': float(hall.right), 'gap_top': gap_top, 'gap_h': self.hall_gap_h})

            # 碰撞体积：柱子有实体，撞柱扣 2 血（每根只扣一次），并把心拱回正轨（缝隙内）
            pillar_w = 20
            shrink = 7
            hitbox = pygame.Rect(self.heart_rect.x + shrink, self.heart_rect.y + shrink,
                                 self.heart_rect.width - 2 * shrink, self.heart_rect.height - 2 * shrink)
            for p in self.hall_pillars:
                top_pillar = pygame.Rect(int(p['x']), hall.top, pillar_w, p['gap_top'] - hall.top)
                bot_pillar = pygame.Rect(int(p['x']), p['gap_top'] + p['gap_h'], pillar_w, hall.bottom - (p['gap_top'] + p['gap_h']))
                hit_top = top_pillar.colliderect(hitbox)
                hit_bot = bot_pillar.colliderect(hitbox)
                if hit_top or hit_bot:
                    if not p.get('hit', False):
                        p['hit'] = True
                        self._dual_shield_hit(self.heart_rect.topright)
                    if hit_top:
                        self.heart_pos[1] = float(p['gap_top'] - shrink)
                    elif hit_bot:
                        self.heart_pos[1] = float(p['gap_top'] + p['gap_h'] - self.heart_rect.height + shrink)
                    self.heart_rect.y = int(self.heart_pos[1])
                    hitbox.y = self.heart_rect.y + shrink

        elif timer > 180:
            # ===== 阶段2：柱子停刷，心继续向右自由落体（重力方向不变），平安落在屏幕最右边 =====
            if self.hall_gravity_active:
                self.hall_vx += self.hall_gravity
                if self.hall_vx > self.hall_max_vx:
                    self.hall_vx = self.hall_max_vx

            # 已有柱子继续滚完（不再刷入新柱）
            for p in self.hall_pillars:
                p['x'] -= self.hall_vx
            self.hall_pillars = [p for p in self.hall_pillars if p['x'] >= hall.left]

            # 心继续向右下坠到屏幕最右边（到达后停住），y 保持
            self.heart_pos[0] += self.hall_vx
            right_limit = hall.right - self.heart_rect.width - 5
            if self.heart_pos[0] > right_limit:
                self.heart_pos[0] = float(right_limit)
            self.heart_rect.x = int(self.heart_pos[0])
            self.heart_rect.y = int(self.heart_pos[1])

        else:
            # ===== 阶段3：幽灵斩（紧贴最右边的竖带），心保持朝右，上/左键一段跳向左躲 =====
            if not getattr(self, 'hall_slash_init', False):
                self.hall_slash_init = True
                # 生成红色竖斩（紧贴最右边，素材原色不染色）
                from entities.bullets import GroundSlash
                self.bullets.append(GroundSlash(hall))
                # 初始化跳跃：心贴最右边=地面，一段跳
                self.heart_pos[0] = float(hall.right - self.heart_rect.width - 5)
                self.hall_jump_vx = 0.0
                self.hall_on_ground = True

            right_limit = float(hall.right - self.heart_rect.width - 5)
            left_limit = float(hall.left + 5)

            if self.hall_on_ground:
                # 地面：心贴最右边，等玩家按上/左跳
                self.heart_pos[0] = right_limit
            else:
                # 空中：受向右重力拉回，向左跳出的心慢慢落回地面（一段跳，落地前不可再跳）
                self.hall_jump_vx += 0.6
                self.heart_pos[0] += self.hall_jump_vx
                if self.heart_pos[0] >= right_limit:
                    self.heart_pos[0] = right_limit
                    self.hall_jump_vx = 0.0
                    self.hall_on_ground = True
                elif self.heart_pos[0] < left_limit:
                    self.heart_pos[0] = left_limit

            self.heart_rect.x = int(self.heart_pos[0])
            self.heart_rect.y = int(self.heart_pos[1])

    def update_enemy_turn(self):
        self.enemy_turn_timer -= 1
        if self.enemy_turn_timer <= 0:
            # Check Escape Dust Punishment (Skill A for Abandoned Robot)
            if "escape_dust" in self.active_skills:
                uncollected_count = len([d for d in self.dusts if not d.is_collected])
                if uncollected_count > 0:
                    # Punishment: 5 DMG
                    dmg = self._enemy_damage(5)
                    self.player.take_damage(dmg)
                    self._spawn_damage_popup(dmg, (255, 0, 0), self.heart_rect.topright, timer=60)
                    self.shake_intensity = 10
                    # Check death immediately?
                    if self.player.hp <= 0:
                        if self.handle_player_death():
                            return

            # Reset Shield Mode immediately if active
            if hasattr(self, 'is_shield_mode') and self.is_shield_mode:
                self.is_shield_mode = False
                self.battle_box = self.original_battle_box
                self._recenter_heart()

            # Reset Dual Shield (失败之作·镜像双心)
            if getattr(self, 'is_dual_shield', False):
                self.is_dual_shield = False
                self.dual_bullets = []

            # Reset Gravity Hall (失败之作·重力走廊)
            if getattr(self, 'is_failure_gravity_hall', False):
                self.is_failure_gravity_hall = False
                self.hall_pillars = []

            # Reset Laser Grid (失败之作·5×5 激光列)
            if getattr(self, 'is_failure_laser_grid', False):
                self.is_failure_laser_grid = False

            # Reset Screen Inversion
            if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
                self.is_screen_inverted = False
            
            # Reset Battle Box for Skill C (if it was shrunk and not shield mode)
            if "black_ranger_c" in self.active_skills and hasattr(self, 'original_battle_box'):
                 self.battle_box = self.original_battle_box
                 self._recenter_heart()

            # 弹簧振子：回合结束恢复战斗框大小（菜单不再被压扁）
            if "spring_oscillator" in self.active_skills and hasattr(self, 'original_battle_box'):
                self.battle_box = self.original_battle_box
                self._recenter_heart()

            self.current_phase = self.PHASE_MENU
            self.bullets = []
            self.dusts = []
            self.debris_particles = []
            self.wind_force = [0, 0]
            self._apply_regen()
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

        if getattr(self, 'is_dual_shield', False):
            # 双心护盾（失败之作技能组1）：锁心不动；左护盾用上下键、右护盾用左右键（互不影响）
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.left_shield_dir = "UP"
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.left_shield_dir = "DOWN"
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.right_shield_dir = "LEFT"
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.right_shield_dir = "RIGHT"
            # 主红心锁为左心；右心由 update_failure_dual_shield 用独立坐标管理
            self.heart_pos[0] = self.dual_left_center[0] - self.heart_rect.width / 2.0
            self.heart_pos[1] = self.dual_left_center[1] - self.heart_rect.height / 2.0
            dx, dy = 0, 0
        elif getattr(self, 'is_failure_gravity_hall', False):
            # 重力走廊（失败之作技能组2）：阶段1上下键穿缝；阶段3跳跃由 handle_input 的 KEYDOWN 触发；阶段2只向右坠
            dx = 0
            dy = 0
            if self.enemy_turn_timer > 360:
                # 阶段1：上下键自由移动穿缝
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    dy = -self.heart_speed
                if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    dy = self.heart_speed
            # 阶段3：上/左键一段跳在 handle_input 的 KEYDOWN 处理，这里不持续移动
            # 阶段2：dx=dy=0，由 update_failure_gravity_hall 让心向右坠到最右边
        elif getattr(self, 'is_failure_laser_grid', False):
            # 5×5 激光列（失败之作二阶段技能组1）：扫射阶段自由连续移动；重力阶段由 update 锁键
            dx = 0
            dy = 0
            if not getattr(self, 'laser_gravity_phase', False):
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    dy = -self.heart_speed
                if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    dy = self.heart_speed
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    dx = -self.heart_speed
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    dx = self.heart_speed
        elif self.is_shield_mode:
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
                if not hasattr(self, 'jump_count'): self.jump_count = 0

                # 二段跳：起跳在 handle_input 的 KEYDOWN 中触发，这里只做重力下落
                self.heart_vy += self.gravity
                dy = self.heart_vy
            elif "conveyor_belt" in self.active_skills:
                # 轨道跑酷：上下切轨由 handle_input 的 KEYDOWN 处理；左右可慢速横移（半速）
                dx = 0
                dy = 0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -self.heart_speed * 0.5
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = self.heart_speed * 0.5
            elif "pendulum" in self.active_skills or "soviet_emblem" in self.active_skills:
                # 单摆（重力摆锤 / 苏联国徽下摆）：左右键施加力矩，重力回复
                dx = 0
                dy = 0
                k = self.pend_k
                torque = self.pend_torque
                # 二阶段重力域：周期性重力脉冲（期间重力骤增、玩家力矩被压制，摆锤被拽向底部）
                if self.phase == 2 and "soviet_emblem" in self.active_skills:
                    self.grav_pulse_timer += 1
                    self.grav_pulse_on = ((self.grav_pulse_timer % self.grav_pulse_interval) < self.grav_pulse_duration)
                    if self.grav_pulse_on:
                        k = self.pend_k * self.grav_pulse_k_mult
                        torque = self.pend_torque * self.grav_pulse_torque_mult
                self.pend_omega += -k * math.sin(self.pend_angle)
                if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.pend_omega -= torque
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.pend_omega += torque
                self.pend_omega *= self.pend_damping
                self.pend_angle += self.pend_omega
                if self.pend_angle > self.pend_max_angle:
                    self.pend_angle = self.pend_max_angle
                    self.pend_omega = 0.0
                elif self.pend_angle < -self.pend_max_angle:
                    self.pend_angle = -self.pend_max_angle
                    self.pend_omega = 0.0
            elif "spring_oscillator" in self.active_skills:
                # 弹簧振子：左右键施加外力，回复力 + 阻尼做简谐振动
                dx = 0
                dy = 0
                if not hasattr(self, 'spring_disp'):
                    self._setup_spring_oscillator()
                self.spring_vel += -self.spring_k * self.spring_disp
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    self.spring_vel -= self.spring_force
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    self.spring_vel += self.spring_force
                self.spring_vel *= self.spring_damping
                self.spring_vel = max(-8.0, min(8.0, self.spring_vel))
                self.spring_disp += self.spring_vel
                max_disp = self.battle_box.width / 2.0 - self.heart_rect.width / 2.0 - 5
                self.spring_disp = max(-max_disp, min(self.spring_disp, max_disp))
            elif "dancer_chase" in self.active_skills:
                # 田字格追逐：玩家沿虚线网格行走（节点处转向，边中间可掉头）
                dx = 0
                dy = 0
                ix = 0
                iy = 0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]: ix = -1
                elif keys[pygame.K_RIGHT] or keys[pygame.K_d]: ix = 1
                if keys[pygame.K_UP] or keys[pygame.K_w]: iy = -1
                elif keys[pygame.K_DOWN] or keys[pygame.K_s]: iy = 1
                if ix != 0 and iy != 0:
                    iy = 0  # 斜向输入只取水平，避免脱离虚线
                if self.dancer_ptarget is None and (ix != 0 or iy != 0):
                    r, c = self.dancer_pgrid
                    nr, nc = r + iy, c + ix
                    if 0 <= nr < 3 and 0 <= nc < 3:
                        self.dancer_ptarget = (nr, nc)
                elif self.dancer_ptarget is not None and (ix != 0 or iy != 0):
                    r, c = self.dancer_pgrid
                    tr, tc = self.dancer_ptarget
                    move = (tr - r, tc - c)
                    if (iy, ix) == (-move[0], -move[1]):
                        # 掉头
                        self.dancer_pgrid, self.dancer_ptarget = self.dancer_ptarget, self.dancer_pgrid
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

        # UFO 牵引：红心落在重力列内时被持续向上吸（往下按可对抗）
        if "ufo_tractor" in self.active_skills:
            if not hasattr(self, 'ufo_gravity_col'):
                self.ufo_gravity_col = random.randint(0, 2)
            if not hasattr(self, 'ufo_gravity_time'):
                self.ufo_gravity_time = 0
            col_w = self.battle_box.width // 3
            g_left = self.battle_box.left + self.ufo_gravity_col * col_w
            g_right = g_left + col_w
            if g_left <= self.heart_rect.centerx <= g_right:
                self.heart_pos[1] -= 0.6
                self.ufo_gravity_time += 1
                if self.heart_rect.top <= self.battle_box.top + 5:
                    # 被吸到顶层贴边：无 3s 宽限，立即开始，每 1s（60 帧）掉 1 血
                    should_damage = (self.ufo_gravity_time % 60 == 0)
                else:
                    # 逗留超过 3s 后，每 1.5s（90 帧）掉 1 血
                    should_damage = (self.ufo_gravity_time > 180 and (self.ufo_gravity_time - 180) % 90 == 0)
                if should_damage:
                    dmg = self._enemy_damage(1)
                    self.player.hp -= dmg
                    if self.player.hp < 0: self.player.hp = 0
                    self.shake_intensity = 10
                    self.damage_flash_timer = 6
                    self._spawn_damage_popup(dmg, (200, 120, 255), self.heart_rect.topright, timer=60)
                    if self.player.hp <= 0:
                        self.handle_player_death()
            else:
                self.ufo_gravity_time = 0

        # 重力走廊（失败之作技能组2）用独立横向长条边界，跳过通用战场 clamp
        if not getattr(self, 'is_failure_gravity_hall', False):
            self.heart_pos[0] = max(self.battle_box.left + 5, min(self.heart_pos[0], self.battle_box.right - self.heart_rect.width - 5))

            bottom_limit = self.battle_box.bottom - self.heart_rect.height - 5
            self.heart_pos[1] = max(self.battle_box.top + 5, min(self.heart_pos[1], bottom_limit))

        if "samurai_gravity_jump" in self.active_skills:
             if self.heart_pos[1] >= bottom_limit - 1:
                 self.on_ground = True
                 self.heart_vy = 0
                 self.jump_count = 0
             elif self.heart_pos[1] <= self.battle_box.top + 5:
                 self.heart_vy = 0

        # 轨道跑酷（废料传送带）：红心极快平滑平移到目标轨道（上下切轨由 handle_input 更新），x 保留慢速横移
        if "conveyor_belt" in self.active_skills:
            if not hasattr(self, 'conveyor_rail_index'):
                self.conveyor_rail_index = 1
            if not hasattr(self, 'conveyor_rail_ys'):
                lane_h = self.battle_box.height // 3
                self.conveyor_rail_ys = [self.battle_box.top + lane_h * (i + 0.5) for i in range(3)]
            self.conveyor_rail_index = max(0, min(2, self.conveyor_rail_index))
            target_y = self.conveyor_rail_ys[self.conveyor_rail_index] - self.heart_rect.height / 2.0
            diff = target_y - self.heart_pos[1]
            if abs(diff) < 1.5:
                self.heart_pos[1] = target_y
            else:
                self.heart_pos[1] += diff * 0.6

        # 单摆（重力摆锤 / 苏联国徽下摆）：红心定位到摆锤当前位置（圆形轨道）
        if "pendulum" in self.active_skills or "soviet_emblem" in self.active_skills:
            if not hasattr(self, 'pend_pivot'):
                self.pend_pivot = (self.battle_box.centerx, self.battle_box.top)
            if not hasattr(self, 'pend_len'):
                self.pend_len = 150
            if not hasattr(self, 'pend_angle'):
                self.pend_angle = 0.0
            bx = self.pend_pivot[0] + self.pend_len * math.sin(self.pend_angle)
            by = self.pend_pivot[1] + self.pend_len * math.cos(self.pend_angle)
            self.heart_pos[0] = bx - self.heart_rect.width / 2.0
            self.heart_pos[1] = by - self.heart_rect.height / 2.0

        # 弹簧振子：红心锁定横置窄条中线，水平方向由简谐振动决定
        if "spring_oscillator" in self.active_skills:
            if not hasattr(self, 'spring_disp'):
                self._setup_spring_oscillator()
            self.spring_center_x = self.battle_box.centerx
            self.heart_pos[0] = self.spring_center_x + self.spring_disp - self.heart_rect.width / 2.0
            self.heart_pos[1] = self.spring_y - self.heart_rect.height / 2.0

        # 双生舞怜·田字格追逐：玩家沿虚线网格平滑移动
        if "dancer_chase" in self.active_skills:
            cols = self.dancer_grid_cols
            rows = self.dancer_grid_rows
            pcx = self.heart_pos[0] + self.heart_rect.width / 2.0
            pcy = self.heart_pos[1] + self.heart_rect.height / 2.0
            # 燃烧边倒计时，到期熄灭（恢复普通虚线）
            for key in list(self.dancer_burned_edges):
                self.dancer_burned_edges[key] -= 1
                if self.dancer_burned_edges[key] <= 0:
                    del self.dancer_burned_edges[key]
            # 二阶段：玩家完整经过一条燃烧红线时，一次性扣 2 血——在抵达目标节点时结算（见下方到达判定）
            if self.dancer_ptarget is not None:
                tr, tc = self.dancer_ptarget
                tx = cols[tc]
                ty = rows[tr]
                ddx = tx - pcx
                ddy = ty - pcy
                dist = math.hypot(ddx, ddy)
                if dist <= self.heart_speed:
                    pcx = float(tx)
                    pcy = float(ty)
                    # 完整经过一条边：若刚走过的边是燃烧红线，一次性扣 2 血
                    old_grid = self.dancer_pgrid
                    new_grid = self.dancer_ptarget
                    if tuple(sorted([old_grid, new_grid])) in self.dancer_burned_edges:
                        dmg = self._enemy_damage(2)
                        self.player.hp -= dmg
                        if self.player.hp < 0:
                            self.player.hp = 0
                        self.shake_intensity = 8
                        self.damage_flash_timer = 5
                        self._spawn_damage_popup(dmg, (255, 60, 60), self.heart_rect.topright, timer=50)
                        if self.player.hp <= 0:
                            self.handle_player_death()
                    self.dancer_pgrid = self.dancer_ptarget
                    self.dancer_ptarget = None
                else:
                    pcx += ddx / dist * self.heart_speed
                    pcy += ddy / dist * self.heart_speed
            self.heart_pos[0] = pcx - self.heart_rect.width / 2.0
            self.heart_pos[1] = pcy - self.heart_rect.height / 2.0

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
        if getattr(self, 'is_dual_shield', False):
            self.update_failure_dual_shield()
        if getattr(self, 'is_failure_gravity_hall', False):
            self.update_failure_gravity_hall()
        if getattr(self, 'is_failure_laser_grid', False):
            self.update_failure_laser_grid()
        
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
            
            if b.type == "laser_trail":
                 # 点到线段距离（二阶段技能1的发光红激光轨迹）
                 if b.hit_test(self.heart_rect.centerx, self.heart_rect.centery, p_radius):
                     is_hit = True
            elif b.type == "laser" or b.type == "plasma_blade" or b.type == "laser_network" or b.type == "ufo_laser" or b.type == "conveyor_scrap" or b.type == "vertical_scrap" or b.type == "ghost_slash" or b.type == "ground_slash":
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
                    self.player.hp -= self._enemy_damage(getattr(b, 'damage', 1))
                    if self.player.hp < 0: self.player.hp = 0 # Clamp HP
                    
                    self.shake_intensity = 10
                    self.damage_flash_timer = 6
                    if b.type != "laser" and b.type != "ufo_laser" and b.type != "dancer_head" and b.type != "dancer_chaser" and b.type != "dancer_rail" and b.type != "ghost_slash" and b.type != "ground_slash":
                        self.bullets.remove(b)
                    if b.type == "dancer_head":
                        b.damaging = False  # 单次冲刺只结算一次伤害
                    elif b.type == "dancer_chaser":
                        b.on_hit()  # 追击命中后进入短暂冷却
                    elif b.type == "dancer_rail":
                        b.damaging = False  # 单次冲刺只结算一次伤害
                    
                    if self.player.hp <= 0:
                        self.handle_player_death()

        # 二阶段技能组1：舞者黄金分割切割完成后，适度提前结束回合（留缓冲，不立刻结束）
        if self.phase == 2 and "dancer_dash" in self.active_skills:
            if not any(getattr(b, 'type', '') == "dancer_head" for b in self.bullets):
                self.enemy_turn_timer = min(self.enemy_turn_timer, self.DANCER_DASH_FINISH_BUFFER)

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
            return True
        # 紧急保险丝：被动锁血一次，濒死时熔断保住 1 点生命并消耗道具
        if self.player is not None and any(
            isinstance(it, dict) and it.get("name") == "紧急保险丝"
            for it in getattr(self.player, "inventory", [])
        ):
            self.player.remove_item("紧急保险丝", 1)
            self.player.hp = 1
            self.shake_intensity = 14
            self.damage_flash_timer = 8
            self.dialog_text = "* 紧急保险丝熔断了！你勉强撑住了一口气。"
            return False
        self.death_triggered = True

        self.player.hp = 0
        pygame.mixer.music.stop()
        self.battle_result = "lost"
        self.running = False
        return True



