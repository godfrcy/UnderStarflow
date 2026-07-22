"""
弹幕设计器 v3 — 直观可视化编辑
==============================
设计模式: 点击画布放置子弹初始位置
细节模式: 选中一个子弹后，在画布上拖拽编辑轨迹向量

操作:
  设计模式: 点击画布 → 放子弹; 点击已有子弹 → 进入细节模式
  细节模式: 在画布上拖拽 → 画出方向箭头(向量); 右侧面板调参数
  空格: 播放/暂停
  Delete: 删除当前编辑的子弹
  Esc: 退出细节模式回到设计模式
  Ctrl+S: 保存
"""

import pygame
import math
import json
import os
import sys

# ─── 常量 ───────────────────────────────────────────────
WINDOW_W, WINDOW_H = 1100, 680
CANVAS_W, CANVAS_H = 400, 300
CANVAS_X, CANVAS_Y = 20, 50
GRID = 20
TIMELINE_Y = 520
TIMELINE_X = 20
TIMELINE_W = 400
TIMELINE_H = 36
PANEL_X = 460
PANEL_Y = 50
PANEL_W = 620
FPS = 60
MAX_DURATION = 480
HEART = 14

BTYPES = {
    "normal":       ("普通子弹", (255,255,255), (10,10)),
    "laser":        ("延时激光", (255,80,80),   (24,240)),
    "cube":         ("方块",     (200,200,100), (24,24)),
    "circle":       ("圆环",     (100,200,255), (8,8)),
    "plasma_blade": ("等离子刃", (0,255,255),   (80,8)),
    "laser_net":    ("激光网",   (0,120,255),   (400,6)),
    "yellow_line":  ("黄线",     (255,255,0),   (36,4)),
    "homing":       ("追踪弹",   (255,140,100), (12,12)),
}

TRAJECTORIES = ["straight", "curve_sin", "curve_arc", "homing", "spread"]
TRAJ_NAMES = {
    "straight": "直线", "curve_sin": "正弦波", "curve_arc": "弧线",
    "homing": "追踪", "spread": "散射"
}

# ─── 字体 ───────────────────────────────────────────────
def _font(size):
    for p in [r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc"]:
        if os.path.exists(p): return pygame.font.Font(p, size)
    return pygame.font.Font(None, size)

# ─── 数据模型 ──────────────────────────────────────────
class BulletEvent:
    def __init__(self, x=200, y=20):
        self.x, self.y = x, y
        self.spawn_frame = 0
        self.lifetime = 480    # 默认活满全场，飞出屏幕即清理
        self.btype = "normal"
        self.w, self.h = BTYPES["normal"][2]
        self.color = list(BTYPES["normal"][1])
        self.trajectory = "straight"
        self.speed = 3.0          # 箭头长度 = 速度
        self.angle = 90           # 箭头方向(度)
        self.curve_amp = 40
        self.curve_freq = 3.0
        self.count = 1
        self.spread_angle = 30
        self.damage = 1
        self.note = ""

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d):
        e = cls()
        for k, v in d.items():
            if hasattr(e, k): setattr(e, k, v)
        return e

    def arrow_end(self):
        """返回向量箭头的终点坐标(画布坐标)，固定长度只表示方向"""
        rad = math.radians(self.angle)
        LEN = 35  # 固定长度
        return self.x + math.cos(rad) * LEN, self.y + math.sin(rad) * LEN

class Pattern:
    def __init__(self, name="new_pattern"):
        self.name = name; self.duration = MAX_DURATION
        self.description = ""; self.events = []

    def to_dict(self):
        return {"name": self.name, "duration": self.duration,
                "description": self.description,
                "events": [e.to_dict() for e in self.events]}

    @classmethod
    def from_dict(cls, d):
        p = cls(d.get("name", "loaded"))
        p.duration = d.get("duration", MAX_DURATION)
        p.description = d.get("description", "")
        p.events = [BulletEvent.from_dict(e) for e in d.get("events", [])]
        return p

