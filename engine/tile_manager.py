import pygame
import os
import re
from engine.utils import resource_path
from engine.config import RENDER_TILE_SIZE, GAME_MAP
from entities.items import Collectible

class TileManager:
    # 定义障碍物瓦片列表
    # 按照 6x6 规格：上方两行 (Indices 0-11) 为背景/障碍物
    # 剩下的 4 行 (Indices 12-35) 为可通行区域
    OBSTACLE_TILES = list(range(12))

    def __init__(self, tileset_folder, extra_obstacles=None, open_top_rows=False, is_pipe_channel=False, is_vertical_pipe_channel=False, rotation=0):
        self.tiles = []
        self.map_data = GAME_MAP
        self.collision_rects = []
        self.terminal_rects = []
        self.tile_width = RENDER_TILE_SIZE
        self.tile_height = RENDER_TILE_SIZE
        self.rotation = rotation
        self.width = len(self.map_data[0]) * self.tile_width if self.map_data else 0
        self.height = len(self.map_data) * self.tile_height if self.map_data else 0
        self.collectibles = pygame.sprite.Group()
        self.load_tiles(tileset_folder)
        
        # 构建碰撞体 (基于逻辑地图 game_map，此时存储的是瓦片索引)
        for row_index, row in enumerate(self.map_data):
            for col_index, map_id in enumerate(row):
                rect = pygame.Rect(col_index * self.tile_width, row_index * self.tile_height, self.tile_width, self.tile_height)
                
                # 使用 OBSTACLE_TILES 列表判定障碍物
                # 如果 open_top_rows 为 True，则忽略默认的障碍物判定（即前两行变为可通行）
                if not open_top_rows and map_id in self.OBSTACLE_TILES:
                    self.collision_rects.append(rect)
                
                # Pipe Channel Logic: Force top 2 and bottom 2 rows as obstacles
                if is_pipe_channel:
                    # Rows 0, 1 (Top) and 4, 5 (Bottom)
                    if row_index in [0, 1, 4, 5]:
                        # Avoid duplicates if already added
                        if rect not in self.collision_rects:
                            self.collision_rects.append(rect)
                            
                # Vertical Pipe Channel Logic: Force left 2 and right 2 columns as obstacles
                if is_vertical_pipe_channel:
                    # Cols 0, 1 (Left) and 4, 5 (Right)
                    if col_index in [0, 1, 4, 5]:
                         if rect not in self.collision_rects:
                            self.collision_rects.append(rect)
                
                # Extra Obstacles (Coordinate based)
                if extra_obstacles and (col_index, row_index) in extra_obstacles:
                     self.collision_rects.append(rect)
                
                # 终端判定 (例如 tile_8 是控制台)
                if map_id == 8:
                    self.terminal_rects.append(rect)

    def load_tiles(self, folder_path):
        if not os.path.exists(folder_path):
            print(f"Error: {folder_path} not found.")
            return

        print(f"Loading tiles from {folder_path}...")
        
        # 获取所有图片文件
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp')
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
        
        # 自然排序
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower()
                    for text in re.split('([0-9]+)', s)]
        
        files.sort(key=natural_sort_key)
        
        for f in files:
            try:
                path = os.path.join(folder_path, f)
                image = pygame.image.load(path).convert()
                image.set_colorkey((255, 255, 255))
                # 强制缩放
                image = pygame.transform.scale(image, (self.tile_width, self.tile_height))
                
                # Apply Rotation if needed
                if self.rotation != 0:
                    image = pygame.transform.rotate(image, self.rotation)
                
                self.tiles.append(image)
            except Exception as e:
                print(f"Failed to load {f}: {e}")
                
        print(f"Loaded {len(self.tiles)} tiles.")

    def add_collectible(self, x, y, anim_folder_name, item_data=None, sound_file=None, item_id=None, scale=1.0):
        """Add a collectible item to the map."""
        collectible = Collectible(x, y, anim_folder_name, sound_file=sound_file, item_data=item_data, item_id=item_id, scale=scale)
        self.collectibles.add(collectible)

    def update_collectibles(self):
        """Update state of all collectibles."""
        self.collectibles.update()

    def try_collect(self, player, game_state):
        """Check if player interacts with any items (Manual Collection)."""
        hits = pygame.sprite.spritecollide(player, self.collectibles, False)
        for collectible in hits:
            if not collectible.collected:
                collectible.interact()
                
                # Persistence
                if collectible.item_id:
                    game_state.collected_items.append(collectible.item_id)
                
                if collectible.item_data:
                    player.inventory.append(collectible.item_data)
                    player.has_new_item = True
                    
                    # Special handling for Battery type to update count
                    if collectible.item_data.get('type') == 'battery':
                        player.battery_count += collectible.item_data.get('value', 1)
                        if player.battery_count > player.max_battery_count:
                            player.battery_count = player.max_battery_count

    def draw(self, surface, camera=None):
        # 暴力平铺 6x6
        offset_x = camera.camera.x if camera else 0
        offset_y = camera.camera.y if camera else 0
        
        for row in range(6):
            for col in range(6):
                index = row * 6 + col
                # 防止越界
                if index < len(self.tiles):
                    x = col * self.tile_width + offset_x
                    y = row * self.tile_height + offset_y
                    surface.blit(self.tiles[index], (x, y))

        # Draw collectibles
        for collectible in self.collectibles:
            # Calculate screen position based on camera offset
            # Collectible.rect is in world coordinates
            screen_x = collectible.rect.x + offset_x
            screen_y = collectible.rect.y + offset_y
            
            if collectible.image:
                surface.blit(collectible.image, (screen_x, screen_y))
