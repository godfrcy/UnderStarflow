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


class UfoLaserColumn:
    """UFO 牵引：整列竖激光柱。变速=前摇时长随机；假动作=喷→停→再喷（每段喷前都有前摇）。"""
    def __init__(self, rect, warning_duration=60, active_duration=60, pause_duration=60, pulses=1):
        self.rect = rect
        self.timer = 0
        self.warning_duration = warning_duration
        self.active_duration = active_duration
        self.pause_duration = pause_duration
        self.pulses = pulses
        self.pulse_index = 0
        self.state = "warning"  # warning / active / pause
        self.damaging = False
        self.damage = 1  # 与标准激光一致：持续伤害，站在束里才掉血
        self.type = "ufo_laser"
        self.alive = True
        self._build_beam()  # 预渲染渐变光束（避免每帧重算）

    def _build_beam(self):
        """预渲染横向渐变光束：白热核心 → 青晕 → 透明边缘，加色混合后呈发光感。"""
        w, h = self.rect.width, self.rect.height
        self.beam_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w / 2.0
        for x in range(w):
            d = min(1.0, abs(x - cx) / cx)  # 0 中心 → 1 边缘
            if d <= 0.30:
                t = d / 0.30
                r = int(255 - 60 * t); g = 255; b = 255; a = 255
            else:
                t = (d - 0.30) / 0.70
                r = int(40 * (1 - t)); g = int(180 * (1 - t)); b = 255
                a = int(220 * (1 - t) ** 1.6)
            pygame.draw.line(self.beam_surf, (r, g, b, max(0, a)), (x, 0), (x, h))

    def update(self, target_rect=None, battle_box=None):
        self.timer += 1
        if self.state == "warning":
            if self.timer >= self.warning_duration:
                self.state = "active"
                self.damaging = True
                self.timer = 0
        elif self.state == "active":
            if self.timer >= self.active_duration:
                self.pulse_index += 1
                if self.pulse_index >= self.pulses:
                    self.alive = False
                    self.damaging = False
                else:
                    self.state = "pause"
                    self.damaging = False
                    self.timer = 0
        elif self.state == "pause":
            if self.timer >= self.pause_duration:
                self.state = "warning"
                self.damaging = False
                self.timer = 0

    def get_hitbox(self):
        return self.rect

    def draw(self, screen, offset=(0, 0)):
        draw_rect = self.rect.move(offset)
        w, h = draw_rect.width, draw_rect.height
        t = pygame.time.get_ticks()

        if self.state == "warning":
            # 预警：柔和渐变脉冲 + 自上而下扫描进度线（加色混合呈发光感）
            pulse = int((math.sin(t * 0.02) + 1) * 45) + 45  # 45~135
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill((0, 150, 255, pulse))
            screen.blit(s, (draw_rect.x, draw_rect.y), special_flags=pygame.BLEND_ADD)
            scan_y = draw_rect.y + int((self.timer / max(1, self.warning_duration)) * h)
            pygame.draw.line(screen, (255, 255, 255), (draw_rect.left + 6, scan_y), (draw_rect.right - 6, scan_y), 3)
        elif self.state == "active":
            # 光束：预渲染渐变 + 加色混合（发光）
            screen.blit(self.beam_surf, (draw_rect.x, draw_rect.y), special_flags=pygame.BLEND_ADD)
        # pause 不绘制：假动作的「停」故意留白，诱骗玩家以为激光结束了


class ConveyorScrap:
    """废料传送带（过马路）：横向飞过的废料板，矩形碰撞，从一侧进入、穿过战斗箱、从另一侧消失。"""
    def __init__(self, rect, vx, box_left, box_right):
        self.rect = rect
        self.vx = vx
        self.pos_x = float(rect.x)
        self.box_left = box_left
        self.box_right = box_right
        self.damaging = True
        self.damage = 1
        self.type = "conveyor_scrap"
        self.alive = True
        self.timer = 0

    def update(self, target_rect=None, battle_box=None):
        self.timer += 1
        self.pos_x += self.vx
        self.rect.x = int(self.pos_x)
        # 穿过战斗箱两侧即销毁
        if self.rect.left > self.box_right or self.rect.right < self.box_left:
            self.alive = False

    def get_hitbox(self):
        return self.rect

    def draw(self, screen, offset=(0, 0)):
        r = self.rect.move(offset)
        pygame.draw.rect(screen, (50, 50, 60), r)                    # 外框
        pygame.draw.rect(screen, (150, 150, 160), r.inflate(-4, -4))  # 金属面
        pygame.draw.rect(screen, (200, 200, 205), r.inflate(-8, -8))  # 高光


