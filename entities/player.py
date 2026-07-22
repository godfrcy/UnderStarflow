import pygame
import os
from engine.utils import resource_path
from engine.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_HEIGHT, 
    PLAYER_ANIM_SPEED, PLAYER_SPEED, PLAYER_SLICE_OFFSET_X
)

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        # 动画相关状态
        self.animations = {
            'left': [],
            'right': [],
            'up': [],
            'down': [],
            'idle_front': [], # 保留之前的正面图作为待机
            'idle_back': []   # 保留之前的背面图作为待机
        }
        self.current_anim = 'idle_front'
        self.frame_index = 0
        self.animation_speed = PLAYER_ANIM_SPEED # 动画播放速度
        self.last_update_time = pygame.time.get_ticks()

        # 尺寸设置
        self.base_height = PLAYER_HEIGHT # 约 96 像素
        
        # Hitbox (Circular for Battle)
        self.hitbox_radius = 4 # 核心判定半径
        self.hitbox_center = (0, 0)
        
        # Inventory System
        self.inventory = [] # List of item dictionaries
        self.has_new_item = False # Notification flag for UI
        self.exp = 0
        self.level = 1
        self.max_exp = 100
        self.attack = 10
        self.battery_count = 3
        
        # Noise System (for Pipe Nightmare 3-3)
        self.noise_level = 0
        self.noise_threshold = 100
        self.noise_decay = 0.5
        

        
        # 确保 animations 字典有基础内容，防止加载失败后 Crash
        # 先填充占位符
        fallback_surface = pygame.Surface((self.base_height // 2, self.base_height))
        fallback_surface.fill((255, 0, 255)) # 洋红色，显眼
        for key in self.animations:
            self.animations[key] = [fallback_surface]

        try:
            # 1. 加载 Sprite Sheet (2047x1050, 1x4 布局)
            sheet_path = resource_path("characters/player/anthe_sheet.png")
            
            sheet = pygame.image.load(sheet_path).convert_alpha()
            sheet_width = sheet.get_width()
            sheet_height = sheet.get_height()
            
            # 计算每帧尺寸 (1行4列)
            frame_width = sheet_width // 4
            frame_height = sheet_height # 现在是一行，所以高度即为图片高度
            
            # 动画帧的目标渲染尺寸：强制为 base_height
            anim_target_height = self.base_height
            scale_factor = anim_target_height / frame_height
            anim_target_width = int(frame_width * scale_factor)

            # 切分并缩放右侧行走动画 (1行4列)
            # 用户反馈图1有一部分像素被切割到图2中，说明切片太靠左，需要向右偏移
            slice_offset_x = PLAYER_SLICE_OFFSET_X # 尝试向右偏移 30 像素
            
            temp_right_anims = []
            for col in range(4):
                current_frame_width = frame_width
                
                # 特殊处理：第三帧 (col=2) 稍微收缩右边界，防止切入第四帧
                if col == 2:
                    current_frame_width -= 10 # 减少 10 像素宽度
                
                rect = pygame.Rect(col * frame_width + slice_offset_x, 0, current_frame_width, frame_height)
                
                # 确保不超出图片边界
                if rect.right > sheet_width:
                    rect.width = sheet_width - rect.x
                
                image = sheet.subsurface(rect)
                # 严禁使用 smoothscale，改回 scale
                scaled_image = pygame.transform.scale(image, (anim_target_width, anim_target_height))
                temp_right_anims.append(scaled_image)
            
            # 如果加载成功，覆盖默认值
            if temp_right_anims:
                self.animations['right'] = temp_right_anims
            
            # 生成左侧行走动画 (镜像翻转右侧动画)
            temp_left_anims = []
            for img in self.animations['right']:
                # flip(surface, x_bool, y_bool) -> True表示翻转
                mirrored_img = pygame.transform.flip(img, True, False)
                temp_left_anims.append(mirrored_img)
            self.animations['left'] = temp_left_anims

            # 2. 加载 W/S 键的垂直行走动画
            # 使用 ahead and recoil.png (4x2 Sheet)
            # Row 0 (Top): Down (S) - 4 Frames
            # Row 1 (Bottom): Up (W) - 4 Frames
            
            try:
                ud_sheet_path = resource_path("characters/player/ahead and recoil.png")
                if os.path.exists(ud_sheet_path):
                    ud_sheet = pygame.image.load(ud_sheet_path).convert_alpha()
                    ud_w = ud_sheet.get_width()
                    ud_h = ud_sheet.get_height()
                    
                    frame_w = ud_w // 4
                    frame_h = ud_h // 2
                    
                    target_h = self.base_height
                    scale = target_h / frame_h
                    target_w = int(frame_w * scale)
                    
                    # Row 0: Down (S)
                    down_frames = []
                    for col in range(4):
                        rect = pygame.Rect(col * frame_w, 0, frame_w, frame_h)
                        img = ud_sheet.subsurface(rect)
                        scaled = pygame.transform.scale(img, (target_w, target_h))
                        down_frames.append(scaled)
                    self.animations['down'] = down_frames
                    self.animations['idle_front'] = [down_frames[0]]
                    
                    # Row 1: Up (W)
                    up_frames = []
                    for col in range(4):
                        rect = pygame.Rect(col * frame_w, frame_h, frame_w, frame_h)
                        img = ud_sheet.subsurface(rect)
                        scaled = pygame.transform.scale(img, (target_w, target_h))
                        up_frames.append(scaled)
                    self.animations['up'] = up_frames
                    
                    print("Loaded ahead and recoil.png for Up/Down animations.")
                    
                    # 3. Load specific idle images (Anthe Front/Back)
                    # As requested: When stopping after W (up), show anthe_back.png
                    # When stopping after S (down), show anthe_front.png
                    
                    # Helper for single image loading
                    def load_single_idle(filename):
                        path = resource_path(filename)
                        if os.path.exists(path):
                            img = pygame.image.load(path).convert_alpha()
                            scale = self.base_height / img.get_height()
                            width = int(img.get_width() * scale)
                            return pygame.transform.scale(img, (width, self.base_height))
                        return None

                    idle_front_img = load_single_idle("characters/player/anthe_front.png")
                    if idle_front_img:
                        self.animations['idle_front'] = [idle_front_img]
                    else:
                        # Fallback to first frame of down animation if file missing
                        self.animations['idle_front'] = [down_frames[0]]
                        
                    idle_back_img = load_single_idle("characters/player/anthe_back.png")
                    if idle_back_img:
                        self.animations['idle_back'] = [idle_back_img]
                    else:
                        # Fallback to first frame of up animation if file missing
                        self.animations['idle_back'] = [up_frames[0]]

                else:
                    raise FileNotFoundError("ahead and recoil.png not found")

            except Exception as e:
                print(f"Vertical animation load failed ({e}), falling back to legacy assets.")
                # Fallback: Legacy Logic
                def load_and_scale(filename):
                    full_path = resource_path(filename)
                    if not os.path.exists(full_path):
                        return fallback_surface
                    img = pygame.image.load(full_path).convert_alpha()
                    scale = self.base_height / img.get_height()
                    width = int(img.get_width() * scale)
                    return pygame.transform.scale(img, (width, self.base_height))

                # Up 动画
                up_frame1 = load_and_scale("characters/player/anthe_forward.png")
                self.animations['up'] = [up_frame1]
                self.animations['idle_back'] = [load_and_scale("characters/player/anthe_back.png")]

                # Down 动画
                down_frame1 = load_and_scale("characters/player/anthe_front.png")
                down_frame2 = load_and_scale("characters/player/anthe_front_walk.png")
                self.animations['down'] = [down_frame1, down_frame2]
                self.animations['idle_front'] = [down_frame1]

        except Exception as e:
            print(f"警告：未找到角色图片或加载出错，使用方块代替。错误: {e}")
            # 保持默认占位符，不 crash
            pass

        # 初始图片
        self.image = self.animations[self.current_anim][0]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = PLAYER_SPEED
        self.facing_back = False
        self.velocity = pygame.math.Vector2(0, 0)
        
        # 战斗属性
        self.hp = 20
        self.max_hp = 20
        
        # 交互系统
        self.interaction_cooldown = 0
        self.battle_cooldown = 0 # 战斗冷却 (逃跑/宽恕后)
        self.on_interact = None
        
        # 物品栏
        self.inventory = [] # 初始物品为空
        self.battery_count = 3
        self.max_battery_count = 3

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0:
            self.hp = 0

    def update(self, collision_rects, terminal_rects=None):
        # 更新圆形判定中心
        self.hitbox_center = self.rect.center
        
        # 处理键盘输入
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0

        # 移动逻辑：支持 WASD 和 方向键
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -self.speed
            self.facing_back = True
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = self.speed
            self.facing_back = False
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx = self.speed

        # Update Velocity
        self.velocity.x = dx
        self.velocity.y = dy

        # --- 动画状态机更新 ---
        current_time = pygame.time.get_ticks()
        is_moving_horizontal = dx != 0
        
        # 1. 确定当前应该播放的动画类型
        new_anim = self.current_anim
        
        # 优先响应移动方向
        if dx < 0:
            new_anim = 'left'
        elif dx > 0:
            new_anim = 'right'
        elif dy < 0:
            new_anim = 'up'
        elif dy > 0:
            new_anim = 'down'
        else:
            # 停止移动时，强制使用正面待机状态
            new_anim = 'idle_front'

        # 2. 切换动画状态
        if new_anim != self.current_anim:
            self.current_anim = new_anim
            self.frame_index = 0 # 重置帧索引
            self.last_update_time = current_time
        
        # 3. 播放动画 (帧更新)
        # 只要在移动，或者当前动画有多帧（例如待机动画有多帧时），就进行更新
        is_moving = dx != 0 or dy != 0
        if is_moving or len(self.animations[self.current_anim]) > 1:
            if current_time - self.last_update_time > self.animation_speed * 1000:
                self.frame_index = (self.frame_index + 1) % len(self.animations[self.current_anim])
                self.last_update_time = current_time
                self.image = self.animations[self.current_anim][self.frame_index]
        else:
            # 静态图直接设置
            self.image = self.animations[self.current_anim][0]

        # --- 物理移动与碰撞检测 (Split Axis) ---
        
        # 1. X 轴移动
        self.rect.x += dx
        # 屏幕边界拦截 X (放宽右侧边界，允许稍微出界以覆盖地图空隙)
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width + 32))
        # 障碍物碰撞 X
        for block in collision_rects:
            if self.rect.colliderect(block):
                if dx > 0: # 向右撞
                    self.rect.right = block.left
                elif dx < 0: # 向左撞
                    self.rect.left = block.right
        
        # 2. Y 轴移动
        self.rect.y += dy
        # 屏幕边界拦截 Y
        self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - self.rect.height))
        # 障碍物碰撞 Y
        for block in collision_rects:
            if self.rect.colliderect(block):
                if dy > 0: # 向下撞
                    self.rect.bottom = block.top
                elif dy < 0: # 向上撞
                    self.rect.top = block.bottom

        # --- 交互检测 (Player.update 中) ---
        current_time = pygame.time.get_ticks()
        
        # 战斗冷却更新
        if self.battle_cooldown > 0:
            self.battle_cooldown -= 1
            
        if terminal_rects:
            if current_time > self.interaction_cooldown:
                # 检查是否与任何终端接触
                for term in terminal_rects:
                    # 支持字典结构 {'rect': Rect, 'callback': func} 或纯 Rect
                    if isinstance(term, dict):
                        term_rect = term['rect']
                        callback = term.get('callback', self.on_interact)
                    else:
                        term_rect = term
                        callback = self.on_interact

                    # 使用极其严格的判定范围
                    interaction_zone = term_rect.inflate(0, 0) # 严格贴合
                    
                    if self.rect.colliderect(interaction_zone):
                        # 如果处于战斗冷却中，则不触发
                        if self.battle_cooldown > 0:
                            break
                            
                        # 触发交互 (阻塞式调用)
                        if callback:
                            callback()
                        # 交互结束后，重置冷却时间
                        self.interaction_cooldown = pygame.time.get_ticks() + 3000 
                        break

    def get_hitbox(self):
        return self.rect

    def gain_exp(self, amount):
        self.exp += amount
        # Check for level up (only for levels < 10)
        while self.level < 10 and self.exp >= self.max_exp:
            self.exp -= self.max_exp
            self.level_up()
            
    def level_up(self):
        self.level += 1
        self.max_hp += 10
        self.attack += 10
        self.hp = self.max_hp # Restore HP on level up
        print(f"Level Up! Now Level {self.level}. HP: {self.max_hp}, ATK: {self.attack}")

    def consolidate_inventory(self):
        """
        Merges duplicate items in the inventory.
        Should be called after loading a save file or whenever inventory might be messy.
        """
        new_inventory = []
        for item in self.inventory:
            # Check if this item is already in new_inventory
            found = False
            for existing_item in new_inventory:
                if existing_item.get("name") == item.get("name"):
                    # Merge count
                    existing_item["count"] = existing_item.get("count", 1) + item.get("count", 1)
                    found = True
                    break
            
            if not found:
                # Add as new entry, ensure count exists
                if "count" not in item:
                    item["count"] = 1
                new_inventory.append(item)
        
        self.inventory = new_inventory

    def add_item(self, new_item):
        """
        Add an item to the inventory, stacking if it already exists.
        new_item: dict with 'name', 'type', 'description', etc.
        """
        # Check if item already exists
        for item in self.inventory:
            if item.get("name") == new_item.get("name"):
                # Stackable logic
                # Ensure 'count' exists in both
                current_count = item.get("count", 1)
                new_count = new_item.get("count", 1)
                item["count"] = current_count + new_count
                self.has_new_item = True
                return
        
        # If not exists, ensure it has a count of 1 (if not specified)
        if "count" not in new_item:
            new_item["count"] = 1
            
        self.inventory.append(new_item)
        self.has_new_item = True

    def remove_item(self, item_name, count=1):
        """
        Remove item(s) from inventory.
        Returns True if successful, False if not found or insufficient count.
        """
        for i, item in enumerate(self.inventory):
            if item.get("name") == item_name:
                current_count = item.get("count", 1)
                if current_count >= count:
                    item["count"] = current_count - count
                    if item["count"] <= 0:
                        self.inventory.pop(i)
                    return True
        return False
