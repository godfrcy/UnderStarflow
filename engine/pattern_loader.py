"""
模式加载器 (Pattern Loader)
===========================
从 JSON 文件加载弹幕模式定义，在战斗中按时间线执行弹幕生成。
供 BattleManager 调用。

JSON 格式由 bullet_designer.py 导出。
"""

import json
import os
import math
import random
from engine.utils import resource_path
from entities.bullets import Bullet, YellowBullet, PlasmaBlade, LaserNetworkLine


# 表达式求值缓存
import math as _math
_SAFE_BUILTINS = {
    "sin": _math.sin, "cos": _math.cos, "tan": _math.tan,
    "sqrt": _math.sqrt, "pi": _math.pi, "e": _math.e,
    "abs": abs, "int": int, "float": float, "max": max, "min": min,
    "random": lambda a=0, b=1: a + random.random() * (b - a),
    "randint": random.randint,
}


def _eval_expr(expr, t=0, frame=0):
    """安全求值一个表达式字符串"""
    if expr is None:
        return 0
    if isinstance(expr, (int, float)):
        return expr
    if not isinstance(expr, str):
        return expr
    try:
        return eval(expr, {"__builtins__": {}}, {**_SAFE_BUILTINS, "t": t, "frame": frame})
    except Exception:
        return 0