class VerticalScrap:
    """单摆战：上下飞过的废料块（矩形碰撞），从顶部下落或从底部上升。"""
    def __init__(self, rect, vy, box_top, box_bottom):
        self.rect = rect
        self.vy = vy  # 正=向下，负=向上
        self.pos_y = float(rect.y)
        self.box_top = box_top
        self.box_bottom = box_bottom
        self.damaging = True
        self.damage = 1
        self.type = "vertical_scrap"
        self.alive = True
        self.timer = 0

    def update(self, target_rect=None, battle_box=None):
        self.timer += 1
        self.pos_y += self.vy
        self.rect.y = int(self.pos_y)
        if self.rect.top > self.box_bottom or self.rect.bottom < self.box_top:
            self.alive = False

    def get_hitbox(self):
        return self.rect

    def draw(self, screen, offset=(0, 0)):
        r = self.rect.move(offset)
        pygame.draw.rect(screen, (50, 50, 60), r)
        pygame.draw.rect(screen, (150, 150, 160), r.inflate(-4, -4))
        pygame.draw.rect(screen, (200, 200, 205), r.inflate(-8, -8))


class DancerHead:
    """双生舞怜·机枢舞者：单个舞者头颅像。
    一阶段：两侧各一只，沿对角线冲刺（首次预警 1s，之后 0.5s，无休息循环）。
    二阶段：只刷一只，按黄金分割比递归切割场地——每刀在活动区域的长边上取黄金分割点，
    沿切割线冲刺并留下发光红激光，玩家所在的一侧成为更小的活动区，逐刀逼到最后一息空间。"""
    WARN_FIRST = 60   # 一阶段首次预警 1s
    WARN_AFTER = 30   # 一阶段第二次起预警 0.5s
    DASH_SPEED = 14.0
    DASH_SPEED_WEAK = 7.0     # 锁血演出回合：虚弱冲刺（速度减半）
    WARN_PHASE2 = 12          # 二阶段前摇 0.2s
    DASH_SPEED_PHASE2 = 16.8  # 二阶段速度 +20%（14 × 1.2）
    GOLDEN = 0.618            # 黄金分割比（较长段占比）
    MAX_CUTS = 7              # 二阶段切割刀数

    def __init__(self, img, side, box, initial_delay=0, phase2=False, weak=False, bullets_ref=None):
        self.img = img
        self.side = side          # "left" / "right"
        self.box = box
        self.type = "dancer_head"
        self.damaging = False
        self.damage = 1
        self.alive = True
        self.timer = 0
        self.direction = (0, 0)
        self.radius = 26
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.pos = [float(box.centerx), float(box.top)]  # 占位，预警时重定位
        self._update_rect()
        self.phase2 = phase2
        self.bullets_ref = bullets_ref
        if phase2:
            # 二阶段：黄金分割切割，前摇 0.2s、速度 +20%
            self.dash_speed = self.DASH_SPEED_PHASE2
            self.warn_duration = self.WARN_PHASE2
            self._init_cut(box)
        else:
            # weak：锁血演出回合的虚弱冲刺，速度减半（仍走一阶段对角线路径）
            self.dash_speed = self.DASH_SPEED_WEAK if weak else self.DASH_SPEED
            self.warn_duration = self.WARN_FIRST
        # 初始延迟用于错开左右节奏；delay=0 则立即进入预警
        if initial_delay > 0:
            self.state = "delay"
            self.delay_total = initial_delay
        else:
            self.state = "warn"
            self._start_warn()

    def _init_cut(self, box):
        """二阶段：初始化黄金分割递归切割——活动区域先覆盖整个战斗框。"""
        self.region = [float(box.left), float(box.top), float(box.right), float(box.bottom)]
        self.cut_index = 0
        self.cut_axis = "v"   # 先竖切（宽 > 高，先切长边）
        self.cut_line = (0.0, 0.0, 0.0, 0.0)  # 预警/冲刺前由 _plan_cut 填好
        self.pos = [float(box.centerx), float(box.top)]
        self._update_rect()

    def _update_rect(self):
        self.rect.center = (int(self.pos[0]), int(self.pos[1]))

    def _plan_cut(self):
        """二阶段：在当前活动区域上规划这一刀的黄金分割切割线，并把舞者定位到切割线起点。"""
        L, T, R, B = self.region
        if self.cut_axis == "v":
            # 竖切：在宽上取黄金分割点，切割线从上边贯穿到下边
            x = L + (R - L) * self.GOLDEN
            self.cut_line = (x, T, x, B)
            self.direction = (0.0, 1.0)   # 自上而下冲
        else:
            # 横切：在高上取黄金分割点，切割线从左贯穿到右
            y = T + (B - T) * self.GOLDEN
            self.cut_line = (L, y, R, y)
            self.direction = (1.0, 0.0)   # 自左而右冲
        self.pos = [float(self.cut_line[0]), float(self.cut_line[1])]
        self._update_rect()

    def _start_warn(self):
        """进入预警；一阶段重定位到边缘对角线，二阶段规划下一刀切割线。"""
        self.state = "warn"
        self.damaging = False
        self.timer = 0
        if self.phase2:
            self._plan_cut()
            return
        # 方向：左侧颅像向右上/右下，右侧向左上/左下；与上一次反向，避免连续两次冲同一条线
        if hasattr(self, 'prev_dy'):
            dy = -self.prev_dy
        else:
            dy = random.choice([-1, 1])
        self.prev_dy = dy
        self.direction = (1.0, dy) if self.side == "left" else (-1.0, dy)
        hw = self.img.get_width() // 2
        # 起跳点：贴箱体内侧边缘（可见），向上冲走下半区、向下冲走上半区
        if self.side == "left":
            sx = self.box.left + hw
        else:
            sx = self.box.right - hw
        margin = 30
        mid = self.box.top + self.box.height * 0.5
        if self.direction[1] < 0:
            sy = random.uniform(mid, self.box.bottom - margin)
        else:
            sy = random.uniform(self.box.top + margin, mid)
        self.pos = [float(sx), float(sy)]
        self._update_rect()

    def _begin_dash(self):
        self.state = "dash"
        self.damaging = True
        self.timer = 0
        self.trail_prev = (self.pos[0], self.pos[1])

    def update(self, target_rect=None, battle_box=None):
        self.timer += 1
        if target_rect is not None:
            self.last_target_rect = target_rect
        if self.state == "delay":
            if self.timer >= self.delay_total:
                self._start_warn()
        elif self.state == "warn":
            if self.timer >= self.warn_duration:
                self._begin_dash()
        elif self.state == "dash":
            if self.phase2:
                self._update_dash_cut()
            else:
                self._update_dash_line()

    def _update_dash_line(self):
        """一阶段：沿对角线直线冲刺，冲出箱体后立刻反向再预警。"""
        self.pos[0] += self.direction[0] * self.dash_speed
        self.pos[1] += self.direction[1] * self.dash_speed
        self._update_rect()
        if (self.pos[0] < self.box.left - 100 or self.pos[0] > self.box.right + 100 or
                self.pos[1] < self.box.top - 100 or self.pos[1] > self.box.bottom + 100):
            self.warn_duration = self.WARN_AFTER
            self._start_warn()

    def _update_dash_cut(self):
        """二阶段：沿切割线冲刺，每帧留一段发光红激光；到终点后按玩家侧收缩区域。"""
        tx, ty = self.cut_line[2], self.cut_line[3]
        dx = tx - self.pos[0]
        dy = ty - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist <= self.dash_speed:
            self.pos[0] = tx
            self.pos[1] = ty
            self._update_rect()
            if self.bullets_ref is not None:
                self.bullets_ref.append(LaserTrail(self.trail_prev[0], self.trail_prev[1], tx, ty))
            self._split_region()
            self.cut_index += 1
            if self.cut_index >= self.MAX_CUTS:
                self.alive = False   # 切割完毕，舞者退场，激光栅栏残留
            else:
                self.cut_axis = "h" if self.cut_axis == "v" else "v"
                self._start_warn()
        else:
            nx = self.pos[0] + self.direction[0] * self.dash_speed
            ny = self.pos[1] + self.direction[1] * self.dash_speed
            if self.bullets_ref is not None:
                self.bullets_ref.append(LaserTrail(self.trail_prev[0], self.trail_prev[1], nx, ny))
            self.trail_prev = (nx, ny)
            self.pos[0] = nx
            self.pos[1] = ny
            self._update_rect()

    def _split_region(self):
        """切割完成后，活动区域收缩为玩家（红心）所在的那一侧。"""
        L, T, R, B = self.region
        if hasattr(self, 'last_target_rect'):
            px = self.last_target_rect.centerx
            py = self.last_target_rect.centery
        else:
            px = (L + R) / 2.0
            py = (T + B) / 2.0
        if self.cut_axis == "v":
            x = self.cut_line[0]
            if px < x:
                self.region = [L, T, x, B]   # 玩家在左
            else:
                self.region = [x, T, R, B]   # 玩家在右
        else:
            y = self.cut_line[1]
            if py < y:
                self.region = [L, T, R, y]   # 玩家在上
            else:
                self.region = [L, y, R, B]   # 玩家在下

    def draw(self, screen, offset=(0, 0)):
        if self.state == "warn":
            self._draw_warning(screen, offset)
        if self.state in ("warn", "dash"):
            r = self.img.get_rect(center=(int(self.pos[0]) + offset[0], int(self.pos[1]) + offset[1]))
            screen.blit(self.img, r)

    def _draw_warning(self, screen, offset):
        if self.phase2 and self.cut_index < self.MAX_CUTS:
            # 二阶段：预警线 = 即将落下的黄金分割切割线（贯穿活动区域）
            x1, y1, x2, y2 = self.cut_line
            sx, sy = x1 + offset[0], y1 + offset[1]
            exx, eyy = x2 + offset[0], y2 + offset[1]
            pygame.draw.line(screen, (255, 60, 60), (sx, sy), (exx, eyy), 3)
            pygame.draw.line(screen, (255, 140, 140), (sx, sy), (exx, eyy), 1)
            return
        dx, dy = self.direction
        x, y = self.pos[0], self.pos[1]
        ex, ey = x, y
        for _ in range(200):
            ex += dx * 8.0
            ey += dy * 8.0
            if (ex < self.box.left or ex > self.box.right or
                    ey < self.box.top or ey > self.box.bottom):
                break
        sx, sy = x + offset[0], y + offset[1]
        exx, eyy = ex + offset[0], ey + offset[1]
        pygame.draw.line(screen, (255, 60, 60), (sx, sy), (exx, eyy), 3)
        pygame.draw.line(screen, (255, 140, 140), (sx, sy), (exx, eyy), 1)


