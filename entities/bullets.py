import pygame
import math
import random
from engine.config import PLASMA_BLADE_DAMAGE

class Bullet:
    def __init__(self, rect, vx, vy, color=(255, 255, 255), b_type="normal", active_color=None):
        self.rect = rect
        self.vx = vx
        self.vy = vy
        self.color = color
        self.active_color = active_color
        self.type = b_type # "normal", "laser", "cube"
        self.timer = 0
        self.warning_duration = 60 if b_type == "laser" else 0
        self.damaging = True if b_type != "laser" else False
        self.damage = 1 # 默认伤害
        
        # Float position for smooth movement
        self.pos_x = float(rect.x)
        self.pos_y = float(rect.y)
        
        # Circular Collision
        self.radius = max(rect.width, rect.height) / 2 # Default to half of max dimension
            
    def update(self, target_rect=None, battle_box=None):
        self.timer += 1
        
        if self.type == "laser":
            if self.timer < self.warning_duration:
                self.damaging = False
                # Warning phase
                self.pos_x += self.vx
                self.pos_y += self.vy
                self.rect.x = int(self.pos_x)
                self.rect.y = int(self.pos_y)
            else:
                self.damaging = True
                if self.active_color:
                    self.color = self.active_color
                else:
                    self.color = (0, 191, 255) # Deep Sky Blue
                
                # 如果有初速度，则按速度移动 (Moving Laser)
                if self.vx != 0 or self.vy != 0:
                    self.pos_x += self.vx
                    self.pos_y += self.vy
                    self.rect.x = int(self.pos_x)
                    self.rect.y = int(self.pos_y)
                # 否则执行旧的追踪逻辑 (Tracking Laser)
                elif target_rect:
                    dx = target_rect.centerx - self.rect.centerx
                    # 简单的 P 控制
                    self.pos_x += dx * 0.05
                    self.rect.x = int(self.pos_x)
        
        else:
            # 普通子弹 / 方块
            self.pos_x += self.vx
            self.pos_y += self.vy
            self.rect.x = int(self.pos_x)
            self.rect.y = int(self.pos_y)

            # 电路重载 (Teleport)
            # 如果提供了 battle_box，则进行穿墙判定
            if battle_box:
                 # 简单的 X 轴穿墙：从右边出去，从左边回来
                 if self.rect.left > battle_box.right:
                     self.rect.right = battle_box.left
                     self.pos_x = float(self.rect.x) # Sync float pos
                 elif self.rect.right < battle_box.left:
                     self.rect.left = battle_box.right
                     self.pos_x = float(self.rect.x) # Sync float pos
        
    def get_hitbox(self):
        return self.rect

    def draw(self, screen, offset=(0, 0)):
        # 应用震动偏移
        draw_rect = self.rect.move(offset[0], offset[1])
        
        if self.type == "laser" and not self.damaging:
            # 预警线：红色虚线或细线
            warn_rect = draw_rect.copy()
            warn_rect.width = 2
            warn_rect.centerx = draw_rect.centerx
            pygame.draw.rect(screen, (255, 0, 0), warn_rect)
            
            # 也可以画个半透明矩形表示范围 (需要 Surface)
            s = pygame.Surface((self.rect.width, self.rect.height))
            s.set_alpha(50)
            s.fill((255, 0, 0))
            screen.blit(s, draw_rect.topleft)
        elif self.type == "blue_sphere":
            pygame.draw.circle(screen, self.color, draw_rect.center, draw_rect.width // 2)
        elif self.type == "fire":
            # Outer Orange
            pygame.draw.circle(screen, self.color, draw_rect.center, draw_rect.width // 2)
            # Inner Yellow
            pygame.draw.circle(screen, (255, 255, 0), draw_rect.center, draw_rect.width // 3)
        elif self.type == "yellow_line":
             # Yellow Line Bullet: Draws as a line, but hitbox is rect
             # If "waiting", maybe draw differently?
             if hasattr(self, 'state') and self.state == "WAIT":
                 # Flashing or fainter?
                 if (pygame.time.get_ticks() // 100) % 2 == 0:
                     pygame.draw.rect(screen, (255, 255, 100), draw_rect) # Light Yellow
                 else:
                     pygame.draw.rect(screen, (200, 200, 0), draw_rect) # Darker Yellow
             else:
                 pygame.draw.rect(screen, self.color, draw_rect)
        else:
            pygame.draw.rect(screen, self.color, draw_rect)

class YellowBullet(Bullet):
    def __init__(self, rect, vx, vy, wait_time=30):
        # 0.5s wait -> 30 frames at 60FPS
        super().__init__(rect, vx, vy, color=(255, 255, 0), b_type="yellow_line")
        self.state = "WAIT"
        self.wait_timer = wait_time
        self.target_vx = vx
        self.target_vy = vy
        # Initial velocity is 0
        self.vx = 0
        self.vy = 0
        self.damage = 1
        
    def update(self, target_rect=None, battle_box=None):
        if self.state == "WAIT":
            self.wait_timer -= 1
            if self.wait_timer <= 0:
                self.state = "MOVE"
                self.vx = self.target_vx
                self.vy = self.target_vy
        else:
            super().update(target_rect, battle_box)

class PlasmaBlade:
    def __init__(self, x, y, width, height, speed, direction=1, color=(0, 255, 255), inner_color=(200, 255, 255)):
        self.rect = pygame.Rect(x, y, width, height)
        self.pos_x = float(x)
        self.speed = speed
        self.direction = direction # 1 for Right, -1 for Left
        self.damaging = True
        self.damage = PLASMA_BLADE_DAMAGE
        self.type = "plasma_blade"
        self.alive = True
        
        # 预渲染 Surface
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        # Layer 1 (Outer) - 基础 Alpha 150
        r, g, b = color
        pygame.draw.rect(self.image, (r, g, b, 150), self.image.get_rect())
        # Layer 2 (Inner) - 基础 Alpha 200
        inner_rect = self.image.get_rect().inflate(-10, -height*0.2)
        ri, gi, bi = inner_color
        pygame.draw.rect(self.image, (ri, gi, bi, 200), inner_rect)
        
    def update(self, target_rect=None, battle_box=None):
        # 横向移动
        self.pos_x += self.speed * self.direction
        self.rect.x = int(self.pos_x)
        
        # 销毁逻辑：完全超出左右边缘
        if battle_box:
            if self.direction > 0 and self.rect.left > battle_box.right:
                self.alive = False
            elif self.direction < 0 and self.rect.right < battle_box.left:
                self.alive = False
    
    def get_hitbox(self):
        # 仅返回核心区域作为碰撞箱
        # 高度取总高度的 25%，居中
        hit_h = max(4, int(self.rect.height * 0.25))
        return pygame.Rect(self.rect.x, self.rect.centery - hit_h//2, self.rect.width, hit_h)
            
    def draw(self, screen, offset=(0, 0)):
        # 基础位置 + 震动偏移
        base_x = self.rect.x + offset[0]
        base_y = self.rect.y + offset[1]
        
        # 1. 自身抖动 (Y轴随机像素)
        jitter_y = random.randint(-2, 2)
        draw_y = base_y + jitter_y
        
        # 2. 动态 Alpha (Sin wave) - 恢复闪烁逻辑
        # 使用预渲染 Surface，通过 set_alpha 实现整体闪烁
        alpha_val = int((math.sin(pygame.time.get_ticks() * 0.01) + 1) / 2 * 155) + 100 # 100-255 range
        self.image.set_alpha(alpha_val)
        
        screen.blit(self.image, (base_x, draw_y))
        
        # 3. 绘制核心 (White) - 细长条 (保留实时绘制，因为简单且需要最上层)
        core_height = max(2, self.rect.height * 0.2)
        core_rect = pygame.Rect(base_x, draw_y + (self.rect.height - core_height)/2, self.rect.width, core_height)
        pygame.draw.rect(screen, (255, 255, 255), core_rect)

class LaserNetworkLine:
    def __init__(self, rect, axis, warning_duration=60, active_duration=60):
        self.rect = rect
        self.axis = axis # 'h' or 'v'
        self.timer = 0
        self.warning_duration = warning_duration
        self.active_duration = active_duration
        self.state = "warning" # warning, active, dead
        self.damaging = False
        self.damage = 10
        self.type = "laser_network"
        self.alive = True
        
    def update(self, target_rect=None, battle_box=None):
        self.timer += 1
        if self.timer < self.warning_duration:
            self.state = "warning"
            self.damaging = False
        elif self.timer < self.warning_duration + self.active_duration:
            self.state = "active"
            self.damaging = True
        else:
            self.alive = False
    
    def get_hitbox(self):
        # 缩小判定范围，只算核心亮色区域
        # 宽度/高度 缩小到 10px 左右 (原 30px)
        if self.axis == 'v':
            w = 12
            return pygame.Rect(self.rect.centerx - w//2, self.rect.y, w, self.rect.height)
        else:
            h = 12
            return pygame.Rect(self.rect.x, self.rect.centery - h//2, self.rect.width, h)
            
    def draw(self, screen, offset=(0, 0)):
        base_x = self.rect.x + offset[0]
        base_y = self.rect.y + offset[1]
        draw_rect = self.rect.move(offset)
        
        if self.state == "warning":
            # 预警线：细线，闪烁
            alpha = int((math.sin(pygame.time.get_ticks() * 0.02) + 1) * 100) # 0-200
            s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            # 绘制中心细线
            if self.axis == 'h':
                pygame.draw.line(s, (0, 200, 255, alpha), (0, self.rect.height//2), (self.rect.width, self.rect.height//2), 2)
            else:
                pygame.draw.line(s, (0, 200, 255, alpha), (self.rect.width//2, 0), (self.rect.width//2, self.rect.height), 2)
            screen.blit(s, (base_x, base_y))
            
        elif self.state == "active":
            # 实体激光：蓝色
            # 外发光
            pygame.draw.rect(screen, (0, 0, 200), draw_rect)
            # 内核
            pygame.draw.rect(screen, (100, 100, 255), draw_rect.inflate(-4, -4))
            # 核心白
            if self.axis == 'h':
                pygame.draw.line(screen, (255, 255, 255), (draw_rect.left, draw_rect.centery), (draw_rect.right, draw_rect.centery), 2)
            else:
                pygame.draw.line(screen, (255, 255, 255), (draw_rect.centerx, draw_rect.top), (draw_rect.centerx, draw_rect.bottom), 2)