class PatternRunner:
    """
    运行一个弹幕模式。由 BattleManager 每帧调用 update()。
    """
    def __init__(self, battle_manager):
        self.battle = battle_manager
        self.pattern = None
        self.elapsed = 0
        self.total_duration = 0
        self.active = False

    def load(self, pattern_data):
        """加载一个 pattern dict（从 JSON 解析后）"""
        self.pattern = pattern_data
        self.total_duration = pattern_data.get("duration", 480)
        self.elapsed = 0
        self.active = True

    def reset(self):
        self.elapsed = 0
        self.active = False
        self.pattern = None

    def update(self):
        """每帧调用，根据时间线生成弹幕"""
        if not self.active or not self.pattern:
            return

        self.elapsed += 1

        for evt in self.pattern.get("events", []):
            # 兼容 v1 "time" 和 v2 "spawn_frame"
            t = evt.get("spawn_frame", evt.get("time", 0))
            interval = evt.get("interval", 0)
            count = evt.get("count", 1)

            if interval > 0:
                offset = self.elapsed - t
                if offset >= 0 and offset % interval == 0:
                    nth = offset // interval
                    if nth < count:
                        self._spawn(evt, nth)
            else:
                if self.elapsed == t:
                    for i in range(count):
                        self._spawn(evt, i)

        if self.elapsed >= self.total_duration:
            self.active = False

    def _compute_velocity(self, evt, frame_offset=0):
        """根据轨迹类型计算速度向量。支持 v2 designer 的 trajectory 系统。"""
        trajectory = evt.get("trajectory", "straight")
        speed = evt.get("speed", 3.0)
        angle = math.radians(evt.get("angle", 90))
        curve_amp = evt.get("curve_amp", 40)
        curve_freq = evt.get("curve_freq", 3.0)

        base_vx = math.cos(angle) * speed
        base_vy = math.sin(angle) * speed

        if trajectory == "straight":
            return base_vx, base_vy
        elif trajectory == "curve_sin":
            phase = frame_offset * 0.1 * curve_freq
            osc = math.sin(phase) * curve_amp * 0.3
            return base_vx + osc, base_vy
        elif trajectory == "curve_arc":
            bend = frame_offset * 0.02 * curve_freq
            return base_vx + math.sin(bend) * curve_amp * 0.2, base_vy
        elif trajectory == "homing":
            # 追踪弹：朝向玩家当前位置
            heart = self.battle.heart_rect
            dx = heart.centerx - (self.battle.battle_box.left + evt.get("x", 200))
            dy = heart.centery - (self.battle.battle_box.top + evt.get("y", 0))
            dist = math.hypot(dx, dy) or 1
            return (dx / dist) * speed, (dy / dist) * speed
        elif trajectory == "spread":
            return base_vx, base_vy
        return base_vx, base_vy

    def _spawn(self, evt, index=0):
        """根据事件数据生成实际子弹"""
        btype = evt.get("btype", "normal")
        battle_box = self.battle.battle_box
        frame = self.elapsed

        # 解析坐标
        x = _eval_expr(evt.get("x", 200), t=frame, frame=frame)
        y = _eval_expr(evt.get("y", 0), t=frame, frame=frame)

        # 计算速度（支持轨迹系统 + 散射角度偏移）
        spread_angle = evt.get("spread_angle", 30)
        count = evt.get("count", 1)
        angle_offset = (index - (count - 1) / 2) * spread_angle if count > 1 else 0

        # 临时修改 angle 来计算散射
        saved_angle = evt.get("angle", 90)
        evt["angle"] = saved_angle + angle_offset

        vx, vy = self._compute_velocity(evt, frame)

        # 恢复angle
        evt["angle"] = saved_angle

        # 兼容旧格式：如果字段直接有 vx/vy，优先使用
        if "vx" in evt and evt["vx"] != 0:
            vx = _eval_expr(evt.get("vx", 0), t=frame, frame=frame)
        if "vy" in evt and evt["vy"] != 0:
            vy = _eval_expr(evt.get("vy", 3), t=frame, frame=frame)

        w = evt.get("w", evt.get("width", 10))
        h = evt.get("h", evt.get("height", 10))
        color = tuple(evt.get("color", [255, 255, 255]))
        damage = evt.get("damage", 1)

        # 画布坐标 → 战斗区域绝对坐标
        abs_x = battle_box.left + x
        abs_y = battle_box.top + y

        # 应用速度倍率（来自 hack）
        spd = self.battle.bullet_speed_multiplier
        vx *= spd
        vy *= spd

        if btype == "normal":
            rect = pygame.Rect(abs_x - w // 2, abs_y - h // 2, w, h)
            self.battle.bullets.append(Bullet(rect, vx, vy, color, "normal"))

        elif btype == "laser":
            rect = pygame.Rect(abs_x - w // 2, abs_y, w, h)
            tracking = evt.get("tracking", False)
            warning = evt.get("warning", 60)
            bullet = Bullet(rect, vx if not tracking else 0, vy if not tracking else 0,
                           color, "laser", evt.get("active_color", None))
            bullet.warning_duration = warning
            self.battle.bullets.append(bullet)

        elif btype == "cube":
            rect = pygame.Rect(abs_x - w // 2, abs_y - h // 2, w, h)
            self.battle.bullets.append(Bullet(rect, vx, vy, color, "blue_sphere"))

        elif btype == "circle":
            # 圆形弹幕环：在一个 spawn 中生成多个
            ring_count = evt.get("ring_count", 12)
            speed = evt.get("speed", 4)
            spread = evt.get("spread_angle", 0)
            for i in range(ring_count):
                angle = (2 * math.pi / ring_count) * i + (spread * math.pi / 180)
                rvx = math.cos(angle) * speed * spd
                rvy = math.sin(angle) * speed * spd
                r = pygame.Rect(abs_x - w // 2, abs_y - h // 2, w, h)
                self.battle.bullets.append(
                    Bullet(r, rvx, rvy, color, "normal"))

        elif btype == "plasma_blade":
            direction = evt.get("direction", 1)
            speed = _eval_expr(evt.get("speed", 6), t=frame, frame=frame)
            blade = PlasmaBlade(abs_x - w // 2, abs_y - h // 2, w, h, speed, direction, color)
            self.battle.bullets.append(blade)

        elif btype == "laser_network":
            axis = evt.get("axis", "h")
            warning = evt.get("warning", 60)
            active = evt.get("active_duration", 60)
            rect = pygame.Rect(abs_x - w // 2, abs_y - h // 2, w, h)
            self.battle.bullets.append(
                LaserNetworkLine(rect, axis, warning, active))

        elif btype == "yellow_line":
            wait = evt.get("wait_time", 30)
            rect = pygame.Rect(abs_x - w // 2, abs_y - h // 2, w, h)
            yb = YellowBullet(rect, vx, vy, wait)
            self.battle.bullets.append(yb)

        elif btype == "targeted":
            # 追踪弹：朝向玩家
            heart = self.battle.heart_rect
            dx = heart.centerx - abs_x
            dy = heart.centery - abs_y
            dist = math.hypot(dx, dy) or 1
            speed = evt.get("speed", 3)
            tvx = (dx / dist) * speed * spd
            tvy = (dy / dist) * speed * spd
            rect = pygame.Rect(abs_x - w // 2, abs_y - h // 2, w, h)
            self.battle.bullets.append(Bullet(rect, tvx, tvy, color, "normal"))

        elif btype == "spread":
            # 扇形散射
            spread_count = evt.get("count", 5)
            spread_angle = evt.get("spread_angle", 30)
            base_angle = _eval_expr(evt.get("base_angle", -90), t=frame, frame=frame)
            base_rad = base_angle * math.pi / 180
            half = (spread_angle * (spread_count - 1) / 2) * math.pi / 180
            speed = _eval_expr(evt.get("speed", 3), t=frame, frame=frame)
            for i in range(spread_count):
                angle = base_rad - half + (i * spread_angle * math.pi / 180 / (spread_count - 1 or 1))
                svx = math.cos(angle) * speed * spd
                svy = math.sin(angle) * speed * spd
                rect = pygame.Rect(abs_x - w // 2, abs_y - h // 2, w, h)
                self.battle.bullets.append(Bullet(rect, svx, svy, color, "normal"))


# ─── 便捷函数 ──────────────────────────────────────────

def load_pattern(pattern_name):
    """
    从 assetsDB/patterns/ 加载 JSON 弹幕模式。
    返回 dict 或 None。
    """
    patterns_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assetsDB", "patterns"
    )
    path = os.path.join(patterns_dir, f"{pattern_name}.json")
    if not os.path.exists(path):
        print(f"Pattern not found: {pattern_name}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load pattern {pattern_name}: {e}")
        return None

# 需要导入 pygame 供 _spawn 使用
import pygame