# ─── 主程序 ────────────────────────────────────────────
class Designer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("弹幕设计器 v3")
        self.clock = pygame.time.Clock()
        self.running = True

        self.fs = _font(14); self.fm = _font(18); self.fl = _font(22)

        self.pattern = Pattern()
        self.mode = "design"        # "design" | "detail"
        self.edit_idx = -1          # 当前正在细节编辑的子弹索引
        self.playing = False
        self.paused = False     # 暂停（不重置帧）
        self.play_frame = 0
        self.spawned_count = 0  # 已生成子弹计数（调试用）
        self.heart = [CANVAS_W//2, CANVAS_H//2]
        self.preview = []
        self.msg = ""; self.msg_timer = 0

        # 拖拽状态
        self.dragging_bullet = None
        self._drag_start_pos = (0, 0)
        self.drawing_arrow = False
        self.arrow_start = (0, 0)

        # 文本输入
        self.input_active = False     # 是否正在输入
        self.input_text = ""          # 当前输入文本
        self.input_field = ""         # "speed" | "search" | "lifetime" | ""
        self.search_result = ""       # 搜索结果提示

        self.patterns_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assetsDB", "patterns")
        self.canvas = pygame.Surface((CANVAS_W, CANVAS_H))
        self.grid = self._make_grid()

    def _make_grid(self):
        s = pygame.Surface((CANVAS_W, CANVAS_H), pygame.SRCALPHA)
        for x in range(0, CANVAS_W, GRID):
            pygame.draw.line(s, (50, 50, 60, 60), (x, 0), (x, CANVAS_H))
        for y in range(0, CANVAS_H, GRID):
            pygame.draw.line(s, (50, 50, 60, 60), (0, y), (CANVAS_W, y))
        return s

    def _msg(self, m):
        self.msg = m; self.msg_timer = 120

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self._handle()
            self._update()
            self._draw()
        pygame.quit()

    # ─── 事件处理 ──────────────────────────────────────
    def _handle(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: self.running = False
            elif ev.type == pygame.KEYDOWN: self._key(ev)
            elif ev.type == pygame.MOUSEBUTTONDOWN: self._down(ev)
            elif ev.type == pygame.MOUSEBUTTONUP: self._up(ev)
            elif ev.type == pygame.MOUSEMOTION: self._move(ev)

    def _key(self, ev):
        k = ev.key
        mod = pygame.key.get_mods()

        # ── 文本输入模式 ──
        if self.input_active:
            if k == pygame.K_RETURN:
                self._confirm_input()
            elif k == pygame.K_ESCAPE:
                self.input_active = False; self.input_text = ""
                self._msg("取消输入")
            elif k == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                # 接受数字、小数点、负号
                c = ev.unicode
                if c.isdigit() or c in ".-":
                    self.input_text += c
            return  # 输入时不处理其他按键

        if k == pygame.K_SPACE: self._toggle_pause()     # 空格=播放/暂停
        elif k == pygame.K_DELETE:
            if self.edit_idx >= 0:
                del self.pattern.events[self.edit_idx]
                self.edit_idx = -1; self.mode = "design"
                self._msg("已删除")
        elif k == pygame.K_ESCAPE:
            self.edit_idx = -1; self.mode = "design"
            self._msg("回到设计模式")
        elif k == pygame.K_s and mod & pygame.KMOD_CTRL: self._save()
        elif k == pygame.K_e and mod & pygame.KMOD_CTRL: self._export_py()
        elif k == pygame.K_o and mod & pygame.KMOD_CTRL: self._load()
        elif k == pygame.K_c and mod & pygame.KMOD_CTRL:
            # 复制当前子弹
            if self.edit_idx >= 0:
                self.clipboard = self.pattern.events[self.edit_idx].to_dict()
                self._msg(f"已复制子弹 #{self.edit_idx} 的参数")
        elif k == pygame.K_v and mod & pygame.KMOD_CTRL:
            # 粘贴到当前子弹
            if hasattr(self, 'clipboard') and self.clipboard and self.edit_idx >= 0:
                e = self.pattern.events[self.edit_idx]
                x, y = e.x, e.y  # 保留位置
                sf = e.spawn_frame  # 保留帧
                for kk, vv in self.clipboard.items():
                    if kk not in ('x', 'y', 'spawn_frame'):
                        setattr(e, kk, vv)
                e.x, e.y = x, y
                e.spawn_frame = sf
                self._msg(f"已粘贴: #{self.edit_idx} 帧={e.spawn_frame} x={e.x} 速度={e.speed} 轨迹={e.trajectory}")
            elif self.edit_idx < 0:
                self._msg("先选中一个子弹再粘贴")
        elif k == pygame.K_r and mod & pygame.KMOD_CTRL:
            self.pattern = Pattern(); self.edit_idx = -1; self.mode = "design"; self.clipboard = None
            self._msg("重置")

        # 预览时控制灵魂
        if self.playing:
            sp = 4
            h = self.heart
            if k == pygame.K_LEFT:  h[0] -= sp
            if k == pygame.K_RIGHT: h[0] += sp
            if k == pygame.K_UP:    h[1] -= sp
            if k == pygame.K_DOWN:  h[1] += sp
            h[0] = max(0, min(h[0], CANVAS_W))
            h[1] = max(0, min(h[1], CANVAS_H))

        # 细节模式快捷键
        if self.mode == "detail" and self.edit_idx >= 0:
            e = self.pattern.events[self.edit_idx]
            s = 5 if mod & pygame.KMOD_SHIFT else 1
            # 数字键激活输入
            if k == pygame.K_1:
                self.input_active = True; self.input_field = "spawn_frame"
                self.input_text = str(e.spawn_frame)
                self._msg("输入出现帧，Enter确认")
            elif k == pygame.K_2:
                self.input_active = True; self.input_field = "lifetime"
                self.input_text = str(e.lifetime)
                self._msg("输入存活帧，Enter确认")
            elif k == pygame.K_3:
                self.input_active = True; self.input_field = "speed"
                self.input_text = f"{e.speed:.1f}"
                self._msg("输入速度，Enter确认")
            # 键盘微调（备用）
            elif k == pygame.K_w: e.spawn_frame = max(0, e.spawn_frame - s*5)
            elif k == pygame.K_s: e.spawn_frame = min(MAX_DURATION, e.spawn_frame + s*5)
            elif k == pygame.K_e: e.lifetime = max(1, e.lifetime - s*10)
            elif k == pygame.K_d: e.lifetime = min(MAX_DURATION, e.lifetime + s*10)
            elif k == pygame.K_q: e.speed = max(0.5, e.speed - 0.5)
            elif k == pygame.K_a: e.speed = min(20, e.speed + 0.5)

    def _down(self, ev):
        mx, my = ev.pos
        btn = ev.button
        in_canvas = CANVAS_X <= mx <= CANVAS_X+CANVAS_W and CANVAS_Y <= my <= CANVAS_Y+CANVAS_H
        in_timeline = TIMELINE_X <= mx <= TIMELINE_X+TIMELINE_W and TIMELINE_Y <= my <= TIMELINE_Y+TIMELINE_H
        in_panel = PANEL_X <= mx <= PANEL_X+PANEL_W

        cx, cy = mx - CANVAS_X, my - CANVAS_Y

        self.input_active = False  # 点击任何地方先关闭输入

        if in_canvas and btn == 1:
            found = self._find(cx, cy)
            if found is not None and self.mode == "design":
                # 设计模式点中子弹 → 进入细节模式 (除非后续拖拽超过阈值)
                self.edit_idx = found
                self.dragging_bullet = found
                self._drag_start_pos = (cx, cy)  # 记录起始位置判断是否拖拽
            elif found is None and self.mode == "design":
                # 放新子弹
                e = BulletEvent(int(cx), int(cy))
                e.spawn_frame = self.play_frame
                self.pattern.events.append(e)
                self.edit_idx = len(self.pattern.events) - 1
                self._msg(f"放置子弹 #{self.edit_idx} at ({e.x},{e.y}) 帧{e.spawn_frame}")
            elif self.mode == "detail" and self.edit_idx >= 0:
                self.drawing_arrow = True
                self.arrow_start = (cx, cy)

        elif in_canvas and btn == 3 and self.mode == "design":
            found = self._find(cx, cy)
            if found is not None:
                del self.pattern.events[found]
                if self.edit_idx == found: self.edit_idx = -1
                self._msg(f"删除 #{found}")

        elif btn == 1:
            if hasattr(self, '_replay_btn_rect') and self._replay_btn_rect.collidepoint(mx, my):
                self._restart_preview()
            elif in_timeline:
                tx = mx - TIMELINE_X
                self.play_frame = int((tx/TIMELINE_W) * self.pattern.duration)
            elif in_panel:
                self._panel_click(mx, my)

    def _up(self, ev):
        # 设计模式：判断单击还是拖拽
        if self.dragging_bullet is not None and self.mode == "design":
            idx = self.dragging_bullet
            if hasattr(self, '_drag_start_pos'):
                sx, sy = self._drag_start_pos
                if idx < len(self.pattern.events):
                    ex, ey = self.pattern.events[idx].x, self.pattern.events[idx].y
                    dist = math.hypot(ex - sx, ey - sy)
                    if dist < 3:
                        # 几乎没动 → 单击 → 进入细节模式
                        self.mode = "detail"
                        self._msg(f"进入细节模式 — 编辑子弹 #{idx}")
                    else:
                        self._msg(f"移动子弹 #{idx} 到 ({ex},{ey})")

        if self.drawing_arrow and self.edit_idx >= 0:
            mx, my = ev.pos
            if CANVAS_X <= mx <= CANVAS_X+CANVAS_W and CANVAS_Y <= my <= CANVAS_Y+CANVAS_H:
                cx, cy = mx - CANVAS_X, my - CANVAS_Y
                e = self.pattern.events[self.edit_idx]
                dx = cx - e.x; dy = cy - e.y
                dist = math.hypot(dx, dy)
                if dist > 3:
                    e.angle = math.degrees(math.atan2(dy, dx))
                    self._msg(f"方向设为 {e.angle:.0f}°")
        self.drawing_arrow = False
        # 停止拖拽子弹
        self.dragging_bullet = None

    def _move(self, ev):
        mx, my = ev.pos
        if self.dragging_bullet is not None:
            if CANVAS_X <= mx <= CANVAS_X+CANVAS_W and CANVAS_Y <= my <= CANVAS_Y+CANVAS_H:
                cx, cy = mx - CANVAS_X, my - CANVAS_Y
                idx = self.dragging_bullet
                if idx < len(self.pattern.events):
                    self.pattern.events[idx].x = max(0, min(int(cx), CANVAS_W))
                    self.pattern.events[idx].y = max(0, min(int(cy), CANVAS_H))

    def _find(self, cx, cy):
        best, best_d = None, 15
        for i, e in enumerate(self.pattern.events):
            d = math.hypot(e.x - cx, e.y - cy)
            if d < best_d: best_d = d; best = i
        return best

    # ─── 面板交互 ──────────────────────────────────────
    def _panel_click(self, mx, my):
        rx, ry = mx - PANEL_X, my - PANEL_Y

        # 模式切换按钮
        bw = PANEL_W // 2 - 6
        if 4 <= ry <= 36:
            if rx <= bw:
                self.mode = "design"; self.edit_idx = -1
                self._msg("设计模式 — 点击画布放子弹")
            else:
                if self.edit_idx < 0 and self.pattern.events:
                    self.edit_idx = len(self.pattern.events) - 1
                self.mode = "detail"
                if self.edit_idx >= 0:
                    self._msg(f"细节模式 — 编辑子弹 #{self.edit_idx}")
                else:
                    self._msg("细节模式 — 先在设计模式点击一个子弹")
            return

        if self.mode != "detail" or self.edit_idx < 0: return
        e = self.pattern.events[self.edit_idx]

        # ── 删除按钮 ──
        del_btn = pygame.Rect(PANEL_X + PANEL_W - 120, PANEL_Y + 62 - 8, 116, 28)
        if del_btn.collidepoint(mx, my):
            del self.pattern.events[self.edit_idx]
            self.edit_idx = -1; self.mode = "design"
            self._msg("已删除子弹"); return

        # ── 弹幕类型 (大按钮，点一下切换下一个) ──
        type_btn = pygame.Rect(PANEL_X + 5, PANEL_Y + 90, 280, 28)
        if type_btn.collidepoint(mx, my):
            btypes = list(BTYPES.keys())
            idx = btypes.index(e.btype) if e.btype in btypes else 0
            next_t = btypes[(idx + 1) % len(btypes)]
            e.btype = next_t; e.w, e.h = BTYPES[next_t][2]; e.color = list(BTYPES[next_t][1])
            self._msg(f"类型: {BTYPES[next_t][0]}"); return

        # ── 轨迹类型 (大按钮，点一下切换下一个) ──
        traj_btn = pygame.Rect(PANEL_X + 295, PANEL_Y + 90, 300, 28)
        if traj_btn.collidepoint(mx, my):
            idx2 = TRAJECTORIES.index(e.trajectory) if e.trajectory in TRAJECTORIES else 0
            next_tr = TRAJECTORIES[(idx2 + 1) % len(TRAJECTORIES)]
            e.trajectory = next_tr
            self._msg(f"轨迹: {TRAJ_NAMES[next_tr]}"); return

    # ─── 更新 ──────────────────────────────────────────
    def _update(self):
        if self.msg_timer > 0: self.msg_timer -= 1
        if self.playing and not self.paused:
            self._spawn()
            self._update_preview()
            self.play_frame += 1
            if self.play_frame >= self.pattern.duration:
                self.playing = False; self.paused = False
                self.preview.clear()
                self._msg(f"预览结束 — 共生成了 {self.spawned_count} 个子弹")

    def _spawn(self):
        for e in self.pattern.events:
            if e.spawn_frame != self.play_frame: continue
            self.spawned_count += 1
            for i in range(e.count):
                off = (i - (e.count-1)/2) * e.spread_angle
                rad = math.radians(e.angle + off)
                spd = e.speed
                self.preview.append({
                    "x": e.x, "y": e.y, "vx": math.cos(rad)*spd, "vy": math.sin(rad)*spd,
                    "w": e.w, "h": e.h, "color": e.color, "type": e.btype,
                    "life": e.lifetime, "traj": e.trajectory,
                    "amp": e.curve_amp, "freq": e.curve_freq, "born": self.play_frame,
                })

    def _update_preview(self):
        for b in self.preview[:]:
            age = self.play_frame - b["born"]
            if b["traj"] == "curve_sin":
                b["vx"] += math.sin(age*0.05*(b["freq"]/3)) * b["amp"]*0.03
            elif b["traj"] == "curve_arc":
                b["vy"] += 0.05
            b["x"] += b["vx"]; b["y"] += b["vy"]; b["life"] -= 1
            if b["life"]<=0 or b["x"]<-60 or b["x"]>CANVAS_W+60 or b["y"]<-60 or b["y"]>CANVAS_H+60:
                self.preview.remove(b)

    def _confirm_input(self):
        """确认文本输入"""
        try:
            val = float(self.input_text)
        except ValueError:
            self._msg(f"无效输入: {self.input_text}")
            self.input_active = False; self.input_text = ""
            return

        if self.input_field == "search":
            idx = int(val)
            if 0 <= idx < len(self.pattern.events):
                self.edit_idx = idx
                self.mode = "detail"
                self._msg(f"跳转到子弹 #{idx}")
            else:
                self._msg(f"子弹 #{idx} 不存在 (共{len(self.pattern.events)}个)")
        elif self.input_field == "spawn_frame" and self.edit_idx >= 0:
            self.pattern.events[self.edit_idx].spawn_frame = max(0, min(int(val), MAX_DURATION))
            self._msg(f"出现帧设为 {int(val)}")
        elif self.input_field == "speed" and self.edit_idx >= 0:
            self.pattern.events[self.edit_idx].speed = max(0.5, min(val, 50))
            self._msg(f"速度设为 {val:.1f}")
        elif self.input_field == "lifetime" and self.edit_idx >= 0:
            self.pattern.events[self.edit_idx].lifetime = max(1, min(int(val), 999))
            self._msg(f"生命设为 {int(val)}帧")

        self.input_active = False; self.input_text = ""

    def _restart_preview(self):
        """空格：从头重新播放"""
        self.playing = True
        self.paused = False
        self.play_frame = 0
        self.preview.clear()
        self.spawned_count = 0
        self.heart = [CANVAS_W//2, CANVAS_H//2]

    def _toggle_pause(self):
        """暂停/继续（不重置帧）"""
        if not self.playing and not self.paused:
            self._restart_preview()
        else:
            self.paused = not self.paused

    def _save(self):
        os.makedirs(self.patterns_dir, exist_ok=True)
        n = self.pattern.name.replace(" ", "_").lower()
        p = os.path.join(self.patterns_dir, f"{n}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.pattern.to_dict(), f, ensure_ascii=False, indent=2)
        self._msg(f"已保存: {p}")

    def _export_py(self):
        """导出为可粘贴到 battle_system.py 的 Python 技能函数"""
        os.makedirs(self.patterns_dir, exist_ok=True)
        name = self.pattern.name.replace(" ", "_").lower()
        path = os.path.join(self.patterns_dir, f"{name}.py")

        lines = [
            f'# Auto-generated skill: {self.pattern.name}',
            f'# Duration: {self.pattern.duration} frames ({self.pattern.duration/60:.1f}s)',
            f'# Events: {len(self.pattern.events)}',
            f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            f'#',
            f'# Usage: Add "@{name}" to enemy skills list, OR paste spawn logic below.',
            f'',
            f'def spawn_{name}(self):',
            f'    """Auto-generated bullet pattern."""',
            f'    t = self.ENEMY_TURN_DURATION - self.enemy_turn_timer',
            f'',
        ]

        for evt in self.pattern.events:
            angle_rad = math.radians(evt.angle)
            vx = math.cos(angle_rad) * evt.speed
            vy = math.sin(angle_rad) * evt.speed
            bx, by = evt.x, evt.y
            w, h = evt.w, evt.h
            c = tuple(evt.color)

            lines.append(f'    if t == {evt.spawn_frame}:')
            lines.append(f'        # {BTYPES[evt.btype][0]} | {TRAJ_NAMES.get(evt.trajectory, evt.trajectory)}')

            if evt.btype == "laser":
                lines.append(f'        r = pygame.Rect(self.battle_box.left + {bx} - {w//2}, self.battle_box.top + {by}, {w}, {h})')
                lines.append(f'        b = Bullet(r, {vx:.1f}, {vy:.1f}, {c}, "laser")')
                lines.append(f'        b.warning_duration = {evt.warning}')
                lines.append(f'        b.damage = {evt.damage}')
                lines.append(f'        self.bullets.append(b)')
            elif evt.btype == "laser_net":
                lines.append(f'        r = pygame.Rect(self.battle_box.left + {bx} - {w//2}, self.battle_box.top + {by} - {h//2}, {w}, {h})')
                lines.append(f'        self.bullets.append(LaserNetworkLine(r, "{evt.axis}", {evt.warning}, {evt.warning}))')
            elif evt.btype == "plasma_blade":
                lines.append(f'        self.bullets.append(PlasmaBlade(self.battle_box.left + {bx} - {w//2}, self.battle_box.top + {by} - {h//2}, {w}, {h}, {evt.speed:.1f}, {evt.direction}, {c}))')
            elif evt.btype == "yellow_line":
                lines.append(f'        r = pygame.Rect(self.battle_box.left + {bx} - {w//2}, self.battle_box.top + {by} - {h//2}, {w}, {h})')
                lines.append(f'        self.bullets.append(YellowBullet(r, {vx:.1f}, {vy:.1f}, wait_time=30))')
            else:
                lines.append(f'        r = pygame.Rect(self.battle_box.left + {bx} - {w//2}, self.battle_box.top + {by} - {h//2}, {w}, {h})')
                lines.append(f'        b = Bullet(r, {vx:.1f}, {vy:.1f}, {c}, "{evt.btype}")')
                lines.append(f'        b.damage = {evt.damage}')
                lines.append(f'        self.bullets.append(b)')
            lines.append('')

        lines.append(f'# End of {name}')

        with open(path, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        self._msg(f"已导出 Python: {path}")

    def _load(self):
        os.makedirs(self.patterns_dir, exist_ok=True)
        fs = [f for f in os.listdir(self.patterns_dir) if f.endswith(".json")]
        if fs:
            with open(os.path.join(self.patterns_dir, fs[0]), "r", encoding="utf-8") as f:
                self.pattern = Pattern.from_dict(json.load(f))
            self.edit_idx = -1; self.mode = "design"
            self._msg(f"已加载: {fs[0]}")
        else: self._msg("无已保存模式")

    # ─── 绘制 ──────────────────────────────────────────
    def _draw(self):
        self.screen.fill((25, 25, 38))
        self._draw_canvas()
        self._draw_timeline()
        self._draw_panel()
        self._draw_status()
        pygame.display.flip()

    def _draw_canvas(self):
        pygame.draw.rect(self.screen, (80,80,100), (CANVAS_X-2, CANVAS_Y-2, CANVAS_W+4, CANVAS_H+4), 2)
        self.canvas.fill((12,12,20))
        self.canvas.blit(self.grid, (0,0))

        # 画所有子弹
        for i, e in enumerate(self.pattern.events):
            is_edit = (self.mode == "detail" and i == self.edit_idx)
            col = (255, 220, 60) if is_edit else e.color
            r = 7 if is_edit else 4
            pygame.draw.circle(self.canvas, col, (int(e.x), int(e.y)), r)
            if is_edit:
                pygame.draw.circle(self.canvas, (255,255,255), (int(e.x), int(e.y)), r+2, 1)
                # 画向量箭头
                ax, ay = e.arrow_end()
                if e.trajectory != "homing":  # 追踪弹不需要方向
                    pygame.draw.line(self.canvas, (0, 255, 100), (e.x, e.y), (ax, ay), 2)
                    # 箭头尖
                    tip_rad = math.radians(e.angle)
                    tip_len = 8
                    a1 = tip_rad + math.radians(150)
                    a2 = tip_rad - math.radians(150)
                    pygame.draw.line(self.canvas, (0, 255, 100),
                                     (ax, ay),
                                     (ax + math.cos(a1)*tip_len, ay + math.sin(a1)*tip_len), 2)
                    pygame.draw.line(self.canvas, (0, 255, 100),
                                     (ax, ay),
                                     (ax + math.cos(a2)*tip_len, ay + math.sin(a2)*tip_len), 2)
            # 显示编号
            lbl = self.fs.render(str(i), True, (180,180,180))
            self.canvas.blit(lbl, (e.x+10, e.y-8))

        # 正在画向量时的实时预览
        if self.drawing_arrow and self.edit_idx >= 0:
            mx, my = pygame.mouse.get_pos()
            if CANVAS_X <= mx <= CANVAS_X+CANVAS_W and CANVAS_Y <= my <= CANVAS_Y+CANVAS_H:
                e = self.pattern.events[self.edit_idx]
                cx, cy = mx - CANVAS_X, my - CANVAS_Y
                pygame.draw.line(self.canvas, (0,255,200), (e.x, e.y), (cx, cy), 2)

        # 预览子弹
        for b in self.preview:
            c = b["color"]
            if b["type"] in ("laser", "laser_net"):
                r = pygame.Rect(b["x"]-b["w"]//2, b["y"]-b["h"]//2, b["w"], b["h"])
                pygame.draw.rect(self.canvas, c, r, 1)
            else:
                pygame.draw.circle(self.canvas, c, (int(b["x"]), int(b["y"])), max(3, b["w"]//2))

        # 灵魂
        if self.playing:
            hx, hy = int(self.heart[0]), int(self.heart[1])
            pygame.draw.rect(self.canvas, (255,50,50), (hx-HEART//2, hy-HEART//2, HEART, HEART))
            pygame.draw.rect(self.canvas, (255,255,255), (hx-HEART//2, hy-HEART//2, HEART, HEART), 1)

        self.screen.blit(self.canvas, (CANVAS_X, CANVAS_Y))

        # 画布标签
        if self.mode == "design":
            lbl = self.fm.render("🎨 设计模式 — 点击放子弹 | 点已有子弹进入细节", True, (180,180,200))
        else:
            e = self.pattern.events[self.edit_idx] if self.edit_idx >= 0 else None
            tn = TRAJ_NAMES.get(e.trajectory, "?") if e else "?"
            lbl = self.fm.render(f"🔍 细节模式 — 编辑 #{self.edit_idx} | 轨迹:{tn} | 拖拽画布设方向向量", True, (180,200,180))
        self.screen.blit(lbl, (CANVAS_X, CANVAS_Y-24))

    def _draw_timeline(self):
        r = pygame.Rect(TIMELINE_X, TIMELINE_Y, TIMELINE_W, TIMELINE_H)
        pygame.draw.rect(self.screen, (35,35,52), r)
        pygame.draw.rect(self.screen, (80,80,100), r, 1)
        px = TIMELINE_X + int((self.play_frame/self.pattern.duration)*TIMELINE_W)
        pygame.draw.line(self.screen, (255,60,60), (px, TIMELINE_Y), (px, TIMELINE_Y+TIMELINE_H), 2)
        for i, e in enumerate(self.pattern.events):
            ex = TIMELINE_X + int((e.spawn_frame/self.pattern.duration)*TIMELINE_W)
            col = (255,220,60) if (self.mode=="detail" and i==self.edit_idx) else (100,180,255)
            pygame.draw.circle(self.screen, col, (ex, TIMELINE_Y+TIMELINE_H//2), 5)
        t = self.fm.render(f"帧:{self.play_frame}/{self.pattern.duration} [{self.pattern.duration/60:.1f}s] | 生成:{self.spawned_count}", True, (200,200,200))
        self.screen.blit(t, (TIMELINE_X+TIMELINE_W+12, TIMELINE_Y+2))

        # 重播按钮
        self._replay_btn_rect = pygame.Rect(TIMELINE_X+TIMELINE_W+10, TIMELINE_Y+20, 60, 22)
        pygame.draw.rect(self.screen, (100, 100, 180), self._replay_btn_rect)
        pygame.draw.rect(self.screen, (140, 140, 220), self._replay_btn_rect, 1)
        self.screen.blit(self.fs.render("↺重播", True, (200,200,255)), (TIMELINE_X+TIMELINE_W+14, TIMELINE_Y+22))

        # 空格指示
        sp_label = "空格" if not self.playing else ("暂停中" if self.paused else "播放中")
        sp_color = (200,200,200) if not self.playing else ((255,200,100) if self.paused else (100,255,100))
        self.screen.blit(self.fs.render(sp_label, True, sp_color), (TIMELINE_X+TIMELINE_W+75, TIMELINE_Y+22))

    def _draw_panel(self):
        x, y = PANEL_X, PANEL_Y
        pygame.draw.rect(self.screen, (35,35,50), (x, y, PANEL_W, 500))
        pygame.draw.rect(self.screen, (80,80,100), (x, y, PANEL_W, 500), 1)

        # 模式切换按钮
        bw = PANEL_W//2 - 6
        d_bg = (80,120,60) if self.mode=="design" else (50,50,65)
        dr = pygame.Rect(x+4, y+4, bw, 30)
        pygame.draw.rect(self.screen, d_bg, dr)
        pygame.draw.rect(self.screen, (120,200,80) if self.mode=="design" else (100,100,120), dr, 2)
        self.screen.blit(self.fm.render("🎨 设计模式", True, (255,255,255) if self.mode=="design" else (160,160,160)), (x+10, y+7))

        e_bg = (80,120,60) if self.mode=="detail" else (50,50,65)
        er = pygame.Rect(x+bw+8, y+4, bw, 30)
        pygame.draw.rect(self.screen, e_bg, er)
        pygame.draw.rect(self.screen, (120,200,80) if self.mode=="detail" else (100,100,120), er, 2)
        self.screen.blit(self.fm.render("🔍 细节模式", True, (255,255,255) if self.mode=="detail" else (160,160,160)), (x+bw+14, y+7))

        # ── 搜索框 (模式按钮下方) ──
        search_box = pygame.Rect(x+5, y+36, 140, 22)
        search_bg = (60, 60, 80) if self.input_active and self.input_field=="search" else (45, 45, 58)
        pygame.draw.rect(self.screen, search_bg, search_box)
        pygame.draw.rect(self.screen, (120, 120, 150), search_box, 1)
        st = self.fs.render(f"🔎 {self.input_text if (self.input_active and self.input_field=='search') else ''}", True, (200,200,200))
        self.screen.blit(st, (x+10, y+10))

        if self.mode == "design":
            self._draw_design_help(x, y+62)
        else:
            self._draw_detail_panel(x, y+62)

    def _draw_design_help(self, x, y):
        for i, line in enumerate([
            "📋 设计模式 — 操作说明",
            "  左键点击画布 → 放置新子弹",
            "  左键点击已有子弹 → 进入细节编辑",
            "  右键点击子弹 → 删除",
            "  点击时间线 → 切换放置帧",
            "",
            "放好子弹后，点击它进入细节模式",
            "设置轨迹、速度、消亡时间等参数。",
        ]):
            c = (200,200,200) if not line.startswith("  ") else (150,150,170)
            self.screen.blit(self.fs.render(line, True, c), (x+10, y+i*20))

    def _draw_detail_panel(self, x, y):
        if self.edit_idx < 0 or self.edit_idx >= len(self.pattern.events):
            self.screen.blit(self.fm.render("未选中子弹 — 在设计模式点击一个子弹", True, (150,150,160)), (x+10, y))
            return

        e = self.pattern.events[self.edit_idx]
        self.screen.blit(self.fl.render(f"编辑子弹 #{self.edit_idx}", True, (255,255,100)), (x+10, y))

        # 删除按钮
        del_btn = pygame.Rect(x + PANEL_W - 120, y - 8, 116, 28)
        pygame.draw.rect(self.screen, (120, 30, 30), del_btn)
        pygame.draw.rect(self.screen, (200, 60, 60), del_btn, 2)
        self.screen.blit(self.fm.render("🗑 删除", True, (255, 200, 200)), (del_btn.x + 28, del_btn.y + 3))

        # ── 弹幕类型按钮 ──
        type_btn = pygame.Rect(x+5, y+28, 280, 28)
        pygame.draw.rect(self.screen, (55,55,70), type_btn)
        pygame.draw.rect(self.screen, e.color, type_btn, 2)
        self.screen.blit(self.fm.render(f"弹幕类型: {BTYPES[e.btype][0]}  (点击切换)", True, (220,220,220)), (x+12, y+31))

        # ── 轨迹类型按钮 ──
        traj_btn = pygame.Rect(x+295, y+28, 300, 28)
        pygame.draw.rect(self.screen, (55,55,70), traj_btn)
        pygame.draw.rect(self.screen, (100,200,255), traj_btn, 2)
        self.screen.blit(self.fm.render(f"轨迹: {TRAJ_NAMES[e.trajectory]}  (点击切换)", True, (220,220,220)), (x+302, y+31))

        # 参数（在类型/轨迹按钮下方）
        px = x+5
        py = y + 65
        self.screen.blit(self.fs.render("参数:", True, (170,170,180)), (px+5, py)); py += 20

        lines = [
            f"1.出现帧: {e.spawn_frame}  [W/S微调]",
            f"2.存活帧: {e.lifetime}  [E/D微调]",
            f"3.速度:   {e.speed:.1f} px/f  [Q/A微调]",
            f"  方向角: {e.angle:.0f}° (画布拖拽)",
            f"  数量: {e.count}",
            f"  散射角: {e.spread_angle}°",
            f"  曲线振幅: {e.curve_amp}",
            f"  曲线频率: {e.curve_freq:.1f}",
            f"  伤害: {e.damage}",
        ]
        for i, line in enumerate(lines):
            c = (200, 210, 200)
            # 高亮可点击的行
            if i == 1: c = (150, 220, 150)  # 存活帧
            if i == 2: c = (150, 220, 150)  # 速度
            self.screen.blit(self.fs.render(line, True, c), (px+5, py))
            py += 20

        guide = self.fs.render("画布上拖拽→设置方向向量", True, (255,200,100))
        self.screen.blit(guide, (px+5, py+5))

        # 输入时的提示
        if self.input_active:
            inp = self.fm.render(f"输入: {self.input_text}_  (Enter确认 Esc取消)", True, (255, 255, 100))
            self.screen.blit(inp, (px+5, py+30))

    def _draw_status(self):
        y = WINDOW_H-22
        pygame.draw.line(self.screen, (60,60,80), (0,y), (WINDOW_W,y))
        st = f"模式: {'设计' if self.mode=='design' else '细节'}"
        if self.edit_idx>=0: st += f" | 编辑:#{self.edit_idx}"
        st += f" | 子弹:{len(self.pattern.events)} | 时长:{self.pattern.duration/60:.1f}s | 空格:播放 Esc:回设计模式"
        self.screen.blit(self.fs.render(st, True, (130,130,150)), (10, y+3))
        if self.msg:
            s = pygame.Surface((WINDOW_W-40, 30), pygame.SRCALPHA); s.fill((0,0,0,160))
            self.screen.blit(s, (20, WINDOW_H-60))
            self.screen.blit(self.fm.render(self.msg, True, (255,255,120)), (30, WINDOW_H-58))

if __name__ == "__main__":
    Designer().run()
