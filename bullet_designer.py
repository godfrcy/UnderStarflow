"""
弹幕设计器 v2 (Bullet Pattern Designer)
=======================================
面向 Under Starflow 的可视化弹幕模式编辑器。

两模式操作：
  设计模式 (Tab)  — 在画布上点击放置子弹初始位置
  细节模式 (Tab)  — 选中子弹后设置消亡时间、轨迹类型、速度

导出 JSON 到 assetsDB/patterns/，游戏用 @pattern_name 引用。

键位：
  空格    播放/暂停预览
  方向键  控制灵魂
  Tab     切换设计/细节模式
  Delete  删除选中子弹
  Ctrl+S  保存
"""

import pygame
import json
import os
import math
import random
import sys

# ─── 常量 ───────────────────────────────────────────────
WINDOW_W, WINDOW_H = 1100, 680
CANVAS_W, CANVAS_H = 400, 300
CANVAS_X, CANVAS_Y = 20, 50
GRID = 20
TIMELINE_Y = 530
TIMELINE_X = 20
TIMELINE_W = 400
TIMELINE_H = 36
PANEL_X = 460
PANEL_Y = 50
PANEL_W = 620
HEART_SIZE = 14
FPS = 60
MAX_DURATION = 480  # 8 秒

# 弹幕类型预设
BTYPES = {
    "normal":       ("● 普通子弹", (255, 255, 255), (10, 10)),
    "laser":        ("▌ 延时激光", (255, 80, 80),   (24, 240)),
    "cube":         ("■ 方块",     (200, 200, 100), (24, 24)),
    "circle":       ("◎ 圆环",     (100, 200, 255), (8, 8)),
    "plasma_blade": ("▬ 等离子刃", (0, 255, 255),   (80, 8)),
    "laser_net":    ("┅ 激光网",   (0, 120, 255),   (400, 6)),
    "yellow_line":  ("─ 黄线",     (255, 255, 0),   (36, 4)),
    "homing":       ("⊕ 追踪弹",   (255, 140, 100), (12, 12)),
}

# 轨迹类型
TRAJECTORIES = ["straight", "curve_sin", "curve_arc", "homing", "spread"]

# ─── 字体 ───────────────────────────────────────────────
def _get_font(size):
    for p in [r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc"]:
        if os.path.exists(p):
            return pygame.font.Font(p, size)
    return pygame.font.Font(None, size)

# ─── 数据模型 ──────────────────────────────────────────
class BulletEvent:
    def __init__(self, x=200, y=20):
        self.x = x; self.y = y
        self.spawn_frame = 0       # 出现时机（帧）
        self.lifetime = 120        # 存活帧数（最大480）
        self.btype = "normal"
        self.w, self.h = 10, 10
        self.color = [255, 255, 255]
        self.trajectory = "straight"
        self.speed = 3.0           # 像素/帧
        self.angle = 90            # 方向角度 (0=右, 90=下, 180=左, 270=上)
        self.curve_amp = 40        # 曲线振幅
        self.curve_freq = 3.0      # 曲线频率
        self.count = 1             # 同帧生成数量
        self.spread_angle = 30     # 散射角度
        self.damage = 1
        self.note = ""

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d):
        e = cls()
        for k, v in d.items():
            if hasattr(e, k):
                setattr(e, k, v)
        return e

    def get_velocity(self, frame_offset=0):
        """根据轨迹类型和时间偏移计算速度向量"""
        rad = math.radians(self.angle)
        base_vx = math.cos(rad) * self.speed
        base_vy = math.sin(rad) * self.speed

        if self.trajectory == "straight":
            return base_vx, base_vy
        elif self.trajectory == "curve_sin":
            # 正弦波：垂直方向叠加振荡
            phase = frame_offset * 0.1 * self.curve_freq
            osc = math.sin(phase) * self.curve_amp * 0.3
            return base_vx + osc, base_vy
        elif self.trajectory == "curve_arc":
            # 弧线：逐渐弯曲
            bend = frame_offset * 0.02 * self.curve_freq
            return base_vx + math.sin(bend) * self.curve_amp * 0.2, base_vy
        elif self.trajectory == "homing":
            return 0, 0  # homing is handled differently in-game
        elif self.trajectory == "spread":
            return base_vx, base_vy
        return base_vx, base_vy

