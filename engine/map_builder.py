import pygame

from engine.enemy_data import BATTLE_DATA, ABANDONED_ROBOT_DATA, ABANDONED_ROBOT_MK2_DATA, TWIN_DANCER_DATA, UFO_DATA
from entities.enemies import OverworldEnemy, Bonfire, FailureEnemy, TwinDancer
from entities.props import Prop
from ui.effects import DataDust, FogGate, FogWall


def spawn_map_content(map_id, config, extra_obstacles, game_state, tile_manager,
                      enemies_group, bonfire_group, props_group, particles,
                      fog_wall=None, fog_walls=None):
    """按 map_id 生成雾门/雾墙、敌人、道具、收集物（原 main.load_map 内联逻辑）。"""
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
        # Single-file spritesheet (4x4 grid) from assetsDB
        enemy_id = "snow_1_2_variable"
        if enemy_id not in game_state.temp_killed_enemies:
            # Point to the FILE, not a folder. OverworldEnemy now handles files.
            # 与战斗动图同步弃用瑕疵帧
            enemy = OverworldEnemy(128 * 4, 128 * 2, "characters/enemies/berserk_variable/berserk_variable.png", "variable", is_grid=True, skip_frames=BATTLE_DATA["variable"].get("skip_frames", []))
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
            tile_manager.add_collectible(128 * 2, 128 * 5, "items/battery", item_data, "audio/bgm/new_items.wav", item_id=item_id, scale=0.5)

    elif map_id == "pipe_nightmare_1":
        # 暴走变量_激光 at 5,5 (Restored Asset & Corrected Pos)
        enemy_id_1 = "pipe_nightmare_1_laser"
        if enemy_id_1 not in game_state.temp_killed_enemies:
            # Restore to previous asset
            enemy = OverworldEnemy(128 * 5, 128 * 5, "characters/enemies/variable_laser/variable_laser_transparent.png", "variable_laser", is_grid=True)
            enemy.battle_data = dict(BATTLE_DATA["berserk_laser"])
            enemies_group.add(enemy)

        # 暴走变量_跳跃 at 3,3 (Restored Pos & Removed Flip)
        enemy_id_2 = "pipe_nightmare_1_jump"
        if enemy_id_2 not in game_state.temp_killed_enemies:
            # Use transparent asset, NO flip correction
            enemy = OverworldEnemy(128 * 3, 128 * 3, "characters/enemies/variable_jump/variable_jump_transparent.png", "variable_jump", is_grid=True)
            enemy.battle_data = dict(BATTLE_DATA["berserk_jump"])
            enemies_group.add(enemy)

        # 紧急保险丝：管道噩梦1 左下角，被动锁血一次（濒死时熔断保住 1 点生命）
        item_id = "pipe_1_emergency_fuse"
        if item_id not in game_state.collected_items:
            item_data = {
                "id": "emergency_fuse",
                "name": "紧急保险丝",
                "type": "key_item",
                "description": "濒死时自动熔断，锁住 1 点生命，保住一次性命。",
            }
            tile_manager.add_collectible(128 * 2, 128 * 3, "items/battery", item_data, "audio/bgm/new_items.wav", item_id=item_id, scale=0.5)

    elif map_id == "pipe_nightmare_3_3":
         # Use same Fog Wall logic as 1-3 if needed
         if extra_obstacles:
             fog_walls = []
             for (col, row) in extra_obstacles:
                 fw = FogWall(pygame.Rect(col * 128, row * 128, 128, 128))
                 fog_walls.append(fw)

         # Spawn FailureEnemy（击败鬼武士后会从这里消失，转移到上升管道3）
         if "failure_enemy_01" not in game_state.temp_killed_enemies and "pipe_2_2_boss" not in game_state.cleared_bosses:
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

    elif map_id == "pipe_ascent_1":
        # 电磁脉冲（光点）——拾取后在战斗中使用，瓦解失败之作的秒杀机制
        item_id = "emp_pulse"
        if item_id not in game_state.collected_items:
            item_data = {
                "id": "emp_pulse",
                "name": "电磁脉冲",
                "type": "consumable",
                "description": "释放一次电磁脉冲，瓦解失败之作的秒杀机制。",
            }
            tile_manager.add_collectible(128 * 3, 128 * 2, "items/battery", item_data, "audio/bgm/new_items.wav", item_id=item_id, scale=0.5)

    elif map_id == "pipe_ascent_3":
        # 击败鬼武士后，失败之作从3-3转移到这里（最左边，缓慢向右漂移，把守通往地表的路）
        if "pipe_2_2_boss" in game_state.cleared_bosses and "failure_enemy_01" not in game_state.temp_killed_enemies:
            enemy = FailureEnemy(64, 128 * 3, slow_right_drift=True) # 最左边，横向管道中央
            enemy.battle_data = dict(BATTLE_DATA["failure"])
            enemies_group.add(enemy)

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

    elif map_id == "pipe_nightmare_3_1":
        # 废弃机器人MK2：管道噩梦3-1 加强版废弃机体，16 帧全用，动画放慢 60%
        enemy_id = "pipe_nightmare_3_1_robot_mk2"
        if enemy_id not in game_state.temp_killed_enemies:
            enemy = OverworldEnemy(128 * 3, 128 * 3, "characters/enemies/abandoned_robot_mk2", "abandoned_robot_mk2", is_grid=True)
            enemy.ANIM_SPEED = 10  # 放慢 60%（6 → 9.6 ≈ 10）
            # 固定在地图最下面两行转圈式徘徊（整体上移 20px，避免贴图底贴边框），不主动追击玩家
            # 巡逻路线整体左移一列（128px），让最左边也能走到
            enemy.set_patrol_rect(min_x=0, min_y=492, max_x=512, max_y=620, speed=2.5)
            enemy.battle_data = dict(ABANDONED_ROBOT_MK2_DATA, id=enemy_id)
            enemies_group.add(enemy)

        # UFO：管道噩梦3-1 偏右上角飞行器，原地悬浮（16 帧动画），体积 64→80（放大 25%）
        ufo_id = "pipe_nightmare_3_1_ufo"
        if ufo_id not in game_state.temp_killed_enemies:
            ufo = OverworldEnemy(128 * 5, 128 * 1, "characters/enemies/ufo", "ufo", is_grid=True, custom_size=(80, 80))
            ufo.battle_data = dict(UFO_DATA, id=ufo_id)
            enemies_group.add(ufo)

        # 纳米修复液(小)：管道噩梦3-1 左侧放置一枚
        item_id = "pipe_3_1_nano_repair_01"
        if item_id not in game_state.collected_items:
            item_data = {
                "id": "nano_repair_small",
                "name": "纳米修复液(小)",
                "type": "consumable",
                "description": "纳米修复液。使用后每回合回复5点生命值，持续3回合。",
            }
            tile_manager.add_collectible(128 * 1, 128 * 2, "items/battery", item_data, "audio/bgm/new_items.wav", item_id=item_id, scale=0.5)

    elif map_id == "pipe_nightmare_3_2":
        # 双生舞怜（boss）：屏幕偏左下角，只向右跑 1.5s 再折返回原位，不主动追击；击败后不再刷新
        enemy_id = "pipe_nightmare_3_2_twin_dancer"
        if "pipe_3_2_boss" not in game_state.cleared_bosses:
            enemy = TwinDancer(128, 576)  # 中心 (128, 576)：偏左下角
            enemy.battle_data = dict(TWIN_DANCER_DATA, id=enemy_id)
            enemies_group.add(enemy)

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

    elif map_id == "base_1":
        # 归航信标：基地1-1 右下方，关键道具（无限使用），传送到任意已激活的篝火
        item_id = "base_1_homing_beacon"
        if item_id not in game_state.collected_items:
            item_data = {
                "id": "homing_beacon",
                "name": "归航信标",
                "type": "key_item",
                "description": "发出归航信号，将你传送到任意已激活的篝火。无限使用。",
            }
            tile_manager.add_collectible(128 * 4, 128 * 5, "items/battery", item_data, "audio/bgm/new_items.wav", item_id=item_id, scale=0.5)

    elif map_id == "base_2":
        # Machine Soldier (机凯种)
        # Center of map (approx 128*3, 128*3)
        enemy_id = "base_2_machine"
        if enemy_id not in game_state.temp_killed_enemies:
            # 与战斗动图同步弃用瑕疵帧
            enemy = OverworldEnemy(128 * 3, 128 * 3, "characters/enemies/machine_soldier", "jikaizhong", is_grid=True, skip_frames=BATTLE_DATA["machine_soldier"].get("skip_frames", []))
            enemy.battle_data = dict(BATTLE_DATA["machine_soldier"])
            enemies_group.add(enemy)

    elif map_id == "base_3":
        # Admin (Rebel Leader / 义军)
        # Center of map (approx 128*3, 128*3)
        # Use rebel_leader assets
        enemy_id = "base_3_admin"
        if enemy_id not in game_state.temp_killed_enemies:
            # 弃用站立动画中的瑕疵帧，不删除图片
            enemy = OverworldEnemy(128 * 3, 128 * 3, "characters/enemies/rebel_leader", "rebel_leader", is_grid=True, skip_idle_frames=[6])
            enemy.ANIM_SPEED = 12 # Slow down animation
            # Rebel Exclusive: Enable Chase Logic
            enemy.can_chase = True
            enemy.vision_range = 300
            enemy.chase_speed = 2.5   # slow, dodgeable chase (original feel)
            enemy.burst_speed = 6.0   # lunge speed once very close
            enemy.burst_range = 80    # center-distance (px) where she bursts; > collision range (57-70)
            enemy.battle_data = dict(BATTLE_DATA["admin"])
            enemies_group.add(enemy)

    elif map_id == "base_4":
        # 义军士兵（原男义军）：基地深层唯一敌人，左右巡逻 + 靠近追逐（义军见机凯种就杀）
        enemy_id = "base_4_rebel_soldier"
        if enemy_id not in game_state.temp_killed_enemies:
            enemy = OverworldEnemy(
                128 * 3, 128 * 4,
                "characters/enemies/rebel_soldier", "rebel_soldier",
                is_grid=True,
                skip_frames=BATTLE_DATA["rebel_soldier"].get("skip_frames", []),
                custom_size=(147, 147)  # 放大 15%（原 128x128）
            )
            enemy.set_wander_behavior(min_x=128, max_x=621, speed=1.0)  # 621 = 768 - 147，避免贴图越界
            enemy.can_chase = True
            enemy.vision_range = 300
            enemy.chase_speed = 2.0
            enemy.ANIM_SPEED = 12  # 动画再慢 50%（帧间隔 8 → 12，即原始 6 翻倍）
            # 碰撞箱「缩水偏右」特化：left 缩 55（裁掉左侧留白+部分身体），right 缩 37，上下各缩。
            # 想更偏右 → 加大 left；想右边更贴 → 加大 right。
            enemy.collision_inset = (55, 12, 37, 5)
            enemy.battle_data = dict(BATTLE_DATA["rebel_soldier"])
            enemies_group.add(enemy)

        # 纳米修复液(小)：基地深层放置一枚，战斗中使用后每回合回复5点生命值，持续3回合
        item_id = "base_4_nano_repair_01"
        if item_id not in game_state.collected_items:
            item_data = {
                "id": "nano_repair_small",
                "name": "纳米修复液(小)",
                "type": "consumable",
                "description": "纳米修复液。使用后每回合回复5点生命值，持续3回合。",
            }
            tile_manager.add_collectible(128 * 2, 128 * 3, "items/battery", item_data, "audio/bgm/new_items.wav", item_id=item_id, scale=0.5)

    return fog_gates, fog_wall, fog_walls
