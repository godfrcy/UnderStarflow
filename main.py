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
from engine.enemy_data import BATTLE_DATA, ABANDONED_ROBOT_DATA
from engine.save_system import save_game, load_game
from entities.player import Player
from entities.enemies import OverworldEnemy, Bonfire, FailureEnemy
from entities.props import Prop
from ui.menus import TitleScreen, ConfirmDialog, BonfireMenu, TeleportMenu, PauseMenu, VolumeMenu, BackpackMenu, StatsMenu
from ui.dialogue import DialogueSystem
from ui.effects import SnowFlake, AreaTitle, DataDust, FogGate, FogWall
from ui.atmosphere import PipeAtmosphere, PulseAtmosphere, FogMaze

# --- Main Game Loop ---

def main():
    # 1. Initialize Pygame
    pygame.init()
    pygame.mixer.init()
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Under Starflow")
    try:
        icon = pygame.image.load(resource_path("ui/backgrounds/mechanical_heart.jpeg"))
        pygame.display.set_icon(icon)
    except Exception as e:
        print(f"Warning: Failed to load icon: {e}")
    clock = pygame.time.Clock()
    
    # 2. Initialize Subsystems
    game_state = GameState()
    battle_manager = BattleManager(screen)
    
    # Camera & Map
    camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT) # Map size will be updated later if needed
    
    # Entities Groups
    enemies_group = pygame.sprite.Group()
    bonfire_group = pygame.sprite.Group()
    # interactables_group removed, managed by TileManager
    
    # ParticlesState Variables
    current_map_id = "start"
    tile_manager = None
    
    # Particles
    particles = []
    fog_gates = [] # List of FogGates
    fog_wall = None
    fog_walls = [] # Initialize fog_walls in main scope
    
    props_group = pygame.sprite.Group() # New Prop Group
    
    # Fog Animation State
    fog_anim_active = False
    fog_anim_timer = 0
    fog_anim_direction = (2, 0)
    FOG_ANIM_DURATION = 90 # 1.5s * 60FPS

    # Helper to load map
    def load_map(map_id, silent=False):
        nonlocal tile_manager, fog_gates, fog_wall, fog_walls, fog_anim_active
        
        # Reset Player Noise Level on Map Transition
        if hasattr(player, 'noise_level'):
            player.noise_level = 0
            
        # Reset Fog Anim
        fog_anim_active = False
        
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
        tile_manager = TileManager(found_path, extra_obstacles=extra_obstacles, open_top_rows=open_top_rows, is_pipe_channel=is_pipe_channel, is_vertical_pipe_channel=is_vertical_pipe_channel, rotation=rotation)
        
        # 2. Clear & Populate Entities
        enemies_group.empty()
        bonfire_group.empty()
        props_group.empty()
        # tile_manager.collectibles is new, so it starts empty for new map instance
        
        # Reset Particles
        particles.clear()
        
        # Fog Gate
        fog_gates = [] # Clear fog gates
        
        # Only spawn if boss NOT defeated (placeholder boss id: 'base_5_boss')
        if map_id == "base_5" and "base_5_boss" not in game_state.cleared_bosses:
            # Rect: 256 - 20 = 236, 512, 40, 256
            fg = FogGate(pygame.Rect(236, 512, 40, 256))
            fog_gates.append(fg)
            # Fog Wall: Row 5 (index 4) top edge, Cols 3,4 (indices 2,3)
            # X: 256, Y: 512. Width 256, Height 40 (centered on 512)
            fog_wall = FogWall(pygame.Rect(256, 512 - 20, 256, 40))
        # Pipe Nightmare 1-3: Visualize Extra Obstacles as Fog Walls
        elif map_id == "pipe_nightmare_1_3":
             fog_walls = [] # Use list for multiple walls
             if extra_obstacles:
                 for (col, row) in extra_obstacles:
                     # Create a FogWall for each obstacle tile (128x128)
                     # Inflate slightly to ensure coverage? No, exact fit is fine.
                     # Visible=False to reduce lag
                     fw = FogWall(pygame.Rect(col * 128, row * 128, 128, 128), visible=False)
                     fog_walls.append(fw)

             # Abandoned Robot (废弃机器人) - Additional Instance
             # Pos: (3, 4) -> 128*3, 128*4 (On the path to bottom exit)
             # "Right-Bottom area" of the playable path (Col 2,3 open)
             robot_id_1_3 = "pipe_nightmare_1_3_robot"
             if robot_id_1_3 not in game_state.temp_killed_enemies:
                 custom_w = int(128 * 1.2)
                 custom_h = int(128 * 1.1)
                 # 01 Static: is_static=True
                 enemy = OverworldEnemy(128 * 3, 128 * 4, "characters/enemies/abandoned_robot", "abandoned_robot", is_grid=True, custom_size=(custom_w, custom_h), is_static=True)
                 
                 # Enable Chase/AI
                 enemy.can_chase = True
                 enemy.vision_range = 300
                 enemy.chase_speed = 2.0
                 
                 enemy.battle_data = dict(ABANDONED_ROBOT_DATA, id=robot_id_1_3)
                 enemies_group.add(enemy)
        
        # Pipe Nightmare 2-2: Ghost Samurai Boss & Fog Gates
        elif map_id == "pipe_nightmare_2_2":
            # 1. Fog Gates
            # Only if boss NOT defeated
            if "pipe_2_2_boss" not in game_state.cleared_bosses:
                # Reduce to 4x4 area (512x512)
                # Horizontal: Fourth row bottom edge (y=512)
                # Spanning Cols 0-4 (0-512)
                fg_h = FogGate(pygame.Rect(0, 512 - 20, 512, 40))
                fog_gates.append(fg_h)
                
                # Vertical: Fourth column right edge (x=512)
                # Spanning Rows 0-4 (0-512)
                fg_v = FogGate(pygame.Rect(512 - 20, 0, 40, 512))
                fog_gates.append(fg_v)
            
            # 2. Ghost Samurai Boss
            # Pos: Third row (Index 2), Second col (Index 1) -> 128*1, 128*2
            if "pipe_2_2_boss" not in game_state.cleared_bosses:
                enemy = OverworldEnemy(128 * 2, 128 * 3, "characters/enemies/samurai_ghost", "samurai_ghost", is_grid=True, custom_size=(141, 154))
                enemy.battle_data = dict(BATTLE_DATA["ghost_samurai"])
                enemies_group.add(enemy)

        else:
            fog_gates = []
            fog_wall = None
            fog_walls = [] # Ensure fog_walls is defined
            
        if "base" in map_id:
            for _ in range(100):
                particles.append(DataDust())

        
        # Config-based Bonfire
        if config.get("has_bonfire"):
            b_pos = config.get("bonfire_pos")
            if b_pos:
                bonfire = Bonfire(b_pos[0], b_pos[1])
                bonfire_group.add(bonfire)

        if map_id == "snow_1_2":
            # Variable Entity (Replaces Machine Soldier)
            # Using variable_grid which contains variable_X_Y.png
            # Updated to use "新版变量.png" from assetsDB (Single file spritesheet)
            enemy_id = "snow_1_2_variable"
            if enemy_id not in game_state.temp_killed_enemies:
                # Point to the FILE, not a folder. OverworldEnemy now handles files.
                enemy = OverworldEnemy(128 * 4, 128 * 2, "characters/enemies/berserk_variable/berserk_variable.png", "variable", is_grid=True)
                enemy.battle_data = dict(BATTLE_DATA["variable"])
                enemies_group.add(enemy)
            
            # New Item at (2, 5) -> 128*2, 128*5
            # Add via TileManager
            item_id = "snow_1_2_battery_01"
            if item_id not in game_state.collected_items:
                item_data = {
                    "name": "投掷电池", 
                    "type": "battery", 
                    "value": 1, 
                    "description": "极不稳定的电池，可以投掷。"
                }
                # Scale 0.5 (1/2 size) as requested
                tile_manager.add_collectible(128 * 2, 128 * 5, "items/battery", item_data, "audio/bgm/new_items.mp3", item_id=item_id, scale=0.5)
            
        elif map_id == "pipe_nightmare_1":
            # 暴走变量_激光 at 5,5 (Restored Asset & Corrected Pos)
            enemy_id_1 = "pipe_nightmare_1_laser"
            if enemy_id_1 not in game_state.temp_killed_enemies:
                # Restore to previous asset
                enemy = OverworldEnemy(128 * 5, 128 * 5, "characters/enemies/variable_laser/variable_laser_透明.png", "variable_laser", is_grid=True)
                enemy.battle_data = dict(BATTLE_DATA["berserk_laser"])
                enemies_group.add(enemy)
                
            # 暴走变量_跳跃 at 3,3 (Restored Pos & Removed Flip)
            enemy_id_2 = "pipe_nightmare_1_jump"
            if enemy_id_2 not in game_state.temp_killed_enemies:
                # Use transparent asset, NO flip correction
                enemy = OverworldEnemy(128 * 3, 128 * 3, "characters/enemies/variable_jump/variable_jump透明.png", "variable_jump", is_grid=True)
                enemy.battle_data = dict(BATTLE_DATA["berserk_jump"])
                enemies_group.add(enemy)

        elif map_id == "pipe_nightmare_3_3":
             # Use same Fog Wall logic as 1-3 if needed
             if extra_obstacles:
                 fog_walls = []
                 for (col, row) in extra_obstacles:
                     fw = FogWall(pygame.Rect(col * 128, row * 128, 128, 128))
                     fog_walls.append(fw)
            
             # Spawn FailureEnemy
             if "failure_enemy_01" not in game_state.temp_killed_enemies:
                 # Center of map: 4x4 tiles, so 256, 256 is center-ish
                 enemy = FailureEnemy(128 * 2, 128 * 2) 
                 enemy.battle_data = dict(BATTLE_DATA["failure"])
                 enemies_group.add(enemy)
             
             # Add Console Prop (Bottom Center)
             if tile_manager:
                 cx = tile_manager.width // 2
                 cy = tile_manager.height - 64
                 console = Prop(cx, cy, "objects/console/console.png", scale=0.2)
                 # Manually set hitbox to center point (5x5 rect)
                 console.hitbox = pygame.Rect(0, 0, 5, 5)
                 console.hitbox.center = console.rect.center
                 console.is_console = True # Flag for interaction
                 props_group.add(console)

        elif map_id == "base_5":
            if "base_5_boss" not in game_state.cleared_bosses:
                 # Black Ranger EX (Grid)
                 # Position: Inside Fog Gate (Bottom-Right)
                 # Using grid assets from assetsDB/黑游侠_grid
                 enemy = OverworldEnemy(0, 0, "characters/enemies/black_ranger", "black_ranger", is_grid=True)
                 
                 # Flip all frames (User wants facing Left, defaults to Right)
                 if enemy.frames:
                     enemy.frames = [pygame.transform.flip(f, True, False) for f in enemy.frames]
                     enemy.image = enemy.frames[0]
                 
                 enemy.rect = enemy.image.get_rect()
                 # Fog Gate Rect is (236, 512, 40, 256)
                 # User requested "Base 5 Bottom-Right Corner"
                 # Map is 6x6 (768x768)
                 # Align to bottom-right of the map
                 enemy.rect.bottomright = (750, 750)
                 enemy.pos = [float(enemy.rect.x), float(enemy.rect.y)]
                 
                 # 1. Slow down animation (2x slower than base, currently was 4x)
                 # Base is 6. 4x was 24. User wants "Double the CURRENT speed"
                 # Wait, "Speed" = 1/Duration.
                 # "Animation Speed is 2x current".
                 # Current Speed is Slow. 2x Speed means Faster.
                 # Current Duration = 24 ticks. Faster = Shorter Duration.
                 # 2x Speed -> 12 ticks.
                 # Base is 6. So multiplier is 2.
                 enemy.ANIM_SPEED *= 2
                 
                 # 2. Wander Logic
                 # 6th row (y=640-768), last 3 cells (x=384-768)
                 # Wander between x=400 and x=750
                 enemy.set_wander_behavior(min_x=400, max_x=750, speed=0.5)
                 
                 enemy.battle_data = dict(BATTLE_DATA["black_ranger"])
                 enemies_group.add(enemy)
            
        elif map_id == "snow_1_3":
            pass
            
        elif map_id == "pipe_nightmare_2_3":
             # Add Monitor Prop in Middle
             # Map is 6x6 tiles (768x768). Middle is 384, 384.
             # Scale 0.2 (1/5th size)
             # Shrink hitbox significantly (e.g. 20px on each side)
             monitor = Prop(384, 384, "objects/props/monitor.png", scale=0.2, hitbox_shrink=(40, 40))
             props_group.add(monitor)

             # Abandoned Robot (废弃机器人)
             # Pos: (2, 5) -> 128*2, 128*5
             # Scale: Width 120% (128*1.2=153.6), Height 110% (128*1.1=140.8)
             # AI: Chase logic enabled, Flip mechanism (Default Right)
             robot_id = "pipe_nightmare_2_3_robot"
             if robot_id not in game_state.temp_killed_enemies:
                 custom_w = int(128 * 1.2)
                 custom_h = int(128 * 1.1)
                 enemy = OverworldEnemy(128 * 2, 128 * 5, "characters/enemies/abandoned_robot", "abandoned_robot", is_grid=True, custom_size=(custom_w, custom_h))
                 
                 # Enable Chase/AI
                 enemy.can_chase = True
                 enemy.vision_range = 300
                 enemy.chase_speed = 2.0
                 
                 enemy.battle_data = dict(ABANDONED_ROBOT_DATA, id=robot_id)
                 enemies_group.add(enemy)

        elif map_id == "base_2":
            # Machine Soldier (机凯种)
            # Center of map (approx 128*3, 128*3)
            enemy_id = "base_2_machine"
            if enemy_id not in game_state.temp_killed_enemies:
                enemy = OverworldEnemy(128 * 3, 128 * 3, "characters/enemies/machine_soldier", "jikaizhong", is_grid=True)
                enemy.battle_data = dict(BATTLE_DATA["machine_soldier"])
                enemies_group.add(enemy)

        elif map_id == "base_3":
            # Admin (Rebel Leader / 义军)
            # Center of map (approx 128*3, 128*3)
            # Use rebel_leader assets
            enemy_id = "base_3_admin"
            if enemy_id not in game_state.temp_killed_enemies:
                enemy = OverworldEnemy(128 * 3, 128 * 3, "characters/enemies/rebel_leader", "rebel_leader", is_grid=True)
                enemy.ANIM_SPEED = 12 # Slow down animation
                # Rebel Exclusive: Enable Chase Logic
                enemy.can_chase = True
                enemy.vision_range = 300
                enemy.chase_speed = 2.5
                enemy.battle_data = dict(BATTLE_DATA["admin"])
                enemies_group.add(enemy)
            
        # 3. Update Camera Limit
        camera.set_map_size(tile_manager.width, tile_manager.height)
        
        # Ensure volume settings are applied to new entities and existing systems
        # This fixes the issue where Map Broadcast and other SFX might not track volume changes correctly
        # or new entities (like items) default to full volume.
        try:
            update_all_volumes()
        except NameError:
            pass
        
        # Area Title
        if config.get("show_title", True):
            if not silent:
                area_title.set_text(config.get("name", "Unknown"))
                area_title.show()
        else:
            area_title.hide()
            
        return tile_manager

    # UI Instances
    title_screen = TitleScreen(screen)
    confirm_dialog = ConfirmDialog(screen)
    bonfire_menu = BonfireMenu(screen)
    pause_menu = PauseMenu(screen)
    volume_menu = VolumeMenu(screen)
    backpack_menu = BackpackMenu(screen)
    stats_menu = StatsMenu(screen)
    area_title = AreaTitle(screen, "无主雪地")
    dialogue_system = DialogueSystem()
    
    # Load UI Assets
    # sync_rate_icon removed as requested

    # Volume Helper (Defined here to access UI instances)
    def update_all_volumes():
        sfx_vol = config.SFX_VOLUME
        
        # Battle Manager
        if battle_manager.calibration_sfx:
            battle_manager.calibration_sfx.set_volume(sfx_vol)
            
        # Area Title
        if area_title.sound:
            area_title.sound.set_volume(sfx_vol)
            
        # Collectibles
        if tile_manager:
            for item in tile_manager.collectibles:
                if item.sound:
                    item.sound.set_volume(sfx_vol)
                
    # Player
    player = Player(128 * 2, 128 * 5)

    # Initial Load
    load_map(current_map_id, silent=True)
    update_all_volumes() # Apply initial volume settings to loaded items
    
    # 4. State Machine
    STATE_TITLE = 0
    STATE_OVERWORLD = 1
    STATE_BATTLE = 2
    STATE_GAMEOVER = 3
    
    current_state = STATE_TITLE
    gameover_timer = 0
    
    # BGM State
    current_bgm = None
    
    # Bonfire Trigger Logic
    ignore_bonfire_collision = False
    
    # Transition Helper
    def run_transition(next_map_id, start_pos_type, hold_duration=0):
        nonlocal current_map_id
        
        # Record Entry Type for Logic (e.g. Pipe Nightmare 2_1 routing)
        game_state.last_entry_type = start_pos_type
        
        # Fade Out (Faster: step 25, delay 15ms -> ~150ms)
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade.fill((0, 0, 0))
        for alpha in range(0, 256, 25):
            # Draw current state one last time? 
            # Ideally we just draw black over it
            fade.set_alpha(alpha)
            screen.blit(fade, (0, 0))
            pygame.display.update()
            pygame.time.delay(15)
        
        # Hold Black Screen
        if hold_duration > 0:
            pygame.time.delay(int(hold_duration * 1000))
            
        # Load New Map
        current_map_id = next_map_id
        load_map(current_map_id)
        
        # Set Player Position
        if start_pos_type == "left":
            player.rect.x = 20
        elif start_pos_type == "right":
            player.rect.x = SCREEN_WIDTH - player.rect.width - 20
            # Fix: Force safe Y position when entering Base 5 from right (Pipe Nightmare 1)
            # Row 4 (y=512) is safe. Obstacles are at Rows 2,3 (Indices).
            if next_map_id == "base_5":
                player.rect.y = 128 * 4 # Row 5 (Index 4) - Safe Channel
            # Fix: Force safe Y position when entering Pipe Nightmare 2-2 from right (Pipe Nightmare 2-3)
            # Rows 0,1 are blocked. Clamp to Row 2 (y=256) minimum.
            elif next_map_id == "pipe_nightmare_2_2":
                if player.rect.y < 128 * 2:
                    player.rect.y = 128 * 2
        elif start_pos_type == "top":
            player.rect.y = 20
        elif start_pos_type == "exact_top":
            player.rect.y = 0
        elif start_pos_type == "bottom":
            player.rect.y = SCREEN_HEIGHT - player.rect.height - 20
        elif start_pos_type == "center_left":
             # Specific for Base entry if needed, but 'left' is fine usually
             player.rect.x = 50
            
        # Fade In (Faster)
        for alpha in range(255, -1, -25):
            screen.fill(COLOR_BG)
            # Draw Map
            if tile_manager:
                tile_manager.draw(screen, camera)
            
            # Draw Entities
            # Collectibles are drawn by tile_manager
            for s in bonfire_group: screen.blit(s.image, camera.apply(s))
            for s in enemies_group: screen.blit(s.image, camera.apply(s))
            screen.blit(player.image, camera.apply(player))
            
            fade.set_alpha(alpha)
            screen.blit(fade, (0, 0))
            pygame.display.update()
            pygame.time.delay(15)

    pipe_atmosphere = PipeAtmosphere()
    pulse_atmosphere = PulseAtmosphere()
    fog_maze = FogMaze()
    
    # import random # Ensure random is available if not already (Removed to fix NameError)

    save_success_timer = 0
    
    # Freeze Effect State (Pipe Nightmare 3-2)
    freeze_timer = 0
    is_frozen = False
    static_frame = None
    FREEZE_CYCLE = 2.0 # 2 seconds total
    FREEZE_START = 1.5 # 1.5s normal, then 0.5s frozen

    # Load Glitch Sound
    glitch_sound = None
    try:
        # User requested temporary replacement with calibration sound
        glitch_path = resource_path("audio/sfx/glitch.mp3")
        if not os.path.exists(glitch_path):
             root_dir = os.path.dirname(os.path.abspath(__file__))
             glitch_path = os.path.join(root_dir, "assetsDB", "audio", "sfx", "故障音.mp3")
        
        if os.path.exists(glitch_path):
            glitch_sound = pygame.mixer.Sound(glitch_path)
            glitch_sound.set_volume(config.SFX_VOLUME)
        else:
             print(f"Warning: Glitch sound not found at {glitch_path}")
    except Exception as e:
        print(f"Warning: Failed to load glitch sound: {e}")

    running = True
    while running:
        if save_success_timer > 0:
            save_success_timer -= 1

        # --- State: Title Screen ---
        if current_state == STATE_TITLE:
            if current_bgm != "audio/bgm/the tree.mp3":
                load_bgm("audio/bgm/the tree.mp3")
                current_bgm = "audio/bgm/the tree.mp3"
                
            action = title_screen.run()
            if action == "new_game":
                # Reset Game State
                game_state.activated_bonfires = ["start"]
                game_state.collected_items = []
                game_state.cleared_bosses = []
                game_state.temp_killed_enemies = []
                game_state.last_rest_map_id = "start"
                game_state.last_rest_pos = (128 * 3, 128 * 5)
                
                # Reset Player State
                player.hp = 20
                player.max_hp = 20
                player.inventory = []
                player.exp = 0
                player.battery_count = 3

                current_state = STATE_OVERWORLD
                current_map_id = "start"
                load_map(current_map_id)
                player.rect.topleft = (128 * 2, 128 * 5)
                area_title.show()
                dialogue_system.start_dialogue(["...真冷啊"])
            elif action == "continue":
                success, saved_map_id = load_game(player, game_state)
                if success:
                    current_map_id = saved_map_id
                    load_map(current_map_id)
                    current_state = STATE_OVERWORLD
                    area_title.show()
                    ignore_bonfire_collision = True # Fix: Prevent immediate bonfire menu trigger
                else:
                    print("Load failed, starting new game.")
                    current_state = STATE_OVERWORLD
                    current_map_id = "start"
                    load_map(current_map_id)
                    area_title.show()
            elif action == "quit":
                running = False
                
        # --- State: Overworld ---
        elif current_state == STATE_OVERWORLD:
            # Play Overworld BGM (Dynamic based on Map Config)
            target_bgm = MAP_CONFIG[current_map_id].get("bgm")
            target_bgm_start = MAP_CONFIG[current_map_id].get("bgm_start", 0.0)
            
            if target_bgm and current_bgm != target_bgm:
                load_bgm(target_bgm, start_pos=target_bgm_start)
                current_bgm = target_bgm
                
            if fog_anim_active:
                # --- Fog Animation State ---
                # Consume events to prevent freezing, but ignore input
                pygame.event.pump()
                
                fog_anim_timer += 1
                # Move player based on direction
                player.rect.x += fog_anim_direction[0]
                player.rect.y += fog_anim_direction[1]
                
                # Visual Updates
                for fg in fog_gates: fg.update()
                if fog_wall: fog_wall.update()
                for fw in fog_walls: fw.update()
                    
                camera.update(player)
                for p in particles: p.update()
                if tile_manager: tile_manager.update_collectibles()
                
                if fog_anim_timer >= FOG_ANIM_DURATION:
                    fog_anim_active = False
            
            else:
                # --- Normal Gameplay State ---
                # Event Handling
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    
                    # Dialogue Input Handling
                    if dialogue_system.active:
                        dialogue_system.handle_event(event)

                    elif event.type == pygame.MOUSEBUTTONDOWN:
                         if hasattr(player, 'noise_level'):
                             player.noise_level += 15

                    elif event.type == pygame.KEYDOWN:
                        if hasattr(player, 'noise_level'):
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
                            player.noise_level += 15

                        if event.key == pygame.K_ESCAPE:
                            bg_surf = screen.copy()
                            # New Pause Menu Logic
                            action = pause_menu.run(bg_surf)
                            
                            # Adjusted handling for new order: Title, Stats, Volume, Backpack
                            if action == "title":
                                confirm_dialog.set_text("确认返回标题界面？")
                                if confirm_dialog.run(bg_surf):
                                    current_state = STATE_TITLE
                                    title_screen.running = True
                                    current_bgm = None
                            elif action == "stats":
                                stats_menu.run(player, bg_surf)
                            elif action == "volume":
                                volume_menu.run(bg_surf, update_all_volumes)
                            elif action == "backpack":
                                dialogue_system.active = False
                                backpack_menu.run(player, screen.copy(), dialogue_system)
                                
                        elif event.key == pygame.K_F5:
                            save_game(player, game_state, current_map_id)
                        elif event.key == pygame.K_SPACE:
                            # Manual Item Interaction
                            if tile_manager:
                                tile_manager.try_collect(player, game_state)
                            
                            # Console Interaction (Pipe Nightmare 3-3)
                            if current_map_id == "pipe_nightmare_3_3":
                                console = None
                                for p in props_group:
                                    if getattr(p, 'is_console', False):
                                        console = p
                                        break
                                
                                if console:
                                    dist_x = abs(player.rect.centerx - console.rect.centerx)
                                    dist_y = abs(player.rect.centery - console.rect.centery)
                                    if dist_x < 100 and dist_y < 100:
                                        has_core = any(item.get("id") == "liquid_nitrogen_core" for item in player.inventory if isinstance(item, dict))
                                        
                                        if not has_core:
                                            player.inventory.append({
                                                "id": "liquid_nitrogen_core", 
                                                "name": "液氮冷却核心", 
                                                "type": "key_item", 
                                                "description": "极低温的冷却核心，可以冻结周围的空气。"
                                            })
                                            dialogue_system.start_dialogue([
                                                "获得了 [液氮冷却核心]。",
                                                "极低温的冷却核心，可以冻结周围的空气。",
                                                "也许可以用它通过某些高温区域。"
                                            ])
                                        else:
                                            dialogue_system.start_dialogue([
                                                "操作台已经停止工作了。",
                                                "核心已被取出。"
                                            ])

                            # Monitor Interaction (Pipe Nightmare 2-3)
                            if current_map_id == "pipe_nightmare_2_3":
                                # Find monitor
                                monitor = None
                                for p in props_group:
                                    monitor = p # Assuming only one prop or first one
                                    break
                                
                                if monitor:
                                    # Check distance
                                    dist_x = abs(player.rect.centerx - monitor.rect.centerx)
                                    dist_y = abs(player.rect.centery - monitor.rect.centery)
                                    if dist_x < 128 and dist_y < 128: # Interaction Range (1 tile)
                                        dialogue_system.start_dialogue([
                                            "冷却系统已停止响应。",
                                            "核心热域温度无法测量。"
                                        ])
                
                # Map Transitions
                if player.rect.right >= SCREEN_WIDTH - 10:
                    next_map = MAP_CONFIG[current_map_id]["next"]
                    if next_map:
                        run_transition(next_map, "left")

                elif player.rect.left <= 10:
                    prev_map = MAP_CONFIG[current_map_id]["prev"]
                    can_exit = True
                    
                    # pipe_nightmare_1_3 Constraint: Only Row 2, 3 allowed (Indices)
                    if current_map_id == "pipe_nightmare_1_3":
                        # Rows 2 and 3 correspond to y range [256, 512]
                        cy = player.rect.centery
                        if not (2 * 128 <= cy <= 4 * 128):
                            can_exit = False
                            player.rect.left = 10 # Block return
                    
                    # Backpack Check: 2-3 -> 2-2
                    if current_map_id == "pipe_nightmare_2_3" and prev_map == "pipe_nightmare_2_2":
                        if not any(item.get("id") == "liquid_nitrogen_core" for item in player.inventory if isinstance(item, dict)):
                            can_exit = False
                            player.rect.left = 20 # Push back
                            dialogue_system.start_dialogue(["检测到高温区域阻断。", "需要【液氮冷却核心】才能通过。"])

                    if prev_map and can_exit:
                        run_transition(prev_map, "right")

                elif player.rect.bottom >= SCREEN_HEIGHT - 10:
                    down_map = MAP_CONFIG[current_map_id].get("down")
                    can_exit = True
                    
                    # pipe_nightmare_1_3 Constraint: Only Col 2, 3 allowed (Indices)
                    if current_map_id == "pipe_nightmare_1_3":
                         # Cols 2 and 3 correspond to x range [256, 512]
                         cx = player.rect.centerx
                         if not (2 * 128 <= cx <= 4 * 128):
                             can_exit = False
                             player.rect.bottom = SCREEN_HEIGHT - 10 # Block exit

                    if down_map and can_exit:
                        run_transition(down_map, "top")
                elif player.rect.top <= 10:
                    up_map = MAP_CONFIG[current_map_id].get("up")
                    
                    # Backpack Check: 3-2 -> 2-2
                    if current_map_id == "pipe_nightmare_3_2" and up_map == "pipe_nightmare_2_2":
                         if not any(item.get("id") == "liquid_nitrogen_core" for item in player.inventory if isinstance(item, dict)):
                             up_map = None # Block transition
                             player.rect.top = 20 # Push back
                             dialogue_system.start_dialogue(["检测到高温区域阻断。", "需要【液氮冷却核心】才能通过。"])

                    if up_map:
                        run_transition(up_map, "bottom")

                # Pipe Channel Constraint
                if MAP_CONFIG[current_map_id].get("is_pipe_channel"):
                    # Force player Y between 2*TILE_SIZE and 4*TILE_SIZE
                    min_y = 2 * 128
                    max_y = 4 * 128 - player.rect.height
                    
                    if player.rect.y < min_y:
                        player.rect.y = min_y
                    elif player.rect.y > max_y:
                        player.rect.y = max_y
                elif MAP_CONFIG[current_map_id].get("is_vertical_pipe_channel"):
                    # Force player X between 2*TILE_SIZE and 4*TILE_SIZE
                    min_x = 2 * 128
                    max_x = 4 * 128 - player.rect.width
                    
                    if player.rect.x < min_x:
                        player.rect.x = min_x
                    elif player.rect.x > max_x:
                        player.rect.x = max_x
                
                # Special Transition for snow_1_3 -> base_1 (The Great Hollow)
                if current_map_id == "snow_1_3":
                    # Area: Row 2-4 (index 1-3), Col 3+ (index 2+)
                    # 128-based: x >= 2*128 (256), 128 <= y <= 4*128 (512)
                    # Let's define the rect for clarity
                    # x: 256 to end, y: 0 to SCREEN_HEIGHT (Full column)
                    hollow_rect = pygame.Rect(256, 0, SCREEN_WIDTH - 256, SCREEN_HEIGHT)
                    if player.rect.colliderect(hollow_rect):
                        confirm_dialog.set_text("确认进入大空洞？")
                        bg_surf = screen.copy()
                        if confirm_dialog.run(bg_surf):
                             run_transition("base_1", "center_left", hold_duration=1.5)
                        else:
                            # Push player left to avoid immediate re-trigger
                            # Make sure player is FULLY outside the rect (left of 256)
                            player.rect.right = 250
                            ignore_bonfire_collision = True # Just in case

                # Special Transition for pipe_nightmare_2 -> pipe_nightmare_3
                if current_map_id == "pipe_nightmare_2":
                    # Rows 4-5 (Indices 3-4), Cols 5-6 (Indices 4-5)
                    # Tile size 128
                    # x: 4*128=512, y: 3*128=384. w=256, h=256
                    pipe_rect = pygame.Rect(512, 384, 256, 256)
                    
                    if player.rect.colliderect(pipe_rect):
                        confirm_dialog.set_text("是否进入管道噩梦？")
                        bg_surf = screen.copy()
                        if confirm_dialog.run(bg_surf):
                             run_transition("pipe_nightmare_3", "left", hold_duration=1.0)
                        else:
                            # Push player left to avoid immediate re-trigger
                            # Entrance is on the right side (Cols 5-6), so pushing left is safe
                            if player.rect.right > 512:
                                player.rect.right = 500
                            ignore_bonfire_collision = True

                # Update
                if not dialogue_system.active:
                    obstacles = tile_manager.collision_rects
                    # Add props to obstacles
                    for prop in props_group:
                        obstacles.append(prop.hitbox)
                        
                    # Noise System Update
                    if hasattr(player, 'noise_level'):
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
                            player.noise_level += 2
                        
                        decay = getattr(player, 'noise_decay', 0.5)
                        player.noise_level = max(0, player.noise_level - decay)

                    player.update(obstacles, tile_manager.terminal_rects)
                    enemies_group.update(player)
                    bonfire_group.update()
                    props_group.update()
                    
                    # Collectibles Update
                    if tile_manager:
                        tile_manager.update_collectibles()
                    
                    for fg in fog_gates:
                        fg.update()
                    if fog_wall:
                        fog_wall.update()
                    
                    camera.update(player)

                    if MAP_CONFIG[current_map_id].get("is_pipe_channel") or MAP_CONFIG[current_map_id].get("is_vertical_pipe_channel"):
                        pipe_atmosphere.update()
                    
                    # Fog Gate Interaction
                    for fg in fog_gates:
                        if player.rect.colliderect(fg.rect):
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
                                
                                is_outside = player.rect.centery > fg.rect.centery
                                if is_outside:
                                    should_trigger_dialog = True
                                else:
                                    # Inside - Block (Push Up)
                                    player.rect.bottom = fg.rect.top + 5 # Slight overlap prevention
                            else:
                                # Vertical Gate
                                # Check if player is "Outside" (Right side for Right Edge)
                                is_outside = player.rect.centerx > fg.rect.centerx
                                
                                # Special Case: Base 5 Gate (x=236). Boss is at Right. Outside is Left.
                                # In Base 5, Boss is "Inside" (Right). Player comes from Left.
                                # So Outside is < 236.
                                # We need a way to distinguish "Entry Direction".
                                # Base 5 Gate Rect: (236, 512, 40, 256).
                                # Pipe 2-2 Gate Rect: (640-20, 0, 40, 640).
                                
                                if current_map_id == "base_5":
                                    # Base 5: Entry from Left (Outside)
                                    is_outside = player.rect.centerx < fg.rect.centerx
                                    if is_outside:
                                        should_trigger_dialog = True
                                    else:
                                        # Inside (Right) - Block (Push Right)
                                        player.rect.left = fg.rect.right - 5
                                else:
                                    # Pipe 2-2 (and others): Entry from Right/Bottom (Outside)
                                    # Pipe 2-2 Vertical Gate is at x=640. Boss is Left.
                                    # So Outside is Right (x > 640).
                                    is_outside = player.rect.centerx > fg.rect.centerx
                                    if is_outside:
                                        should_trigger_dialog = True
                                    else:
                                        # Inside (Left) - Block (Push Left)
                                        player.rect.right = fg.rect.left + 5
                            
                            if should_trigger_dialog:
                                 confirm_dialog.set_text("是否穿过雾门？")
                                 bg_surf = screen.copy()
                                 
                                 if confirm_dialog.run(bg_surf):
                                     fog_anim_active = True
                                     fog_anim_timer = 0
                                     
                                     if is_horizontal:
                                         if is_outside:
                                             fog_anim_direction = (0, -2)
                                         else:
                                             fog_anim_direction = (0, 2)
                                     else:
                                        if current_map_id == "base_5":
                                            if is_outside:
                                                fog_anim_direction = (2, 0)
                                            else:
                                                fog_anim_direction = (-2, 0)
                                        else:
                                            if current_map_id == "pipe_nightmare_2_2":
                                                # Explicit check for Pipe 2-2 Vertical Gate (Right side)
                                                # Outside is Right. Move Left to Enter.
                                                if is_outside:
                                                    fog_anim_direction = (-2, 0)
                                                else:
                                                    fog_anim_direction = (2, 0)
                                            else:
                                                if is_outside:
                                                    fog_anim_direction = (-2, 0)
                                                else:
                                                    fog_anim_direction = (2, 0)
                                 else:
                                    # Push back to Outside
                                    push_dist = 20
                                    if is_horizontal:
                                        player.rect.top = fg.rect.bottom + push_dist
                                    else:
                                        if current_map_id == "base_5":
                                             player.rect.right = fg.rect.left - push_dist
                                        else:
                                             player.rect.left = fg.rect.right + push_dist
                            
                    # Fog Wall Interaction (Block only)
                    if fog_wall and player.rect.colliderect(fog_wall.rect):
                         # Horizontal Wall: Check Y relative to center
                         if player.rect.centery < fog_wall.rect.centery:
                             player.rect.bottom = fog_wall.rect.top
                         else:
                             player.rect.top = fog_wall.rect.bottom

                    # Bonfire Interaction Check
                    colliding_bonfire = None
                    for b in bonfire_group:
                        if player.rect.colliderect(b.hitbox):
                            colliding_bonfire = b
                            break
                    
                    if colliding_bonfire:
                        # Activate Bonfire
                        if current_map_id not in game_state.activated_bonfires:
                            game_state.activated_bonfires.append(current_map_id)
                            print(f"Bonfire activated: {current_map_id}")
                        
                        # Rest at Bonfire (Heal + Refill Battery)
                        if not ignore_bonfire_collision:
                            player.hp = player.max_hp
                            player.battery_count = player.max_battery_count # Assume 3 is max for now or use attribute
                            # Reset killed enemies
                            game_state.temp_killed_enemies = []
                            # Reload map to respawn them
                            load_map(current_map_id, silent=True)
                            
                            # Update Last Rest Point
                            game_state.last_rest_map_id = current_map_id
                            # Use spawn_pos from config if available, else current pos (approx) or bonfire pos
                            cfg = MAP_CONFIG.get(current_map_id, {})
                            game_state.last_rest_pos = cfg.get("spawn_pos", (player.rect.x, player.rect.y))
                            
                        if not ignore_bonfire_collision:
                            bg_surf = screen.copy()
                            result = bonfire_menu.run(bg_surf)
                            
                            if result == "save":
                                save_game(player, game_state, current_map_id)
                                save_success_timer = 30 # Show "Game Saved" for 0.5 second (30 frames)
                            elif result == "teleport":
                                 # Teleport Logic
                                 destinations = []
                                 for mid, cfg in MAP_CONFIG.items():
                                     if cfg.get("has_bonfire") and mid in game_state.activated_bonfires:
                                         destinations.append({"id": mid, "name": cfg.get("name")})
                                 
                                 current_map_name = MAP_CONFIG[current_map_id].get("name")
                                 teleport_menu = TeleportMenu(screen, current_map_name, destinations)
                                 target_id = teleport_menu.run(screen.copy())
                                 
                                 if target_id:
                                     current_map_id = target_id
                                     load_map(current_map_id)
                                     update_all_volumes()
                                     spawn_pos = MAP_CONFIG[current_map_id].get("spawn_pos", (128*2, 128*2))
                                     player.rect.topleft = spawn_pos
                                     ignore_bonfire_collision = True
                            elif result == "leave":
                                ignore_bonfire_collision = True
                    else:
                        ignore_bonfire_collision = False
                    
                    # Collision Check: Player vs Enemy -> Battle
                    # Use ratio 0.6 to require closer proximity (smaller hitbox)
                    collided_enemy = pygame.sprite.spritecollideany(player, enemies_group, collided=pygame.sprite.collide_rect_ratio(0.6))
                    if collided_enemy:
                        if player.battle_cooldown <= 0:
                            current_state = STATE_BATTLE
                            battle_data = getattr(collided_enemy, 'battle_data', None)
                            battle_manager.start_battle(player, battle_data)
            
            # Custom Boundary Check for Pipe Nightmare 1-3 (Bottom Exit)
            if current_map_id == "pipe_nightmare_1_3" and player.rect.y > SCREEN_HEIGHT:
                 run_transition("pipe_nightmare_2_3", "exact_top")

            # --- Pipe Nightmare 3-2 & 3-3 Freeze Logic ---
            if current_map_id in ["pipe_nightmare_3_2", "pipe_nightmare_3_3"]:
                is_moving = player.velocity.length() > 0
                
                if is_moving or is_frozen or freeze_timer > 0:
                    freeze_timer += 1 / 60.0 # Approx dt
                    
                    if freeze_timer >= FREEZE_CYCLE:
                        freeze_timer = 0
                        is_frozen = False
                        static_frame = None
                        # Play Glitch Sound
                        if glitch_sound:
                             glitch_sound.play()
                    elif freeze_timer >= FREEZE_START and not is_frozen:
                        is_frozen = True
                        static_frame = screen.copy()
            else:
                freeze_timer = 0
                is_frozen = False
                static_frame = None

            # Draw
            if is_frozen and static_frame:
                screen.blit(static_frame, (0, 0))
                
                # Visual Interference: Random Black Blocks
                for _ in range(15):
                     w = random.randint(50, 300)
                     h = random.randint(10, 80)
                     x = random.randint(0, SCREEN_WIDTH - w)
                     y = random.randint(0, SCREEN_HEIGHT - h)
                     s = pygame.Surface((w, h))
                     s.fill((0, 0, 0))
                     s.set_alpha(random.randint(20, 60)) 
                     screen.blit(s, (x, y))
                
                # Visual Interference: Scanlines
                for i in range(0, SCREEN_HEIGHT, 8):
                     pygame.draw.line(screen, (0, 0, 0, 40), (0, i), (SCREEN_WIDTH, i))
                
                pygame.display.flip()
                clock.tick(FPS)
                continue # Skip normal draw

            screen.fill(COLOR_BG)
            
            # Draw Map
            if tile_manager:
                tile_manager.draw(screen, camera)
            
            # Draw Entities
            # Collectibles are now drawn by tile_manager.draw()
            
            for sprite in bonfire_group:
                screen.blit(sprite.image, camera.apply(sprite))
            
            for prop in props_group:
                screen.blit(prop.image, camera.apply(prop))
            
            for sprite in enemies_group:
                screen.blit(sprite.image, camera.apply(sprite))
                
            screen.blit(player.image, camera.apply(player))

            # Fog Maze (Pipe Nightmare 1-3 & 3-3)
            if current_map_id in ["pipe_nightmare_1_3", "pipe_nightmare_3_3"]:
                fog_maze.draw(screen, camera.apply(player))
                # Also draw Fog Walls (the visible obstacles)
                for fw in fog_walls: 
                    fw.update()
                    fw.draw(screen, camera)

            if MAP_CONFIG[current_map_id].get("is_pipe_channel"):
                pipe_atmosphere.draw(screen, mode="horizontal")
                pipe_atmosphere.update(mode="horizontal")
            elif MAP_CONFIG[current_map_id].get("is_vertical_pipe_channel"):
                pipe_atmosphere.draw(screen, mode="vertical")
                pipe_atmosphere.update(mode="vertical")
            
            # Pulse Atmosphere (Pipe Nightmare 3-1 & 3-3)
            if current_map_id in ["pipe_nightmare_3_1", "pipe_nightmare_3_3"]:
                speed = 0.002
                if current_map_id == "pipe_nightmare_3_3" and hasattr(player, 'noise_level'):
                     threshold = getattr(player, 'noise_threshold', 100)
                     if player.noise_level > threshold:
                         speed = 0.02 # Faster flicker
                
                pulse_atmosphere.update(speed=speed)
                pulse_atmosphere.draw(screen)
            
            if fog_wall:
                fog_wall.update()
                fog_wall.draw(screen, camera)

            # Draw Fog Gates (List)
            for fg in fog_gates:
                fg.update()
                fg.draw(screen, camera)

            # Draw Fog Walls (List) - Already drawn in pipe_nightmare section, but let's consolidate if possible
            # Check lines 1864-1865: "Also draw Fog Walls (the visible obstacles)"
            # It only draws, doesn't update. Let's add update there or move it here.
            # To be safe and avoid double draw, I will stick to the existing structure for fog_walls in pipe_nightmare_1_3
            # but I should ensure they are updated.

            
            # Particles (Data Dust)
            for p in particles:
                p.update()
                p.draw(screen)

            # UI Overlay
            try:
                font = get_font(24)
            except:
                font = pygame.font.Font(None, 24)
                
            hp_text = font.render(f"HP: {player.hp}/{player.max_hp}", True, (255, 255, 255))
            screen.blit(hp_text, (10, 10))
            
            area_title.update()
            area_title.draw()
            
            dialogue_system.draw(screen)

            # Save Success Message
            if save_success_timer > 0:
                save_msg = font.render("存档已保存", True, (0, 255, 0))
                screen.blit(save_msg, (50, SCREEN_HEIGHT - 50))
            
            pygame.display.flip()
            clock.tick(FPS)

        # --- State: Battle ---
        elif current_state == STATE_BATTLE:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    battle_manager.handle_input(event)
            
            battle_manager.update()
            
            screen.fill((0, 0, 0)) # Battle BG
            battle_manager.draw()
            pygame.display.flip()
            clock.tick(FPS)
            
            if not battle_manager.running:
                if battle_manager.battle_result == "lost":
                    current_state = STATE_GAMEOVER
                    gameover_timer = pygame.time.get_ticks()
                else:
                    current_state = STATE_OVERWORLD
                    
                    # Win or Flee or Spare
                    if battle_manager.battle_result == "win" or battle_manager.battle_result == "spare":
                        # Handle Enemy Persistence
                        # Check if Boss
                        boss_id = battle_manager.enemy_data.get("boss_id")
                        if boss_id:
                            if boss_id not in game_state.cleared_bosses:
                                game_state.cleared_bosses.append(boss_id)
                                print(f"Boss Cleared: {boss_id}")
                                # Optional: Auto-save on boss clear?
                                # save_game(player, game_state, current_map_id)
                        
                        # Check if Minion (Standard Respawnable Enemy)
                        enemy_id = battle_manager.enemy_data.get("id")
                        if enemy_id:
                            # Only add to temp_killed if NOT a boss (though logic allows overlap if needed)
                            # Assuming bosses also have unique IDs but we track them via cleared_bosses for permadeath
                            if not boss_id:
                                if enemy_id not in game_state.temp_killed_enemies:
                                    game_state.temp_killed_enemies.append(enemy_id)
                        
                        # Remove from current group
                        for e in enemies_group:
                            # Match by ID or Boss ID
                            e_data = getattr(e, 'battle_data', {})
                            if (enemy_id and e_data.get('id') == enemy_id) or \
                               (boss_id and e_data.get('boss_id') == boss_id):
                                e.kill()
                                break
                                    
                        boss_id = battle_manager.enemy_data.get("boss_id")
                        if boss_id:
                            if boss_id not in game_state.cleared_bosses:
                                game_state.cleared_bosses.append(boss_id)
                            
                            if boss_id == "base_5_boss":
                                fog_wall = None
                                # Also clear list if we migrate base_5 to use list in future
                                fog_gates = [] 
                                for enemy in enemies_group:
                                    if getattr(enemy, 'battle_data', {}).get('boss_id') == boss_id:
                                        enemy.kill()
                                        break
                            
                            elif boss_id == "pipe_2_2_boss":
                                fog_gates = [] # Clear fog gates
                                for enemy in enemies_group:
                                    if getattr(enemy, 'battle_data', {}).get('boss_id') == boss_id:
                                        enemy.kill()
                                        break
                    else:
                        # Fleeing
                        player.rect.y += 50

                    player.battle_cooldown = 180
                    load_bgm("audio/bgm/city ruins.mp3")
                    current_bgm = "audio/bgm/city ruins.mp3"

        # --- State: GameOver ---
        elif current_state == STATE_GAMEOVER:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            screen.fill((0, 0, 0))
            
            try:
                font_large = get_font(72)
            except:
                font_large = pygame.font.Font(None, 72)
            
            text = font_large.render("YOU DIED", True, (200, 0, 0))
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(text, text_rect)
            
            pygame.display.flip()
            clock.tick(FPS)
            
            if pygame.time.get_ticks() - gameover_timer > 3000: # 3 seconds
                # Respawn Logic
                print(f"Respawning at {game_state.last_rest_map_id}")
                game_state.temp_killed_enemies = []
                
                current_map_id = game_state.last_rest_map_id
                load_map(current_map_id)
                player.rect.topleft = game_state.last_rest_pos
                
                player.hp = player.max_hp
                player.battery_count = player.max_battery_count
                
                area_title.show()
                current_state = STATE_OVERWORLD
                
                load_bgm("audio/bgm/city ruins.mp3")
                current_bgm = "audio/bgm/city ruins.mp3"

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