class Pattern:
    def __init__(self, name="new_pattern"):
        self.name = name
        self.duration = MAX_DURATION
        self.description = ""
        self.events = []

    def to_dict(self):
        return {
            "name": self.name, "duration": self.duration,
            "description": self.description,
            "events": [e.to_dict() for e in self.events]
        }

    @classmethod
    def from_dict(cls, d):
        p = cls(d.get("name", "loaded"))
        p.duration = d.get("duration", MAX_DURATION)
        p.description = d.get("description", "")
        p.events = [BulletEvent.from_dict(e) for e in d.get("events", [])]
        return p

# ─── 编辑器 ────────────────────────────────────────────
class Designer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("弹幕设计器 v2 — Design / Detail 模式")
        self.clock = pygame.time.Clock()
        self.running = True

        self.fs = _get_font(14)
        self.fm = _get_font(18)
        self.fl = _get_font(24)

        self.pattern = Pattern()
        self.selected_idx = -1
        self.mode = "design"       # "design" | "detail"
        self.playing = False
        self.play_frame = 0
        self.heart = [CANVAS_W // 2, CANVAS_H // 2]
        self.preview_bullets = []
        self.dragging = None
        self.msg = ""
        self.msg_timer = 0
        self.patterns_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assetsDB", "patterns")

        # 画布
        self.canvas = pygame.Surface((CANVAS_W, CANVAS_H))
        self.grid_surf = self._make_grid()

    def _make_grid(self):
        s = pygame.Surface((CANVAS_W, CANVAS_H), pygame.SRCALPHA)
        for x in range(0, CANVAS_W, GRID):
            pygame.draw.line(s, (50, 50, 60, 60), (x, 0), (x, CANVAS_H))
        for y in range(0, CANVAS_H, GRID):
            pygame.draw.line(s, (50, 50, 60, 60), (0, y), (CANVAS_W, y))
        return s

    def msg_show(self, m):
        self.msg = m; self.msg_timer = 120

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self._events()
            self._update()
            self._draw()
        pygame.quit()

    # ─── 输入 ──────────────────────────────────────────
    def _events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                self._key(ev)
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                self._mousedown(ev)
            elif ev.type == pygame.MOUSEBUTTONUP:
                self.dragging = None
            elif ev.type == pygame.MOUSEMOTION:
                self._mousemove(ev)

    def _key(self, ev):
        k = ev.key
        if k == pygame.K_SPACE:
            self._toggle_play()
        elif k == pygame.K_TAB:
            self.mode = "detail" if self.mode == "design" else "design"
            self.msg_show(f"切换到 {'细节模式' if self.mode == 'detail' else '设计模式'}")
        elif k == pygame.K_DELETE and self.selected_idx >= 0:
            del self.pattern.events[self.selected_idx]
            self.selected_idx = -1
            self.msg_show("已删除")
        elif k == pygame.K_ESCAPE:
            self.selected_idx = -1
        elif k == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self._save()
        elif k == pygame.K_o and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self._load_first()
        elif k == pygame.K_r and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.pattern = Pattern()
            self.selected_idx = -1
            self.msg_show("已重置")
        elif k in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT) and self.playing:
            sp = 4
            if k == pygame.K_LEFT:  self.heart[0] -= sp
            if k == pygame.K_RIGHT: self.heart[0] += sp
            if k == pygame.K_UP:    self.heart[1] -= sp
            if k == pygame.K_DOWN:  self.heart[1] += sp
            self.heart[0] = max(0, min(self.heart[0], CANVAS_W))
            self.heart[1] = max(0, min(self.heart[1], CANVAS_H))
        # 细节模式：调整参数
        if self.mode == "detail" and self.selected_idx >= 0:
            evt = self.pattern.events[self.selected_idx]
            step = 5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1
            if k == pygame.K_LEFT:  evt.x -= step
            if k == pygame.K_RIGHT: evt.x += step
            if k == pygame.K_UP:    evt.y -= step
            if k == pygame.K_DOWN:  evt.y += step
            if k == pygame.K_w:     evt.spawn_frame = max(0, evt.spawn_frame - step * 5)
            if k == pygame.K_s:     evt.spawn_frame = min(MAX_DURATION, evt.spawn_frame + step * 5)
            if k == pygame.K_e:     evt.lifetime = max(1, evt.lifetime - step * 10)
            if k == pygame.K_d:     evt.lifetime = min(MAX_DURATION, evt.lifetime + step * 10)
            if k == pygame.K_q:     evt.speed = max(0.5, evt.speed - 0.5)
            if k == pygame.K_a:     evt.speed = min(20, evt.speed + 0.5)

    def _mousedown(self, ev):
        mx, my = ev.pos
        btn = ev.button
        in_canvas = CANVAS_X <= mx <= CANVAS_X + CANVAS_W and CANVAS_Y <= my <= CANVAS_Y + CANVAS_H
        in_timeline = TIMELINE_X <= mx <= TIMELINE_X + TIMELINE_W and TIMELINE_Y <= my <= TIMELINE_Y + TIMELINE_H
        in_panel = PANEL_X <= mx <= PANEL_X + PANEL_W

        if in_canvas and btn == 1:
            cx, cy = mx - CANVAS_X, my - CANVAS_Y
            if self.mode == "design":
                # 放置新子弹
                e = BulletEvent(int(cx), int(cy))
                e.spawn_frame = self.play_frame
                self.pattern.events.append(e)
                self.selected_idx = len(self.pattern.events) - 1
                self.msg_show(f"放置子弹 #{self.selected_idx} at ({e.x},{e.y}) 帧{e.spawn_frame}")
            elif self.mode == "detail":
                # 选中已有子弹
                found = self._find_event(cx, cy)
                if found is not None:
                    self.selected_idx = found
                    self.dragging = found
                    self.msg_show(f"选中 #{found}")
                else:
                    self.selected_idx = -1

        elif in_timeline and btn == 1:
            tx = mx - TIMELINE_X
            self.play_frame = int((tx / TIMELINE_W) * self.pattern.duration)

        elif in_panel and btn == 1:
            self._panel_click(mx, my)

    def _mousemove(self, ev):
        if self.dragging is not None:
            mx, my = ev.pos
            if CANVAS_X <= mx <= CANVAS_X + CANVAS_W and CANVAS_Y <= my <= CANVAS_Y + CANVAS_H:
                self.pattern.events[self.dragging].x = max(0, min(int(mx - CANVAS_X), CANVAS_W))
                self.pattern.events[self.dragging].y = max(0, min(int(my - CANVAS_Y), CANVAS_H))

    def _find_event(self, cx, cy):
        best, best_d = None, 20
        for i, e in enumerate(self.pattern.events):
            d = math.hypot(e.x - cx, e.y - cy)
            if d < best_d:
                best_d = d; best = i
        return best

    def _panel_click(self, mx, my):
        """处理面板点击：模式切换、弹幕类型、轨迹类型"""
        ry = my - PANEL_Y
        rx = mx - PANEL_X

        # ── 顶部模式切换按钮 ──
        if 5 <= ry <= 38:
            if rx <= PANEL_W // 2:
                self.mode = "design"
                self.msg_show("切换到设计模式 — 点击画布放置子弹")
            else:
                self.mode = "detail"
                self.msg_show("切换到细节模式 — 点击子弹编辑轨迹")
            return

        if self.mode != "detail" or self.selected_idx < 0:
            return

        evt = self.pattern.events[self.selected_idx]

        # ── 弹幕类型（左列）──
        btypes = list(BTYPES.keys())
        for i, t in enumerate(btypes):
            by = 66 + i * 25
            if 5 <= rx <= 190 and by <= ry <= by + 22:
                evt.btype = t
                evt.w, evt.h = BTYPES[t][2]
                evt.color = list(BTYPES[t][1])
                self.msg_show(f"类型: {BTYPES[t][0]}")
                return

        # ── 轨迹类型（中列）──
        for i, t in enumerate(TRAJECTORIES):
            by = 66 + i * 25
            if 205 <= rx <= 390 and by <= ry <= by + 22:
                evt.trajectory = t
                self.msg_show(f"轨迹: {t}")
                return

    # ─── 更新 ──────────────────────────────────────────
    def _update(self):
        if self.msg_timer > 0:
            self.msg_timer -= 1
        if self.playing:
            self.play_frame += 1
            if self.play_frame >= self.pattern.duration:
                self.playing = False
                self.preview_bullets.clear()
            self._spawn_preview()
            self._update_preview()

    def _spawn_preview(self):
        for evt in self.pattern.events:
            if evt.spawn_frame == self.play_frame:
                for i in range(evt.count):
                    angle_off = (i - (evt.count - 1) / 2) * evt.spread_angle
                    rad = math.radians(evt.angle + angle_off)
                    spd = evt.speed
                    self.preview_bullets.append({
                        "x": evt.x, "y": evt.y,
                        "vx": math.cos(rad) * spd,
                        "vy": math.sin(rad) * spd,
                        "w": evt.w, "h": evt.h,
                        "color": evt.color, "type": evt.btype,
                        "life": evt.lifetime,
                        "traj": evt.trajectory,
                        "amp": evt.curve_amp, "freq": evt.curve_freq,
                        "born": self.play_frame,
                    })

    def _update_preview(self):
        for b in self.preview_bullets[:]:
            age = self.play_frame - b["born"]
            if b["traj"] == "curve_sin":
                b["vx"] += math.sin(age * 0.05 * (b["freq"] / 3)) * b["amp"] * 0.03
            elif b["traj"] == "curve_arc":
                b["vy"] += 0.05

            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["life"] -= 1
            if b["life"] <= 0 or b["x"] < -60 or b["x"] > CANVAS_W + 60 or b["y"] < -60 or b["y"] > CANVAS_H + 60:
                self.preview_bullets.remove(b)

    def _toggle_play(self):
        self.playing = not self.playing
        if self.playing:
            self.play_frame = 0
            self.preview_bullets.clear()
            self.heart = [CANVAS_W // 2, CANVAS_H // 2]
        else:
            self.preview_bullets.clear()

    def _save(self):
        os.makedirs(self.patterns_dir, exist_ok=True)
        name = self.pattern.name.replace(" ", "_").lower()
        path = os.path.join(self.patterns_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.pattern.to_dict(), f, ensure_ascii=False, indent=2)
        self.msg_show(f"已保存: {path}")

    def _load_first(self):
        os.makedirs(self.patterns_dir, exist_ok=True)
        files = [f for f in os.listdir(self.patterns_dir) if f.endswith(".json")]
        if files:
            path = os.path.join(self.patterns_dir, files[0])
            with open(path, "r", encoding="utf-8") as f:
                self.pattern = Pattern.from_dict(json.load(f))
            self.selected_idx = -1
            self.msg_show(f"已加载: {files[0]}")
        else:
            self.msg_show("没有已保存的模式")

    # ─── 绘制 ──────────────────────────────────────────
    def _draw(self):
        self.screen.fill((25, 25, 38))
        self._draw_canvas()
        self._draw_timeline()
        if self.mode == "detail":
            self._draw_detail_panel()
        else:
            self._draw_design_panel()
        self._draw_status()
        pygame.display.flip()

    def _draw_canvas(self):
        # 边框
        pygame.draw.rect(self.screen, (80, 80, 100),
                         (CANVAS_X - 2, CANVAS_Y - 2, CANVAS_W + 4, CANVAS_H + 4), 2)

        # 填充
        self.canvas.fill((12, 12, 20))
        self.canvas.blit(self.grid_surf, (0, 0))

        # 绘制弹幕事件
        for i, evt in enumerate(self.pattern.events):
            sel = i == self.selected_idx
            col = (255, 220, 60) if sel else evt.color
            r = 6 if sel else 4
            pygame.draw.circle(self.canvas, col, (int(evt.x), int(evt.y)), r)
            if sel:
                pygame.draw.circle(self.canvas, (255, 255, 255), (int(evt.x), int(evt.y)), r + 2, 1)
            # 显示编号
            label = self.fs.render(str(i), True, (200, 200, 200))
            self.canvas.blit(label, (evt.x + 8, evt.y - 6))

        # 预览子弹
        for b in self.preview_bullets:
            c = b["color"]
            if b["type"] in ("laser", "laser_net"):
                r = pygame.Rect(b["x"] - b["w"] // 2, b["y"] - b["h"] // 2, b["w"], b["h"])
                pygame.draw.rect(self.canvas, c, r, 1)
            else:
                pygame.draw.circle(self.canvas, c, (int(b["x"]), int(b["y"])), max(3, b["w"] // 2))

        # 灵魂（预览时）
        if self.playing:
            hx, hy = int(self.heart[0]), int(self.heart[1])
            pygame.draw.rect(self.canvas, (255, 50, 50),
                             (hx - HEART_SIZE // 2, hy - HEART_SIZE // 2, HEART_SIZE, HEART_SIZE))
            pygame.draw.rect(self.canvas, (255, 255, 255),
                             (hx - HEART_SIZE // 2, hy - HEART_SIZE // 2, HEART_SIZE, HEART_SIZE), 1)

        self.screen.blit(self.canvas, (CANVAS_X, CANVAS_Y))

        # 画布标签
        mode_label = self.fm.render(
            "🎨 设计模式 — 点击画布放置子弹" if self.mode == "design" else "🔍 细节模式 — 点击画布选中子弹，面板编辑轨迹",
            True, (180, 180, 200))
        self.screen.blit(mode_label, (CANVAS_X, CANVAS_Y - 24))

    def _draw_timeline(self):
        r = pygame.Rect(TIMELINE_X, TIMELINE_Y, TIMELINE_W, TIMELINE_H)
        pygame.draw.rect(self.screen, (35, 35, 52), r)
        pygame.draw.rect(self.screen, (80, 80, 100), r, 1)

        # 播放头
        px = TIMELINE_X + int((self.play_frame / self.pattern.duration) * TIMELINE_W)
        pygame.draw.line(self.screen, (255, 60, 60), (px, TIMELINE_Y), (px, TIMELINE_Y + TIMELINE_H), 2)

        # 标记
        for i, evt in enumerate(self.pattern.events):
            ex = TIMELINE_X + int((evt.spawn_frame / self.pattern.duration) * TIMELINE_W)
            col = (255, 220, 60) if i == self.selected_idx else (100, 180, 255)
            pygame.draw.circle(self.screen, col, (ex, TIMELINE_Y + TIMELINE_H // 2), 5)

        # 文本
        txt = self.fm.render(f"帧: {self.play_frame}/{self.pattern.duration}  [{self.pattern.duration/60:.1f}s]", True, (200, 200, 200))
        self.screen.blit(txt, (TIMELINE_X + TIMELINE_W + 12, TIMELINE_Y + 2))
        btn = self.fm.render("⏸ 暂停" if self.playing else "▶ 播放", True, (200, 150, 50) if self.playing else (100, 200, 100))
        self.screen.blit(btn, (TIMELINE_X + TIMELINE_W + 12, TIMELINE_Y + 22))

    def _draw_design_panel(self):
        """设计模式面板：操作提示"""
        x, y = PANEL_X, PANEL_Y
        pygame.draw.rect(self.screen, (35, 35, 50), (x, y, PANEL_W, 280))
        pygame.draw.rect(self.screen, (80, 80, 100), (x, y, PANEL_W, 280), 1)

        self._draw_mode_buttons(x, y)

        lines = [
            "",
            "📋 设计模式操作",
            "  点击画布 → 放置子弹初始位置",
            "  点击时间线 → 跳到指定帧",
            "",
            "放置后点击「细节模式」，",
            "可编辑每个子弹的轨迹和参数。",
            "",
            "⏎ 键位速查:",
            "  空格 播放/暂停   方向键 控灵魂",
            "  Delete 删除     Ctrl+S 保存",
            "  Ctrl+O 加载     Ctrl+R 重置",
        ]
        for i, line in enumerate(lines):
            c = (200, 200, 200) if not line.startswith("  ") else (150, 150, 170)
            lbl = self.fs.render(line, True, c)
            self.screen.blit(lbl, (x + 10, y + 45 + i * 20))

    def _draw_detail_panel(self):
        """细节模式面板：编辑选中子弹的参数"""
        x, y = PANEL_X, PANEL_Y
        pygame.draw.rect(self.screen, (35, 35, 50), (x, y, PANEL_W, 500))
        pygame.draw.rect(self.screen, (80, 80, 100), (x, y, PANEL_W, 500), 1)

        # ── 模式切换按钮 ──
        self._draw_mode_buttons(x, y)

        if self.selected_idx < 0 or self.selected_idx >= len(self.pattern.events):
            lbl = self.fm.render("未选中子弹 — 去画布上点击一个子弹", True, (150, 150, 160))
            self.screen.blit(lbl, (x + 10, y + 50))
            return

        evt = self.pattern.events[self.selected_idx]

        # 标题
        title = self.fl.render(f"子弹 #{self.selected_idx}", True, (255, 255, 100))
        self.screen.blit(title, (x + 10, y + 44))

        cy = y + 66

        # 弹幕类型（左侧列）
        self.screen.blit(self.fs.render("─ 弹幕类型 ─", True, (170, 170, 180)), (x + 5, cy)); cy += 20
        for t in BTYPES:
            bg = (70, 50, 20) if evt.btype == t else (45, 45, 60)
            r = pygame.Rect(x + 5, cy, 185, 22)
            pygame.draw.rect(self.screen, bg, r)
            if evt.btype == t:
                pygame.draw.rect(self.screen, BTYPES[t][1], r, 2)
            lbl = self.fs.render(BTYPES[t][0], True, BTYPES[t][1])
            self.screen.blit(lbl, (x + 10, cy + 2))
            cy += 25

        # 轨迹类型（中间列）
        tx = x + 200
        cy2 = y + 66
        self.screen.blit(self.fs.render("─ 轨迹 ─", True, (170, 170, 180)), (tx + 5, cy2)); cy2 += 20
        traj_labels = {
            "straight": "→ 直线", "curve_sin": "∿ 正弦波",
            "curve_arc": "⌒ 弧线", "homing": "⊕ 追踪", "spread": "⌔ 散射"
        }
        for t in TRAJECTORIES:
            bg = (70, 50, 20) if evt.trajectory == t else (45, 45, 60)
            r = pygame.Rect(tx + 5, cy2, 185, 22)
            pygame.draw.rect(self.screen, bg, r)
            if evt.trajectory == t:
                pygame.draw.rect(self.screen, (100, 200, 255), r, 2)
            lbl = self.fs.render(traj_labels.get(t, t), True, (200, 200, 200))
            self.screen.blit(lbl, (tx + 10, cy2 + 2))
            cy2 += 25

        # 参数区域（右侧列）
        px = x + 400
        py = y + 66
        self.screen.blit(self.fs.render("─ 参数 ─", True, (170, 170, 180)), (px + 5, py)); py += 22

        params = [
            f"出现帧: {evt.spawn_frame}  (W/S调整)",
            f"存活帧: {evt.lifetime}  (E/D调整)",
            f"速度:   {evt.speed:.1f} px/f  (Q/A调整)",
            f"方向角: {evt.angle}°",
            f"数量:   {evt.count}",
            f"散射角: {evt.spread_angle}°",
            f"曲线振幅: {evt.curve_amp}",
            f"曲线频率: {evt.curve_freq:.1f}",
            f"伤害:   {evt.damage}",
        ]
        if evt.note:
            params.append(f"备注: {evt.note}")

        for line in params:
            lbl = self.fs.render(line, True, (200, 210, 200))
            self.screen.blit(lbl, (px + 5, py))
            py += 20

        coord = self.fs.render(f"坐标: ({evt.x}, {evt.y})  拖拽画布或方向键微调", True, (140, 140, 160))
        self.screen.blit(coord, (px + 5, py + 10))

    def _draw_mode_buttons(self, x, y):
        """绘制设计/细节模式切换按钮"""
        bw = PANEL_W // 2 - 6
        # 设计按钮
        d_bg = (80, 120, 60) if self.mode == "design" else (50, 50, 65)
        dr = pygame.Rect(x + 4, y + 4, bw, 30)
        pygame.draw.rect(self.screen, d_bg, dr)
        pygame.draw.rect(self.screen, (120, 200, 80) if self.mode == "design" else (100, 100, 120), dr, 2)
        dl = self.fm.render("🎨 设计模式", True, (255, 255, 255) if self.mode == "design" else (160, 160, 160))
        self.screen.blit(dl, (x + 10, y + 7))

        # 细节按钮
        e_bg = (80, 120, 60) if self.mode == "detail" else (50, 50, 65)
        er = pygame.Rect(x + bw + 8, y + 4, bw, 30)
        pygame.draw.rect(self.screen, e_bg, er)
        pygame.draw.rect(self.screen, (120, 200, 80) if self.mode == "detail" else (100, 100, 120), er, 2)
        el = self.fm.render("🔍 细节模式", True, (255, 255, 255) if self.mode == "detail" else (160, 160, 160))
        self.screen.blit(el, (x + bw + 14, y + 7))

    def _draw_status(self):
        y = WINDOW_H - 22
        pygame.draw.line(self.screen, (60, 60, 80), (0, y), (WINDOW_W, y))
        st = f"模式: {'设计' if self.mode == 'design' else '细节'} | 子弹数: {len(self.pattern.events)} | 时长: {self.pattern.duration}帧 ({self.pattern.duration/60:.1f}s) | 点击右上角按钮切换模式"
        lbl = self.fs.render(st, True, (130, 130, 150))
        self.screen.blit(lbl, (10, y + 3))

        if self.msg:
            s = pygame.Surface((WINDOW_W - 40, 30), pygame.SRCALPHA)
            s.fill((0, 0, 0, 160))
            self.screen.blit(s, (20, WINDOW_H - 60))
            self.screen.blit(self.fm.render(self.msg, True, (255, 255, 120)), (30, WINDOW_H - 58))


if __name__ == "__main__":
    Designer().run()