class LaserTrail:
    """双生舞怜·二阶段技能1：舞者冲刺路径留下的发光红色激光线段。
    点到线段距离判定碰撞，触碰受伤，短暂停留后自动消失。"""
    def __init__(self, x1, y1, x2, y2):
        self.type = "laser_trail"
        self.damaging = True
        self.damage = 1
        self.alive = True
        self.timer = 0
        self.lifetime = 480         # 囚笼残留（回合结束时会统一清空）
        self.x1, self.y1 = float(x1), float(y1)
        self.x2, self.y2 = float(x2), float(y2)
        self.radius = 6             # 线段命中半宽
        pad = 9
        self.rect = pygame.Rect(int(min(x1, x2) - pad), int(min(y1, y2) - pad),
                                int(abs(x2 - x1) + pad * 2), int(abs(y2 - y1) + pad * 2))

    def hit_test(self, px, py, pr):
        """点到线段距离 < pr + self.radius 判定碰撞。"""
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        seg2 = dx * dx + dy * dy
        if seg2 == 0:
            dist = math.hypot(px - self.x1, py - self.y1)
        else:
            t = ((px - self.x1) * dx + (py - self.y1) * dy) / seg2
            t = max(0.0, min(1.0, t))
            dist = math.hypot(px - (self.x1 + t * dx), py - (self.y1 + t * dy))
        return dist < pr + self.radius

    def update(self, target_rect=None, battle_box=None):
        self.timer += 1
        if self.timer >= self.lifetime:
            self.alive = False

    def draw(self, screen, offset=(0, 0)):
        ax = self.x1 + offset[0]; ay = self.y1 + offset[1]
        bx = self.x2 + offset[0]; by = self.y2 + offset[1]
        # 发光红线：暗红外晕 → 亮红主体 → 白粉高光核心
        pygame.draw.line(screen, (150, 0, 0), (ax, ay), (bx, by), 9)
        pygame.draw.line(screen, (255, 30, 30), (ax, ay), (bx, by), 5)
        pygame.draw.line(screen, (255, 170, 170), (ax, ay), (bx, by), 2)


