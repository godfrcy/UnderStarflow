import pygame
import sys
import os
import json
import math
import random

from engine.utils import resource_path, get_font
import engine.config as config
from engine.config import *
from engine.audio import load_bgm
from engine.game_state import GameState
from engine.battle_system import BattleManager
from engine.camera import Camera
from engine.tile_manager import TileManager
from engine.map_data import MAP_CONFIG
from engine.map_builder import spawn_map_content
from engine.enemy_data import BATTLE_DATA, ABANDONED_ROBOT_DATA
from engine.save_system import save_game, load_game
from entities.player import Player
from entities.enemies import OverworldEnemy, Bonfire, FailureEnemy
from entities.props import Prop
from ui.menus import TitleScreen, ConfirmDialog, BonfireMenu, TeleportMenu, PauseMenu, VolumeMenu, BackpackMenu, StatsMenu
from ui.dialogue import DialogueSystem
from ui.effects import SnowFlake, AreaTitle, DataDust, FogGate, FogWall, ExitGlow
from ui.atmosphere import PipeAtmosphere, PulseAtmosphere, FogMaze

# --- Main Game Loop ---


class Game:
    def __init__(self):
        # 1. Initialize Pygame
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Under Starflow")
        try:
            icon = pygame.image.load(resource_path("ui/backgrounds/mechanical_heart.jpeg"))
            pygame.display.set_icon(icon)
        except Exception as e:
            print(f"Warning: Failed to load icon: {e}")
        self.clock = pygame.time.Clock()

        # 2. Initialize Subsystems
        self.game_state = GameState()
        self.battle_manager = BattleManager(self.screen)
        self.battle_manager.game_state = self.game_state

        # Camera & Map
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT) # Map size will be updated later if needed

        # Entities Groups
        self.enemies_group = pygame.sprite.Group()
        self.bonfire_group = pygame.sprite.Group()
        # interactables_group removed, managed by TileManager

        # ParticlesState Variables
        self.current_map_id = "start"
        self.tile_manager = None

        # Particles
        self.particles = []
        self.fog_gates = [] # List of FogGates
        self.fog_wall = None
        self.fog_walls = [] # Fog walls list (multiple walls, pipe nightmare)
        self.exit_glows = [] # 出口「数据缝」微光列表

        self.props_group = pygame.sprite.Group() # New Prop Group

        # Fog Animation State
        self.fog_anim_active = False
        self.fog_anim_timer = 0
        self.fog_anim_direction = (2, 0)
        self.FOG_ANIM_DURATION = 90 # 1.5s * 60FPS

        # UI Instances
        self.title_screen = TitleScreen(self.screen)
        self.confirm_dialog = ConfirmDialog(self.screen)
        self.bonfire_menu = BonfireMenu(self.screen)
        self.pause_menu = PauseMenu(self.screen)
        self.volume_menu = VolumeMenu(self.screen)
        self.backpack_menu = BackpackMenu(self.screen)
        self.stats_menu = StatsMenu(self.screen)
        self.area_title = AreaTitle(self.screen, "无主雪地")
        self.dialogue_system = DialogueSystem()

        # Player
        self.player = Player(128 * 2, 128 * 5)

        # Initial Load
        self.load_map(self.current_map_id, silent=True)
        self.update_all_volumes() # Apply initial volume settings to loaded items

        # 4. State Machine
        self.STATE_TITLE = 0
        self.STATE_OVERWORLD = 1
        self.STATE_BATTLE = 2
        self.STATE_GAMEOVER = 3

        self.current_state = self.STATE_TITLE
        self.gameover_timer = 0

        # BGM State
        self.current_bgm = None

        # Bonfire Trigger Logic
        self.ignore_bonfire_collision = False

        self.pipe_atmosphere = PipeAtmosphere()
        self.pulse_atmosphere = PulseAtmosphere()
        self.fog_maze = FogMaze()

        # import random # Ensure random is available if not already (Removed to fix NameError)

        self.save_success_timer = 0

        # 拾取提示（屏幕最下方，1.5s 后消失）
        self.pickup_notice_text = None
        self.pickup_notice_timer = 0
        self.PICKUP_NOTICE_DURATION = 90  # 1.5s * 60FPS

        # Freeze Effect State (Pipe Nightmare 3-2)
        self.freeze_timer = 0
        self.is_frozen = False
        self.static_frame = None
        self.FREEZE_CYCLE = 2.0 # 2 seconds total
        self.FREEZE_START = 1.5 # 1.5s normal, then 0.5s frozen

        # Load Glitch Sound
        self.glitch_sound = None
        try:
            # User requested temporary replacement with calibration sound
            glitch_path = resource_path("audio/sfx/glitch.mp3")
            if not os.path.exists(glitch_path):
                 root_dir = os.path.dirname(os.path.abspath(__file__))
                 glitch_path = os.path.join(root_dir, "assetsDB", "audio", "sfx", "故障音.mp3")

            if os.path.exists(glitch_path):
                self.glitch_sound = pygame.mixer.Sound(glitch_path)
                self.glitch_sound.set_volume(config.SFX_VOLUME)
            else:
                 print(f"Warning: Glitch sound not found at {glitch_path}")
        except Exception as e:
            print(f"Warning: Failed to load glitch sound: {e}")

        self.running = True

    def load_map(self, map_id, silent=False):
        
        # Reset Player Noise Level on Map Transition
        if hasattr(self.player, 'noise_level'):
            self.player.noise_level = 0
            
        # Reset Fog Anim
        self.fog_anim_active = False
        
        # 1. Find Folder
        config = MAP_CONFIG.get(map_id)
        if not config:
            print(f"Error: Map ID {map_id} not found.")
            return
            
        folder_name = config["folder"]
        
        # Dynamic search for folder
        target_name = folder_name
        found_path = None
        root_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Check assetsDB first (User convention)
        assets_db_path = os.path.join(root_dir, "assetsDB")
        if os.path.exists(assets_db_path):
             path = os.path.join(assets_db_path, target_name)
             if os.path.exists(path):
                 found_path = path
        
        # Fallback to root or resource_path
        if not found_path:
            for item in os.listdir(root_dir):
                if item == target_name:
                    found_path = os.path.join(root_dir, item)
                    break
        
        if not found_path:
             found_path = resource_path(target_name)
        
        print(f"Loading map {map_id} from {found_path}")
        extra_obstacles = config.get("extra_obstacles", None)
        open_top_rows = config.get("open_top_rows", False)
        is_pipe_channel = config.get("is_pipe_channel", False)
        is_vertical_pipe_channel = config.get("is_vertical_pipe_channel", False)
        rotation = config.get("rotation", 0)
        self.tile_manager = TileManager(found_path, extra_obstacles=extra_obstacles, open_top_rows=open_top_rows, is_pipe_channel=is_pipe_channel, is_vertical_pipe_channel=is_vertical_pipe_channel, rotation=rotation)
        
        # 2. Clear & Populate Entities
        self.enemies_group.empty()
        self.bonfire_group.empty()
        self.props_group.empty()
        # tile_manager.collectibles is new, so it starts empty for new map instance
        
        # Reset Particles
        self.particles.clear()
        
        # 生成雾门/雾墙 + 敌人/道具/收集物（抽到 engine/map_builder.py）
        self.fog_gates, self.fog_wall, self.fog_walls = spawn_map_content(
            map_id, config, extra_obstacles, self.game_state, self.tile_manager,
            self.enemies_group, self.bonfire_group, self.props_group, self.particles,
            self.fog_wall, self.fog_walls
        )
        # 3. Update Camera Limit
        self.camera.set_map_size(self.tile_manager.width, self.tile_manager.height)

        # 出口「数据缝」微光（引导单向地图/岔路/锁门的出口方向）
        # glow_edges 每项可为字符串简写（"right"）或字典（{"edge","start","end","locked"}）
        self.exit_glows = []
        has_core = any(item.get("id") == "liquid_nitrogen_core" for item in self.player.inventory if isinstance(item, dict))
        for spec in config.get("glow_edges", []):
            if isinstance(spec, str):
                edge, start, end, locked, boss = spec, None, None, False, None
            else:
                edge = spec["edge"]
                start = spec.get("start")
                end = spec.get("end")
                locked = spec.get("locked", False)
                boss = spec.get("boss")  # 指定 boss_id：仅当该 boss 被击败后才显示此出口光
            if boss and boss not in self.game_state.cleared_bosses:
                continue  # 未击败对应 boss，暂不显示该出口光
            if locked and has_core:
                locked = False  # 已持核心 → 锁门直接亮蓝光
            if edge in ("left", "right"):
                s = start if start is not None else 256
                e = end if end is not None else SCREEN_HEIGHT
            else:
                s = start if start is not None else 0
                e = end if end is not None else SCREEN_WIDTH
            self.exit_glows.append(ExitGlow(edge, s, e, locked=locked))
        
        # Ensure volume settings are applied to new entities and existing systems
        # This fixes the issue where Map Broadcast and other SFX might not track volume changes correctly
        # or new entities (like items) default to full volume.
        try:
            self.update_all_volumes()
        except NameError:
            pass
        
        # Area Title
        if config.get("show_title", True):
            if not silent:
                self.area_title.set_text(config.get("name", "Unknown"))
                self.area_title.show()
        else:
            self.area_title.hide()
            
        return self.tile_manager


    def update_all_volumes(self):
        sfx_vol = config.SFX_VOLUME
        
        # Battle Manager
        if self.battle_manager.calibration_sfx:
            self.battle_manager.calibration_sfx.set_volume(sfx_vol)
            
        # Area Title
        if self.area_title.sound:
            self.area_title.sound.set_volume(sfx_vol)
            
        # Collectibles
        if self.tile_manager:
            for item in self.tile_manager.collectibles:
                if item.sound:
                    item.sound.set_volume(sfx_vol)
                

    def run_transition(self, next_map_id, start_pos_type, hold_duration=0):
        
        # Record Entry Type for Logic (e.g. Pipe Nightmare 2_1 routing)
        self.game_state.last_entry_type = start_pos_type
        
        # Fade Out (Faster: step 25, delay 15ms -> ~150ms)
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade.fill((0, 0, 0))
        for alpha in range(0, 256, 25):
            # Draw current state one last time? 
            # Ideally we just draw black over it
            fade.set_alpha(alpha)
            self.screen.blit(fade, (0, 0))
            pygame.display.update()
            pygame.time.delay(15)
        
        # Hold Black Screen
        if hold_duration > 0:
            pygame.time.delay(int(hold_duration * 1000))
            
        # Load New Map
        self.current_map_id = next_map_id
        self.load_map(self.current_map_id)
        
        # Set Player Position
        if start_pos_type == "left":
            self.player.rect.x = 20
        elif start_pos_type == "right":
            self.player.rect.x = SCREEN_WIDTH - self.player.rect.width - 20
            # Fix: Force safe Y position when entering Base 5 from right (Pipe Nightmare 1)
            # Row 4 (y=512) is safe. Obstacles are at Rows 2,3 (Indices).
            if next_map_id == "base_5":
                self.player.rect.y = 128 * 4 # Row 5 (Index 4) - Safe Channel
            # Fix: Force safe Y position when entering Pipe Nightmare 2-2 from right (Pipe Nightmare 2-3)
            # Rows 0,1 are blocked. Clamp to Row 2 (y=256) minimum.
            elif next_map_id == "pipe_nightmare_2_2":
                if self.player.rect.y < 128 * 2:
                    self.player.rect.y = 128 * 2
        elif start_pos_type == "top":
            self.player.rect.y = 20
        elif start_pos_type == "exact_top":
            self.player.rect.y = 0
        elif start_pos_type == "bottom":
            self.player.rect.y = SCREEN_HEIGHT - self.player.rect.height - 20
        elif start_pos_type == "center_left":
             # Specific for Base entry if needed, but 'left' is fine usually
             self.player.rect.x = 50
            
        # Fade In (Faster)
        for alpha in range(255, -1, -25):
            self.screen.fill(COLOR_BG)
            # Draw Map
            if self.tile_manager:
                self.tile_manager.draw(self.screen, self.camera)
            
            # Draw Entities
            # Collectibles are drawn by tile_manager
            for s in self.bonfire_group: self.screen.blit(s.image, self.camera.apply(s))
            for s in self.enemies_group: self.screen.blit(s.image, self.camera.apply(s))
            self.screen.blit(self.player.image, self.camera.apply(self.player))
            
            fade.set_alpha(alpha)
            self.screen.blit(fade, (0, 0))
            pygame.display.update()
            pygame.time.delay(15)


    def show_pickup_notice(self, names):
        """显示拾取提示（屏幕最下方，1.5s 后消失）。"""
        if not names:
            return
        self.pickup_notice_text = f"* 获得了 {'、'.join(names)}"
        self.pickup_notice_timer = self.PICKUP_NOTICE_DURATION

    def grant_test_item(self):
        """开局发放测试道具「测试」：战斗中造成1000伤害，用于秒杀boss验证路线。"""
        if not any(isinstance(i, dict) and i.get("name") == "测试" for i in self.player.inventory):
            self.player.inventory.append({
                "name": "测试",
                "type": "consumable",
                "description": "测试道具，使用后造成1000点伤害。",
            })

    def run(self):
        while self.running:
            if self.save_success_timer > 0:
                self.save_success_timer -= 1

            if self.pickup_notice_timer > 0:
                self.pickup_notice_timer -= 1
                if self.pickup_notice_timer == 0:
                    self.pickup_notice_text = None

            # --- State: Title Screen ---
            if self.current_state == self.STATE_TITLE:
                if self.current_bgm != "audio/bgm/the tree.mp3":
                    load_bgm("audio/bgm/the tree.mp3")
                    self.current_bgm = "audio/bgm/the tree.mp3"

                action = self.title_screen.run()
                if action == "new_game":
                    # Reset Game State
                    self.game_state.activated_bonfires = ["start"]
                    self.game_state.collected_items = []
                    self.game_state.cleared_bosses = []
                    self.game_state.temp_killed_enemies = []
                    self.game_state.failure_emp_used = False
                    self.game_state.last_rest_map_id = "start"
                    self.game_state.last_rest_pos = (128 * 3, 128 * 5)

                    # Reset Player State
                    self.player.hp = 20
                    self.player.max_hp = 20
                    self.player.inventory = []
                    self.player.exp = 0
                    self.player.battery_count = 3
                    self.grant_test_item()

                    self.current_state = self.STATE_OVERWORLD
                    self.current_map_id = "start"
                    self.load_map(self.current_map_id)
                    self.player.rect.topleft = (128 * 2, 128 * 5)
                    self.area_title.show()
                    self.dialogue_system.start_dialogue(["...真冷啊"])
                elif action == "continue":
                    success, saved_map_id = load_game(self.player, self.game_state)
                    if success:
                        self.grant_test_item()
                        self.current_map_id = saved_map_id
                        self.load_map(self.current_map_id)
                        self.current_state = self.STATE_OVERWORLD
                        self.area_title.show()
                        self.ignore_bonfire_collision = True # Fix: Prevent immediate bonfire menu trigger
                    else:
                        print("Load failed, starting new game.")
                        self.current_state = self.STATE_OVERWORLD
                        self.current_map_id = "start"
                        self.load_map(self.current_map_id)
                        self.area_title.show()
                elif action == "quit":
                    self.running = False

            # --- State: Overworld ---
            elif self.current_state == self.STATE_OVERWORLD:
                # Play Overworld BGM (Dynamic based on Map Config)
                target_bgm = MAP_CONFIG[self.current_map_id].get("bgm")
                target_bgm_start = MAP_CONFIG[self.current_map_id].get("bgm_start", 0.0)

                if target_bgm and self.current_bgm != target_bgm:
                    load_bgm(target_bgm, start_pos=target_bgm_start)
                    self.current_bgm = target_bgm

                if self.fog_anim_active:
                    # --- Fog Animation State ---
                    # Consume events to prevent freezing, but ignore input
                    pygame.event.pump()

                    self.fog_anim_timer += 1
                    # Move player based on direction
                    self.player.rect.x += self.fog_anim_direction[0]
                    self.player.rect.y += self.fog_anim_direction[1]

                    # Visual Updates
                    for fg in self.fog_gates: fg.update()
                    if self.fog_wall: self.fog_wall.update()
                    for fw in self.fog_walls: fw.update()

                    self.camera.update(self.player)
                    for p in self.particles: p.update()
                    if self.tile_manager: self.tile_manager.update_collectibles()

                    if self.fog_anim_timer >= self.FOG_ANIM_DURATION:
                        self.fog_anim_active = False

                else:
                    # --- Normal Gameplay State ---
                    # Event Handling
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.running = False

                        # Dialogue Input Handling
                        if self.dialogue_system.active:
                            self.dialogue_system.handle_event(event)

                        elif event.type == pygame.MOUSEBUTTONDOWN:
                             if hasattr(self.player, 'noise_level'):
                                 self.player.noise_level += 15

                        elif event.type == pygame.KEYDOWN:
                            if hasattr(self.player, 'noise_level'):
                                # Only add noise for non-movement keys? 
                                # Or just add it as requested. 
                                # User said "Point press avoids chase", so we shouldn't punish single taps too hard.
                                # But current logic is +15.
                                # If I remove this +15, then tapping W is just "short hold".
                                # If I keep it, tapping W is +15 noise.
                                # The user said "Tap avoids chase". 15 is < 100. So it works.
                                # I will keep it but maybe ensure movement keys don't trigger it? 
                                # No, user said "KEYDOWN... noise_level += 15". I should follow orders.
                                # But wait, the user's LATEST feedback said: "Tap can avoid being chased".
                                # My logic: Tap = +15 (Event) + Small Amount (Hold). Total ~20.
                                # Long Press = +15 (Event) + Large Amount (Hold). Total > 100.
                                # This seems correct.
                                # The "Immediate Chase" was the main bug, fixed by reset.
                                self.player.noise_level += 15

                            if event.key == pygame.K_ESCAPE:
                                bg_surf = self.screen.copy()
                                # New Pause Menu Logic
                                action = self.pause_menu.run(bg_surf)

                                # Adjusted handling for new order: Title, Stats, Volume, Backpack
                                if action == "title":
                                    self.confirm_dialog.set_text("确认返回标题界面？")
                                    if self.confirm_dialog.run(bg_surf):
                                        self.current_state = self.STATE_TITLE
                                        self.title_screen.running = True
                                        self.current_bgm = None
                                elif action == "stats":
                                    self.stats_menu.run(self.player, bg_surf)
                                elif action == "volume":
                                    self.volume_menu.run(bg_surf, self.update_all_volumes)
                                elif action == "backpack":
                                    self.dialogue_system.active = False
                                    self.backpack_menu.run(self.player, self.screen.copy(), self.dialogue_system)

                            elif event.key == pygame.K_F5:
                                save_game(self.player, self.game_state, self.current_map_id)
                            elif event.key == pygame.K_SPACE:
                                # Manual Item Interaction
                                if self.tile_manager:
                                    collected = self.tile_manager.try_collect(self.player, self.game_state)
                                    if collected:
                                        self.show_pickup_notice(collected)

                                # Console Interaction (Pipe Nightmare 3-3)
                                if self.current_map_id == "pipe_nightmare_3_3":
                                    console = None
                                    for p in self.props_group:
                                        if getattr(p, 'is_console', False):
                                            console = p
                                            break

                                    if console:
                                        dist_x = abs(self.player.rect.centerx - console.rect.centerx)
                                        dist_y = abs(self.player.rect.centery - console.rect.centery)
                                        if dist_x < 100 and dist_y < 100:
                                            has_core = any(item.get("id") == "liquid_nitrogen_core" for item in self.player.inventory if isinstance(item, dict))

                                            if not has_core:
                                                self.player.inventory.append({
                                                    "id": "liquid_nitrogen_core", 
                                                    "name": "液氮冷却核心", 
                                                    "type": "key_item", 
                                                    "description": "极低温的冷却核心，可以冻结周围的空气。"
                                                })
                                                self.dialogue_system.start_dialogue([
                                                    "获得了 [液氮冷却核心]。",
                                                    "极低温的冷却核心，可以冻结周围的空气。",
                                                    "也许可以用它通过某些高温区域。"
                                                ])
                                            else:
                                                self.dialogue_system.start_dialogue([
                                                    "操作台已经停止工作了。",
                                                    "核心已被取出。"
                                                ])

                                # Monitor Interaction (Pipe Nightmare 2-3)
                                if self.current_map_id == "pipe_nightmare_2_3":
                                    # Find monitor
                                    monitor = None
                                    for p in self.props_group:
                                        monitor = p # Assuming only one prop or first one
                                        break

                                    if monitor:
                                        # Check distance
                                        dist_x = abs(self.player.rect.centerx - monitor.rect.centerx)
                                        dist_y = abs(self.player.rect.centery - monitor.rect.centery)
                                        if dist_x < 128 and dist_y < 128: # Interaction Range (1 tile)
                                            self.dialogue_system.start_dialogue([
                                                "冷却系统已停止响应。",
                                                "核心热域温度无法测量。"
                                            ])

                    # Map Transitions
                    if self.player.rect.right >= SCREEN_WIDTH - 10:
                        next_map = MAP_CONFIG[self.current_map_id]["next"]
                        if next_map:
                            self.run_transition(next_map, "left")

                    elif self.player.rect.left <= 10:
                        prev_map = MAP_CONFIG[self.current_map_id]["prev"]
                        can_exit = True

                        # pipe_nightmare_1_3 Constraint: Only Row 2, 3 allowed (Indices)
                        if self.current_map_id == "pipe_nightmare_1_3":
                            # Rows 2 and 3 correspond to y range [256, 512]
                            cy = self.player.rect.centery
                            if not (2 * 128 <= cy <= 4 * 128):
                                can_exit = False
                                self.player.rect.left = 10 # Block return

                        # Backpack Check: 2-3 -> 2-2
                        if self.current_map_id == "pipe_nightmare_2_3" and prev_map == "pipe_nightmare_2_2":
                            if not any(item.get("id") == "liquid_nitrogen_core" for item in self.player.inventory if isinstance(item, dict)):
                                can_exit = False
                                self.player.rect.left = 20 # Push back
                                self.dialogue_system.start_dialogue(["检测到高温区域阻断。", "需要【液氮冷却核心】才能通过。"])

                        # 2-2 -> 上升管道(通往地表)：需先击败鬼武士，左出口才解锁
                        if self.current_map_id == "pipe_nightmare_2_2" and prev_map == "pipe_ascent_1":
                            if "pipe_2_2_boss" not in self.game_state.cleared_bosses:
                                can_exit = False
                                self.player.rect.left = 20 # Push back
                                self.dialogue_system.start_dialogue(["这条路的出口被武士的怨念封锁了。", "需要先击败鬼武士。"])

                        if prev_map and can_exit:
                            self.run_transition(prev_map, "right")

                    elif self.player.rect.bottom >= SCREEN_HEIGHT - 10:
                        down_map = MAP_CONFIG[self.current_map_id].get("down")
                        can_exit = True

                        # pipe_nightmare_1_3 Constraint: Only Col 2, 3 allowed (Indices)
                        if self.current_map_id == "pipe_nightmare_1_3":
                             # Cols 2 and 3 correspond to x range [256, 512]
                             cx = self.player.rect.centerx
                             if not (2 * 128 <= cx <= 4 * 128):
                                 can_exit = False
                                 self.player.rect.bottom = SCREEN_HEIGHT - 10 # Block exit

                        if down_map and can_exit:
                            self.run_transition(down_map, "top")
                    elif self.player.rect.top <= 10:
                        up_map = MAP_CONFIG[self.current_map_id].get("up")

                        # Backpack Check: 3-2 -> 2-2
                        if self.current_map_id == "pipe_nightmare_3_2" and up_map == "pipe_nightmare_2_2":
                             if not any(item.get("id") == "liquid_nitrogen_core" for item in self.player.inventory if isinstance(item, dict)):
                                 up_map = None # Block transition
                                 self.player.rect.top = 20 # Push back
                                 self.dialogue_system.start_dialogue(["检测到高温区域阻断。", "需要【液氮冷却核心】才能通过。"])

                        if up_map:
                            self.run_transition(up_map, "bottom")

                    # Pipe Channel Constraint
                    if MAP_CONFIG[self.current_map_id].get("is_pipe_channel"):
                        # Force player Y between 2*TILE_SIZE and 4*TILE_SIZE
                        min_y = 2 * 128
                        max_y = 4 * 128 - self.player.rect.height

                        if self.player.rect.y < min_y:
                            self.player.rect.y = min_y
                        elif self.player.rect.y > max_y:
                            self.player.rect.y = max_y
                    elif MAP_CONFIG[self.current_map_id].get("is_vertical_pipe_channel"):
                        # Force player X between 2*TILE_SIZE and 4*TILE_SIZE
                        min_x = 2 * 128
                        max_x = 4 * 128 - self.player.rect.width

                        if self.player.rect.x < min_x:
                            self.player.rect.x = min_x
                        elif self.player.rect.x > max_x:
                            self.player.rect.x = max_x

                    # Special Transition for snow_1_3 -> base_1 (The Great Hollow)
                    if self.current_map_id == "snow_1_3":
                        # Area: Row 2-4 (index 1-3), Col 3+ (index 2+)
                        # 128-based: x >= 2*128 (256), 128 <= y <= 4*128 (512)
                        # Let's define the rect for clarity
                        # x: 256 to end, y: 0 to SCREEN_HEIGHT (Full column)
                        hollow_rect = pygame.Rect(256, 0, SCREEN_WIDTH - 256, SCREEN_HEIGHT)
                        if self.player.rect.colliderect(hollow_rect):
                            self.confirm_dialog.set_text("确认进入大空洞？")
                            bg_surf = self.screen.copy()
                            if self.confirm_dialog.run(bg_surf):
                                 self.run_transition("base_1", "center_left", hold_duration=1.5)
                            else:
                                # Push player left to avoid immediate re-trigger
                                # Make sure player is FULLY outside the rect (left of 256)
                                self.player.rect.right = 250
                                self.ignore_bonfire_collision = True # Just in case

                    # Special Transition for pipe_nightmare_2 -> pipe_nightmare_3
                    if self.current_map_id == "pipe_nightmare_2":
                        # Rows 4-5 (Indices 3-4), Cols 5-6 (Indices 4-5)
                        # Tile size 128
                        # x: 4*128=512, y: 3*128=384. w=256, h=256
                        pipe_rect = pygame.Rect(512, 384, 256, 256)

                        if self.player.rect.colliderect(pipe_rect):
                            self.confirm_dialog.set_text("是否进入管道噩梦？")
                            bg_surf = self.screen.copy()
                            if self.confirm_dialog.run(bg_surf):
                                 self.run_transition("pipe_nightmare_3", "left", hold_duration=1.0)
                            else:
                                # Push player left to avoid immediate re-trigger
                                # Entrance is on the right side (Cols 5-6), so pushing left is safe
                                if self.player.rect.right > 512:
                                    self.player.rect.right = 500
                                self.ignore_bonfire_collision = True

                    # Update
                    if not self.dialogue_system.active:
                        obstacles = self.tile_manager.collision_rects
                        # Add props to obstacles
                        for prop in self.props_group:
                            obstacles.append(prop.hitbox)

                        # Noise System Update
                        if hasattr(self.player, 'noise_level'):
                            keys = pygame.key.get_pressed()
                            # Only add continuous noise for LONG PRESS (Holding)
                            # We define "Holding" as: key is pressed AND it wasn't a fresh tap.
                            # But simpler logic: User said "Tap avoids chase, Long press chases".
                            # This implies moving generates noise per frame, but if you only move for a few frames (Tap),
                            # the accumulated noise is small enough to decay or stay under threshold.
                            # My previous implementation:
                            # KEYDOWN: +15
                            # Key Pressed: +2 per frame
                            # Decay: -0.5 per frame

                            # Problem: Tapping W for 5 frames (approx 0.1s)
                            # Noise = 15 + 5 * 2 = 25.
                            # Decay = 5 * 0.5 = 2.5.
                            # Net ~ 22.5. Safe.

                            # Problem: "Immediate chase on entry"
                            # This likely means noise_level persists.
                            # I will reset noise_level in load_map (done separately).

                            # But wait, user says "Point press avoids chase".
                            # If I add +15 on KEYDOWN, that IS the penalty for "Point press".
                            # Maybe +15 is too high if they tap rapidly?
                            # If they tap 4 times a second: 4 * 15 = 60. Safe-ish.
                            # But if they hold: 60 * 2 = 120 per second.

                            # The user says "I enter room and am chased immediately".
                            # This strongly suggests persistence or initialization issue.

                            if keys[pygame.K_w] or keys[pygame.K_a] or keys[pygame.K_s] or keys[pygame.K_d] or \
                               keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
                                # Only add noise if moving
                                self.player.noise_level += 2

                            decay = getattr(self.player, 'noise_decay', 0.5)
                            self.player.noise_level = max(0, self.player.noise_level - decay)

                        self.player.update(obstacles, self.tile_manager.terminal_rects)
                        self.enemies_group.update(self.player)
                        self.bonfire_group.update()
                        self.props_group.update()

                        # Collectibles Update
                        if self.tile_manager:
                            self.tile_manager.update_collectibles()

                        for fg in self.fog_gates:
                            fg.update()
                        if self.fog_wall:
                            self.fog_wall.update()

                        self.camera.update(self.player)

                        if MAP_CONFIG[self.current_map_id].get("is_pipe_channel") or MAP_CONFIG[self.current_map_id].get("is_vertical_pipe_channel"):
                            self.pipe_atmosphere.update()

                        # Fog Gate Interaction
                        for fg in self.fog_gates:
                            if self.player.rect.colliderect(fg.rect):
                                # Determine Orientation
                                is_horizontal = fg.rect.width > fg.rect.height

                                should_trigger_dialog = False
                                push_target = None

                                if is_horizontal:
                                    # Horizontal Gate (e.g. Bottom Edge)
                                    # Check if player is "Outside" (Below for Bottom Edge, Above for Top Edge?)
                                    # Assumption: Boss is usually "Inside" (Top/Left). Gates block "Outside" (Bottom/Right).
                                    # But we should be generic.
                                    # For Pipe 2-2: Gates are at y=640 (Bottom) and x=640 (Right).
                                    # Boss is at (1,2) (Inside).
                                    # So Outside is > 640. Inside is < 640.

                                    is_outside = self.player.rect.centery > fg.rect.centery
                                    if is_outside:
                                        should_trigger_dialog = True
                                    else:
                                        # Inside - Block (Push Up)
                                        self.player.rect.bottom = fg.rect.top + 5 # Slight overlap prevention
                                else:
                                    # Vertical Gate
                                    # Check if player is "Outside" (Right side for Right Edge)
                                    is_outside = self.player.rect.centerx > fg.rect.centerx

                                    # Special Case: Base 5 Gate (x=236). Boss is at Right. Outside is Left.
                                    # In Base 5, Boss is "Inside" (Right). Player comes from Left.
                                    # So Outside is < 236.
                                    # We need a way to distinguish "Entry Direction".
                                    # Base 5 Gate Rect: (236, 512, 40, 256).
                                    # Pipe 2-2 Gate Rect: (640-20, 0, 40, 640).

                                    if self.current_map_id == "base_5":
                                        # Base 5: Entry from Left (Outside)
                                        is_outside = self.player.rect.centerx < fg.rect.centerx
                                        if is_outside:
                                            should_trigger_dialog = True
                                        else:
                                            # Inside (Right) - Block (Push Right)
                                            self.player.rect.left = fg.rect.right - 5
                                    else:
                                        # Pipe 2-2 (and others): Entry from Right/Bottom (Outside)
                                        # Pipe 2-2 Vertical Gate is at x=640. Boss is Left.
                                        # So Outside is Right (x > 640).
                                        is_outside = self.player.rect.centerx > fg.rect.centerx
                                        if is_outside:
                                            should_trigger_dialog = True
                                        else:
                                            # Inside (Left) - Block (Push Left)
                                            self.player.rect.right = fg.rect.left + 5

                                if should_trigger_dialog:
                                     self.confirm_dialog.set_text("是否穿过雾门？")
                                     bg_surf = self.screen.copy()

                                     if self.confirm_dialog.run(bg_surf):
                                         self.fog_anim_active = True
                                         self.fog_anim_timer = 0

                                         if is_horizontal:
                                             if is_outside:
                                                 self.fog_anim_direction = (0, -2)
                                             else:
                                                 self.fog_anim_direction = (0, 2)
                                         else:
                                            if self.current_map_id == "base_5":
                                                if is_outside:
                                                    self.fog_anim_direction = (2, 0)
                                                else:
                                                    self.fog_anim_direction = (-2, 0)
                                            else:
                                                if self.current_map_id == "pipe_nightmare_2_2":
                                                    # Explicit check for Pipe 2-2 Vertical Gate (Right side)
                                                    # Outside is Right. Move Left to Enter.
                                                    if is_outside:
                                                        self.fog_anim_direction = (-2, 0)
                                                    else:
                                                        self.fog_anim_direction = (2, 0)
                                                else:
                                                    if is_outside:
                                                        self.fog_anim_direction = (-2, 0)
                                                    else:
                                                        self.fog_anim_direction = (2, 0)
                                     else:
                                        # Push back to Outside
                                        push_dist = 20
                                        if is_horizontal:
                                            self.player.rect.top = fg.rect.bottom + push_dist
                                        else:
                                            if self.current_map_id == "base_5":
                                                 self.player.rect.right = fg.rect.left - push_dist
                                            else:
                                                 self.player.rect.left = fg.rect.right + push_dist

                        # Fog Wall Interaction (Block only)
                        if self.fog_wall and self.player.rect.colliderect(self.fog_wall.rect):
                             # Horizontal Wall: Check Y relative to center
                             if self.player.rect.centery < self.fog_wall.rect.centery:
                                 self.player.rect.bottom = self.fog_wall.rect.top
                             else:
                                 self.player.rect.top = self.fog_wall.rect.bottom

                        # Bonfire Interaction Check
                        colliding_bonfire = None
                        for b in self.bonfire_group:
                            if self.player.rect.colliderect(b.hitbox):
                                colliding_bonfire = b
                                break

                        if colliding_bonfire:
                            # Activate Bonfire
                            if self.current_map_id not in self.game_state.activated_bonfires:
                                self.game_state.activated_bonfires.append(self.current_map_id)
                                print(f"Bonfire activated: {self.current_map_id}")

                            # Rest at Bonfire (Heal + Refill Battery)
                            if not self.ignore_bonfire_collision:
                                self.player.hp = self.player.max_hp
                                self.player.battery_count = self.player.max_battery_count # Assume 3 is max for now or use attribute
                                # Reset killed enemies
                                self.game_state.temp_killed_enemies = []
                                # Reload map to respawn them
                                self.load_map(self.current_map_id, silent=True)

                                # Update Last Rest Point
                                self.game_state.last_rest_map_id = self.current_map_id
                                # Use spawn_pos from config if available, else current pos (approx) or bonfire pos
                                cfg = MAP_CONFIG.get(self.current_map_id, {})
                                self.game_state.last_rest_pos = cfg.get("spawn_pos", (self.player.rect.x, self.player.rect.y))

                            if not self.ignore_bonfire_collision:
                                bg_surf = self.screen.copy()
                                result = self.bonfire_menu.run(bg_surf)

                                if result == "save":
                                    save_game(self.player, self.game_state, self.current_map_id)
                                    self.save_success_timer = 30 # Show "Game Saved" for 0.5 second (30 frames)
                                elif result == "teleport":
                                     # Teleport Logic
                                     destinations = []
                                     for mid, cfg in MAP_CONFIG.items():
                                         if cfg.get("has_bonfire") and mid in self.game_state.activated_bonfires:
                                             destinations.append({"id": mid, "name": cfg.get("name")})

                                     current_map_name = MAP_CONFIG[self.current_map_id].get("name")
                                     teleport_menu = TeleportMenu(self.screen, current_map_name, destinations)
                                     target_id = teleport_menu.run(self.screen.copy())

                                     if target_id:
                                         self.current_map_id = target_id
                                         self.load_map(self.current_map_id)
                                         self.update_all_volumes()
                                         spawn_pos = MAP_CONFIG[self.current_map_id].get("spawn_pos", (128*2, 128*2))
                                         self.player.rect.topleft = spawn_pos
                                         self.ignore_bonfire_collision = True
                                elif result == "leave":
                                    self.ignore_bonfire_collision = True
                        else:
                            self.ignore_bonfire_collision = False

                        # Collision Check: Player vs Enemy -> Battle
                        # Use ratio 0.6 to require closer proximity (smaller hitbox)
                        collided_enemy = pygame.sprite.spritecollideany(self.player, self.enemies_group, collided=pygame.sprite.collide_rect_ratio(0.6))
                        if collided_enemy:
                            if self.player.battle_cooldown <= 0:
                                self.current_state = self.STATE_BATTLE
                                battle_data = getattr(collided_enemy, 'battle_data', None)
                                self.battle_manager.start_battle(self.player, battle_data)

                # Custom Boundary Check for Pipe Nightmare 1-3 (Bottom Exit)
                if self.current_map_id == "pipe_nightmare_1_3" and self.player.rect.y > SCREEN_HEIGHT:
                     self.run_transition("pipe_nightmare_2_3", "exact_top")

                # --- Pipe Nightmare 3-2 & 3-3 Freeze Logic ---
                if self.current_map_id in ["pipe_nightmare_3_2", "pipe_nightmare_3_3"]:
                    is_moving = self.player.velocity.length() > 0

                    if is_moving or self.is_frozen or self.freeze_timer > 0:
                        self.freeze_timer += 1 / 60.0 # Approx dt

                        if self.freeze_timer >= self.FREEZE_CYCLE:
                            self.freeze_timer = 0
                            self.is_frozen = False
                            self.static_frame = None
                            # Play Glitch Sound
                            if self.glitch_sound:
                                 self.glitch_sound.play()
                        elif self.freeze_timer >= self.FREEZE_START and not self.is_frozen:
                            self.is_frozen = True
                            self.static_frame = self.screen.copy()
                else:
                    self.freeze_timer = 0
                    self.is_frozen = False
                    self.static_frame = None

                # Draw
                if self.is_frozen and self.static_frame:
                    self.screen.blit(self.static_frame, (0, 0))

                    # Visual Interference: Random Black Blocks
                    for _ in range(15):
                         w = random.randint(50, 300)
                         h = random.randint(10, 80)
                         x = random.randint(0, SCREEN_WIDTH - w)
                         y = random.randint(0, SCREEN_HEIGHT - h)
                         s = pygame.Surface((w, h))
                         s.fill((0, 0, 0))
                         s.set_alpha(random.randint(20, 60)) 
                         self.screen.blit(s, (x, y))

                    # Visual Interference: Scanlines
                    for i in range(0, SCREEN_HEIGHT, 8):
                         pygame.draw.line(self.screen, (0, 0, 0, 40), (0, i), (SCREEN_WIDTH, i))

                    pygame.display.flip()
                    self.clock.tick(FPS)
                    continue # Skip normal draw

                self.screen.fill(COLOR_BG)

                # Draw Map
                if self.tile_manager:
                    self.tile_manager.draw(self.screen, self.camera)

                # 出口「数据缝」微光（画在地板上，实体之下）
                for glow in self.exit_glows:
                    glow.update()
                    glow.draw(self.screen)

                # Draw Entities
                # Collectibles are now drawn by tile_manager.draw()

                for sprite in self.bonfire_group:
                    self.screen.blit(sprite.image, self.camera.apply(sprite))

                for prop in self.props_group:
                    self.screen.blit(prop.image, self.camera.apply(prop))

                for sprite in self.enemies_group:
                    self.screen.blit(sprite.image, self.camera.apply(sprite))

                self.screen.blit(self.player.image, self.camera.apply(self.player))

                # Fog Maze (Pipe Nightmare 1-3 & 3-3)
                if self.current_map_id in ["pipe_nightmare_1_3", "pipe_nightmare_3_3"]:
                    self.fog_maze.draw(self.screen, self.camera.apply(self.player))
                    # Also draw Fog Walls (the visible obstacles)
                    for fw in self.fog_walls: 
                        fw.update()
                        fw.draw(self.screen, self.camera)

                if MAP_CONFIG[self.current_map_id].get("is_pipe_channel"):
                    self.pipe_atmosphere.draw(self.screen, mode="horizontal")
                    self.pipe_atmosphere.update(mode="horizontal")
                elif MAP_CONFIG[self.current_map_id].get("is_vertical_pipe_channel"):
                    self.pipe_atmosphere.draw(self.screen, mode="vertical")
                    self.pipe_atmosphere.update(mode="vertical")

                # Pulse Atmosphere (Pipe Nightmare 3-1 & 3-3)
                if self.current_map_id in ["pipe_nightmare_3_1", "pipe_nightmare_3_3"]:
                    speed = 0.002
                    if self.current_map_id == "pipe_nightmare_3_3" and hasattr(self.player, 'noise_level'):
                         threshold = getattr(self.player, 'noise_threshold', 100)
                         if self.player.noise_level > threshold:
                             speed = 0.02 # Faster flicker

                    self.pulse_atmosphere.update(speed=speed)
                    self.pulse_atmosphere.draw(self.screen)

                if self.fog_wall:
                    self.fog_wall.update()
                    self.fog_wall.draw(self.screen, self.camera)

                # Draw Fog Gates (List)
                for fg in self.fog_gates:
                    fg.update()
                    fg.draw(self.screen, self.camera)

                # Draw Fog Walls (List) - Already drawn in pipe_nightmare section, but let's consolidate if possible
                # Check lines 1864-1865: "Also draw Fog Walls (the visible obstacles)"
                # It only draws, doesn't update. Let's add update there or move it here.
                # To be safe and avoid double draw, I will stick to the existing structure for fog_walls in pipe_nightmare_1_3
                # but I should ensure they are updated.


                # Particles (Data Dust)
                for p in self.particles:
                    p.update()
                    p.draw(self.screen)

                # UI Overlay
                try:
                    font = get_font(24)
                except:
                    font = pygame.font.Font(None, 24)

                # 拾取提示显示期间短暂隐藏 HP，避免重叠
                if self.pickup_notice_timer == 0:
                    hp_text = font.render(f"HP: {self.player.hp}/{self.player.max_hp}", True, (255, 255, 255))
                    self.screen.blit(hp_text, (10, 10))

                self.area_title.update()
                self.area_title.draw()

                self.dialogue_system.draw(self.screen)

                # Save Success Message
                if self.save_success_timer > 0:
                    save_msg = font.render("存档已保存", True, (0, 255, 0))
                    self.screen.blit(save_msg, (50, SCREEN_HEIGHT - 50))

                # 拾取提示（紧贴屏幕最上方的全宽横条，1.5s 后消失）
                if self.pickup_notice_timer > 0 and self.pickup_notice_text:
                    try:
                        notice_font = get_font(28)
                    except:
                        notice_font = pygame.font.Font(None, 28)
                    notice_surf = notice_font.render(self.pickup_notice_text, True, (255, 255, 255))
                    bar_h = 56
                    bar = pygame.Surface((SCREEN_WIDTH, bar_h), pygame.SRCALPHA)
                    bar.fill((0, 0, 0, 220))
                    self.screen.blit(bar, (0, 0))
                    notice_rect = notice_surf.get_rect(center=(SCREEN_WIDTH // 2, bar_h // 2))
                    self.screen.blit(notice_surf, notice_rect)

                pygame.display.flip()
                self.clock.tick(FPS)

            # --- State: Battle ---
            elif self.current_state == self.STATE_BATTLE:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    else:
                        self.battle_manager.handle_input(event)

                self.battle_manager.update()

                self.screen.fill((0, 0, 0)) # Battle BG
                self.battle_manager.draw()
                pygame.display.flip()
                self.clock.tick(FPS)

                if not self.battle_manager.running:
                    if self.battle_manager.battle_result == "lost":
                        self.current_state = self.STATE_GAMEOVER
                        self.gameover_timer = pygame.time.get_ticks()
                    else:
                        self.current_state = self.STATE_OVERWORLD

                        # Win or Flee or Spare
                        if self.battle_manager.battle_result == "win" or self.battle_manager.battle_result == "spare":
                            # Handle Enemy Persistence
                            # Check if Boss
                            boss_id = self.battle_manager.enemy_data.get("boss_id")
                            if boss_id:
                                if boss_id not in self.game_state.cleared_bosses:
                                    self.game_state.cleared_bosses.append(boss_id)
                                    print(f"Boss Cleared: {boss_id}")
                                    # Optional: Auto-save on boss clear?
                                    # save_game(self.player, self.game_state, self.current_map_id)

                            # Check if Minion (Standard Respawnable Enemy)
                            enemy_id = self.battle_manager.enemy_data.get("id")
                            if enemy_id:
                                # Only add to temp_killed if NOT a boss (though logic allows overlap if needed)
                                # Assuming bosses also have unique IDs but we track them via cleared_bosses for permadeath
                                if not boss_id:
                                    if enemy_id not in self.game_state.temp_killed_enemies:
                                        self.game_state.temp_killed_enemies.append(enemy_id)

                            # Remove from current group
                            for e in self.enemies_group:
                                # Match by ID or Boss ID
                                e_data = getattr(e, 'battle_data', {})
                                if (enemy_id and e_data.get('id') == enemy_id) or \
                                   (boss_id and e_data.get('boss_id') == boss_id):
                                    e.kill()
                                    break

                            boss_id = self.battle_manager.enemy_data.get("boss_id")
                            if boss_id:
                                if boss_id not in self.game_state.cleared_bosses:
                                    self.game_state.cleared_bosses.append(boss_id)

                                if boss_id == "base_5_boss":
                                    self.fog_wall = None
                                    # Also clear list if we migrate base_5 to use list in future
                                    self.fog_gates = [] 
                                    for enemy in self.enemies_group:
                                        if getattr(enemy, 'battle_data', {}).get('boss_id') == boss_id:
                                            enemy.kill()
                                            break

                                elif boss_id == "pipe_2_2_boss":
                                    self.fog_gates = [] # Clear fog gates
                                    for enemy in self.enemies_group:
                                        if getattr(enemy, 'battle_data', {}).get('boss_id') == boss_id:
                                            enemy.kill()
                                            break
                        else:
                            # Fleeing
                            self.player.rect.y += 50

                        self.player.battle_cooldown = 180
                        load_bgm("audio/bgm/city ruins.mp3")
                        self.current_bgm = "audio/bgm/city ruins.mp3"

            # --- State: GameOver ---
            elif self.current_state == self.STATE_GAMEOVER:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False

                self.screen.fill((0, 0, 0))

                try:
                    font_large = get_font(72)
                except:
                    font_large = pygame.font.Font(None, 72)

                text = font_large.render("YOU DIED", True, (200, 0, 0))
                text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                self.screen.blit(text, text_rect)

                pygame.display.flip()
                self.clock.tick(FPS)

                if pygame.time.get_ticks() - self.gameover_timer > 3000: # 3 seconds
                    # Respawn Logic
                    print(f"Respawning at {self.game_state.last_rest_map_id}")
                    self.game_state.temp_killed_enemies = []

                    self.current_map_id = self.game_state.last_rest_map_id
                    self.load_map(self.current_map_id)
                    self.player.rect.topleft = self.game_state.last_rest_pos

                    self.player.hp = self.player.max_hp
                    self.player.battery_count = self.player.max_battery_count

                    self.area_title.show()
                    self.current_state = self.STATE_OVERWORLD

                    load_bgm("audio/bgm/city ruins.mp3")
                    self.current_bgm = "audio/bgm/city ruins.mp3"

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