class DancerChaser:
    """双生舞怜·技能组2：田字格追逐。
    一阶段：两个舞者头像沿田字格虚线移动，一只追击玩家（BFS 最短路），一只懒散游荡，周期性交换角色。
    二阶段：只剩一只追击者（游荡者已败），速度 1.5 倍、不交换角色，走过的网格边会燃烧（变红），
    玩家在燃烧路径上移动时每秒扣 1 血。"""
    CHASE_SPEED = 3.5     # 追击速度（略慢于玩家 heart_speed=4）
    WANDER_SPEED = 2.0    # 游荡速度（懒散）
    ROLE_DURATION = 180   # 3s 交换一次追/游荡角色
    HIT_COOLDOWN = 60     # 命中后 1s 不再结算伤害
    PHASE2_SPEED_SCALE = 1.5   # 二阶段追击速度 ×1.5
    BURN_DURATION = 180        # 燃烧路径持续时间（3s），给玩家绕行/等冷却的余裕
    TURN_STALL = 6             # 二阶段转角僵直（0.1s），到达节点后停顿，给玩家拉开距离

    def __init__(self, img, cols, rows, grid_pos, role, phase2=False, burned_edges=None):
        self.img = img
        self.type = "dancer_chaser"
        self.damaging = False
        self.damage = 1
        self.alive = True
        self.timer = 0
        self.radius = 22
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        # 田字格节点坐标（3×3 交叉点，由外部统一计算传入）
        self.cols = cols
        self.rows = rows
        self.grid_pos = grid_pos      # (row, col)
        self.role = role              # "chase" / "wander"
        self.phase2 = phase2          # 二阶段：单追、提速、燃烧路径
        self.burned_edges = burned_edges   # 二阶段共享的"燃烧路径"边集合
        self.role_timer = 0
        self.hit_cooldown = 0
        self.stall = 0                # 转角僵直倒计时（二阶段）
        self.target = None            # 下一目标节点 (row, col)
        self.pos = [float(self.cols[grid_pos[1]]), float(self.rows[grid_pos[0]])]
        self._update_rect()

    def _update_rect(self):
        self.rect.center = (int(self.pos[0]), int(self.pos[1]))

    def on_hit(self):
        self.hit_cooldown = self.HIT_COOLDOWN
        self.damaging = False

    @staticmethod
    def _edge_key(a, b):
        """无向边标准 key：两节点排序后的元组。"""
        return tuple(sorted([a, b]))

    def _nearest_node(self, point):
        px, py = point
        col = min(range(3), key=lambda c: abs(self.cols[c] - px))
        row = min(range(3), key=lambda r: abs(self.rows[r] - py))
        return (row, col)

    def _neighbors(self, node):
        r, c = node
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < 3 and 0 <= nc < 3:
                yield (nr, nc)

    def _bfs_next(self, start, goal):
        """BFS 求 start→goal 的下一跳节点（田字格无权重，最短路）。"""
        if start == goal:
            return None
        queue = [start]
        came_from = {start: None}
        while queue:
            cur = queue.pop(0)
            if cur == goal:
                break
            for nxt in self._neighbors(cur):
                if nxt not in came_from:
                    came_from[nxt] = cur
                    queue.append(nxt)
        if goal not in came_from:
            return None
        path = []
        node = goal
        while node is not None:
            path.append(node)
            node = came_from[node]
        path.reverse()
        return path[1] if len(path) >= 2 else None

    def _chase_target(self, target_rect):
        goal = self._nearest_node(target_rect.center)
        return self._bfs_next(self.grid_pos, goal)

    def _wander_target(self):
        nbs = list(self._neighbors(self.grid_pos))
        return random.choice(nbs) if nbs else None

    def update(self, target_rect=None, battle_box=None):
        self.timer += 1
        # 命中冷却
        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1
        # 错峰：周期性交换追/游荡角色（二阶段单追不交换）
        self.role_timer += 1
        if not self.phase2 and self.role_timer >= self.ROLE_DURATION:
            self.role_timer = 0
            self.role = "wander" if self.role == "chase" else "chase"
        # 追击者与游荡者碰到都结算伤害，命中后进入冷却（避免贴脸连击）
        self.damaging = (self.hit_cooldown == 0)
        # 转角僵直（二阶段）：到达节点后短暂停顿，给玩家拉开距离的机会
        if self.stall > 0:
            self.stall -= 1
        else:
            # 决定下一目标节点
            if self.target is None:
                if self.role == "chase" and target_rect is not None:
                    self.target = self._chase_target(target_rect)
                else:
                    self.target = self._wander_target()
            # 朝目标节点移动
            if self.target is not None:
                tx = self.cols[self.target[1]]
                ty = self.rows[self.target[0]]
                if self.role == "chase":
                    speed = self.CHASE_SPEED * (self.PHASE2_SPEED_SCALE if self.phase2 else 1.0)
                else:
                    speed = self.WANDER_SPEED
                dx = tx - self.pos[0]
                dy = ty - self.pos[1]
                dist = math.hypot(dx, dy)
                if dist <= speed:
                    # 到达目标节点：走过的这条边燃烧（二阶段，持续 BURN_DURATION）
                    if self.phase2 and self.burned_edges is not None:
                        self.burned_edges[self._edge_key(self.grid_pos, self.target)] = self.BURN_DURATION
                    self.pos = [float(tx), float(ty)]
                    self.grid_pos = self.target
                    self.target = None
                    if self.phase2:
                        self.stall = self.TURN_STALL   # 转角僵直
                else:
                    self.pos[0] += dx / dist * speed
                    self.pos[1] += dy / dist * speed
                self._update_rect()

    def draw(self, screen, offset=(0, 0)):
        cx = int(self.pos[0]) + offset[0]
        cy = int(self.pos[1]) + offset[1]
        r = self.img.get_rect(center=(cx, cy))
        screen.blit(self.img, r)
        # 追击者画红圈，游荡者不画（UI 错峰提示）
        if self.role == "chase":
            pygame.draw.circle(screen, (255, 70, 70), (cx, cy), self.radius, 2)


class DancerRail:
    """双生舞怜·技能组3：轨道冲刺舞者。
    沿竖三轨或横三轨随机选一条，预警后沿轨冲刺穿场，循环（与机枢舞者同款节奏）。
    二阶段：只剩一只，速度 +20%，每次冲刺后横/竖轨迹交替。"""
    WARN_FIRST = 60
    WARN_AFTER = 30
    DASH_SPEED = 12.0
    DASH_SPEED_PHASE2 = 14.4   # 二阶段速度 +20%（12 × 1.2）

    def __init__(self, img, box, orientation, initial_delay=0, phase2=False):
        self.img = img
        self.box = box
        self.orientation = orientation      # "vertical" / "horizontal"
        self.phase2 = phase2
        self.type = "dancer_rail"
        self.damaging = False
        self.damage = 1
        self.alive = True
        self.timer = 0
        self.radius = 26
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.dash_speed = self.DASH_SPEED_PHASE2 if phase2 else self.DASH_SPEED
        self._build_tracks()
        self.track = random.choice(self.tracks)
        self.direction = (0.0, 0.0)
        self.pos = [float(box.centerx), float(box.centery)]
        self._update_rect()
        self.warn_duration = self.WARN_FIRST
        if initial_delay > 0:
            self.state = "delay"
            self.delay_total = initial_delay
        else:
            self.state = "warn"
            self._start_warn()

    def _build_tracks(self):
        """按当前方向重建三条轨道（横/竖轨迹交替时会重新计算）。"""
        if self.orientation == "vertical":
            self.tracks = [self.box.left + self.box.width * k / 4.0 for k in (1, 2, 3)]
        else:
            self.tracks = [self.box.top + self.box.height * k / 4.0 for k in (1, 2, 3)]

    def _update_rect(self):
        self.rect.center = (int(self.pos[0]), int(self.pos[1]))

    def _start_warn(self):
        self.state = "warn"
        self.damaging = False
        self.timer = 0
        self.track = random.choice(self.tracks)
        margin = 24
        if self.orientation == "vertical":
            # 竖轨：从上往下或从下往上冲
            self.direction = (0.0, random.choice([-1.0, 1.0]))
            if self.direction[1] < 0:
                self.pos = [float(self.track), float(self.box.bottom - margin)]
            else:
                self.pos = [float(self.track), float(self.box.top + margin)]
        else:
            # 横轨：从左往右或从右往左冲
            self.direction = (random.choice([-1.0, 1.0]), 0.0)
            if self.direction[0] < 0:
                self.pos = [float(self.box.right - margin), float(self.track)]
            else:
                self.pos = [float(self.box.left + margin), float(self.track)]
        self._update_rect()

    def update(self, target_rect=None, battle_box=None):
        self.timer += 1
        if self.state == "delay":
            if self.timer >= self.delay_total:
                self._start_warn()
        elif self.state == "warn":
            if self.timer >= self.warn_duration:
                self.state = "dash"
                self.damaging = True
                self.timer = 0
        elif self.state == "dash":
            self.pos[0] += self.direction[0] * self.dash_speed
            self.pos[1] += self.direction[1] * self.dash_speed
            self._update_rect()
            if (self.pos[0] < self.box.left - 80 or self.pos[0] > self.box.right + 80 or
                    self.pos[1] < self.box.top - 80 or self.pos[1] > self.box.bottom + 80):
                self.warn_duration = self.WARN_AFTER
                if self.phase2:
                    # 二阶段：每次冲刺后横/竖轨迹交替
                    self.orientation = "horizontal" if self.orientation == "vertical" else "vertical"
                    self._build_tracks()
                self._start_warn()

    def draw(self, screen, offset=(0, 0)):
        if self.state == "warn":
            self._draw_warning(screen, offset)
        if self.state in ("warn", "dash"):
            r = self.img.get_rect(center=(int(self.pos[0]) + offset[0], int(self.pos[1]) + offset[1]))
            screen.blit(self.img, r)

    def _draw_warning(self, screen, offset):
        if self.orientation == "vertical":
            x = self.pos[0] + offset[0]
            y0 = self.box.top + offset[1]
            y1 = self.box.bottom + offset[1]
            pygame.draw.line(screen, (255, 60, 60), (x, y0), (x, y1), 3)
            pygame.draw.line(screen, (255, 140, 140), (x, y0), (x, y1), 1)
        else:
            y = self.pos[1] + offset[1]
            x0 = self.box.left + offset[0]
            x1 = self.box.right + offset[0]
            pygame.draw.line(screen, (255, 60, 60), (x0, y), (x1, y), 3)
            pygame.draw.line(screen, (255, 140, 140), (x0, y), (x1, y), 1)
