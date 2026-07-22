"""
弹幕设计器 (Bullet Pattern Designer)
=====================================
面向 Under Starflow 的可视化弹幕模式编辑器。
在等同游戏战斗区域的画布上设计弹幕，实时预览，导出 JSON 供游戏加载。

操作:
  鼠标: 画布上拖拽放置弹幕起点，时间线选择帧，属性面板修改参数
  键盘: 空格播放/暂停，方向键控制灵魂，1-8切换弹幕类型
  文件: 导出 JSON 到 assetsDB/patterns/
"""

import pygame
import json
import os
import math
import random
from datetime import datetime

# ─── 常量 ───────────────────────────────────────────────
WINDOW_W, WINDOW_H = 1100, 650
CANVAS_W, CANVAS_H = 400, 300        # 等同游戏 battle_box
CANVAS_OFFSET_X = 20
CANVAS_OFFSET_Y = 50
GRID_SIZE = 20                        # 网格大小
TIMELINE_Y = 520                      # 时间线 Y 位置
TIMELINE_X = CANVAS_OFFSET_X
TIMELINE_W = CANVAS_W
TIMELINE_H = 40
PANEL_X = CANVAS_OFFSET_X + CANVAS_W + 40
PANEL_Y = 50
PANEL_W = 240
HEART_SIZE = 16

FPS = 60
DEFAULT_DURATION = 480                # 默认 8 秒

# 弹幕类型定义
BULLET_TYPES = {
    "normal":       {"name": "普通子弹", "color": (255, 255, 255), "size": (10, 10), "icon": "●"},
    "laser":        {"name": "延时激光", "color": (255, 0, 0),     "size": (20, 200),"icon": "▌"},
    "cube":         {"name": "方块",     "color": (200, 200, 100), "size": (24, 24), "icon": "■"},
    "circle":       {"name": "圆形弹幕", "color": (100, 200, 255), "size": (8, 8),   "icon": "◎"},
    "plasma_blade": {"name": "等离子刃", "color": (0, 255, 255),   "size": (60, 8),  "icon": "▬"},
    "laser_network": {"name": "激光网",  "color": (0, 100, 255),   "size": (400, 4), "icon": "┅"},
    "yellow_line":  {"name": "黄线",     "color": (255, 255, 0),   "size": (30, 4),  "icon": "─"},
    "targeted":     {"name": "追踪弹",   "color": (255, 100, 100), "size": (12, 12), "icon": "⊕"},
}

# ─── 字体 ───────────────────────────────────────────────
def get_font(size):
    """简单的字体加载（不需要游戏引擎的字体系统）"""
    font_paths = [
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
    ]
    for p in font_paths:
        if os.path.exists(p):
            return pygame.font.Font(p, size)
    return pygame.font.Font(None, size)


# ─── BulletEvent ────────────────────────────────────────
class BulletEvent:
    """单个弹幕生成事件"""
    def __init__(self, time=0, btype="normal"):
        self.time = time
        self.btype = btype
        self.count = 1
        self.interval = 0        # 0 = 同时生成; >0 = 每隔N帧生成一个
        self.x = 200             # 画布内 X (0-400)
        self.y = 0               # 画布内 Y (0-300)
        self.vx = 0.0            # X 速度
        self.vy = 3.0            # Y 速度
        self.width = BULLET_TYPES[btype]["size"][0]
        self.height = BULLET_TYPES[btype]["size"][1]
        self.color = list(BULLET_TYPES[btype]["color"])
        self.damage = 1
        self.warning = 60        # laser 预警帧数
        self.tracking = False    # laser 追踪
        self.direction = 1       # plasma_blade 方向
        self.axis = "h"          # laser_network 轴向
        self.spread_angle = 0    # 散射角度
        self.note = ""           # 自定义备注

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d):
        e = cls(d.get("time", 0), d.get("btype", "normal"))
        for k, v in d.items():
            if hasattr(e, k):
                setattr(e, k, v)
        return e


# ─── BulletPattern ──────────────────────────────────────
class BulletPattern:
    """弹幕模式：一组 BulletEvent + 元数据"""
    def __init__(self, name="new_pattern"):
        self.name = name
        self.duration = DEFAULT_DURATION
        self.events = []
        self.description = ""

    def to_dict(self):
        return {
            "name": self.name,
            "duration": self.duration,
            "description": self.description,
            "events": [e.to_dict() for e in self.events]
        }

    @classmethod
    def from_dict(cls, d):
        p = cls(d.get("name", "loaded"))
        p.duration = d.get("duration", DEFAULT_DURATION)
        p.description = d.get("description", "")
        p.events = [BulletEvent.from_dict(e) for e in d.get("events", [])]
        return p


# ─── 编辑器主类 ──────────────────────────────────────────
class BulletDesigner:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("弹幕设计器 - Bullet Pattern Designer")
        self.clock = pygame.time.Clock()
        self.running = True

        # 字体
        self.font_sm = get_font(14)
        self.font_md = get_font(18)
        self.font_lg = get_font(24)

        # 画布表面
        self.canvas_surf = pygame.Surface((CANVAS_W, CANVAS_H))
        self.grid_surf = self._make_grid_surf()

        # 当前模式
        self.pattern = BulletPattern()
        self.selected_idx = -1

        # 播放状态
        self.playing = False
        self.play_frame = 0
        self.heart_pos = [CANVAS_W // 2, CANVAS_H // 2]  # 灵魂位置（画布坐标）

        # 预览子弹（播放时生成的实际子弹实例）
        self.preview_bullets = []

        # 拖拽状态
        self.dragging_event = None  # 正在拖拽的 event
        self.drag_offset = (0, 0)
        self.timeline_drag = False

        # 消息
        self.message = ""
        self.message_timer = 0

        # 文件路径
        self.current_file = None
        self.patterns_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "assetsDB", "patterns")

    def _make_grid_surf(self):
        """生成网格覆盖图"""
        surf = pygame.Surface((CANVAS_W, CANVAS_H), pygame.SRCALPHA)
        for x in range(0, CANVAS_W, GRID_SIZE):
            pygame.draw.line(surf, (60, 60, 60, 80), (x, 0), (x, CANVAS_H))
        for y in range(0, CANVAS_H, GRID_SIZE):
            pygame.draw.line(surf, (60, 60, 60, 80), (0, y), (CANVAS_W, y))
        return surf

    def show_message(self, msg):
        self.message = msg
        self.message_timer = 180

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()
        pygame.quit()

    # ─── 事件处理 ────────────────────────────────────────
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                self._handle_key(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_down(event)

            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mouse_up(event)

            elif event.type == pygame.MOUSEMOTION:
                self._handle_mouse_move(event)

    def _handle_key(self, event):
        if event.key == pygame.K_SPACE:
            self._toggle_play()

        elif event.key == pygame.K_r and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self._reset()

        elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self._save()

        elif event.key == pygame.K_o and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self._load_dialog()

        elif event.key == pygame.K_e and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self._export()

        elif event.key == pygame.K_DELETE:
            self._delete_selected()

        elif event.key == pygame.K_ESCAPE:
            self.selected_idx = -1
            self.dragging_event = None

        elif event.key in range(pygame.K_1, pygame.K_9):
            self._quick_add_bullet(event.key - pygame.K_1)

        elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
            if self.playing:
                speed = 4
                k = event.key
                if k == pygame.K_LEFT:  self.heart_pos[0] -= speed
                if k == pygame.K_RIGHT: self.heart_pos[0] += speed
                if k == pygame.K_UP:    self.heart_pos[1] -= speed
                if k == pygame.K_DOWN:  self.heart_pos[1] += speed
                self.heart_pos[0] = max(0, min(self.heart_pos[0], CANVAS_W))
                self.heart_pos[1] = max(0, min(self.heart_pos[1], CANVAS_H))

        elif event.key == pygame.K_PAGEUP and self.selected_idx >= 0:
            self.pattern.events[self.selected_idx].time = max(0,
                self.pattern.events[self.selected_idx].time - 10)
        elif event.key == pygame.K_PAGEDOWN and self.selected_idx >= 0:
            self.pattern.events[self.selected_idx].time = min(self.pattern.duration,
                self.pattern.events[self.selected_idx].time + 10)

    def _handle_mouse_down(self, event):
        mx, my = event.pos

        # 检查画布区域
        if self._in_canvas(mx, my):
            cx, cy = mx - CANVAS_OFFSET_X, my - CANVAS_OFFSET_Y  # 画布坐标

            if event.button == 1:  # 左键：选中或放置
                found = self._find_event_at(cx, cy)
                if found is not None:
                    self.selected_idx = found
                    self.dragging_event = self.pattern.events[found]
                    self.drag_offset = (cx - self.dragging_event.x, cy - self.dragging_event.y)
                else:
                    # 新弹幕：在当前帧放置
                    btype = "normal"
                    evt = BulletEvent(self.play_frame, btype)
                    evt.x = int(cx)
                    evt.y = int(cy)
                    self.pattern.events.append(evt)
                    self.selected_idx = len(self.pattern.events) - 1
                    self.show_message(f"添加弹幕: {BULLET_TYPES[btype]['name']} at ({evt.x},{evt.y})")

            elif event.button == 3:  # 右键：删除
                found = self._find_event_at(cx, cy)
                if found is not None:
                    del self.pattern.events[found]
                    self.selected_idx = -1

        # 检查时间线区域
        elif self._in_timeline(mx, my):
            tx = mx - TIMELINE_X
            frame = int((tx / TIMELINE_W) * self.pattern.duration)
            self.play_frame = max(0, min(frame, self.pattern.duration))
            self.timeline_drag = True

        # 检查属性面板
        elif self._in_panel(mx, my):
            self._handle_panel_click(mx, my)

    def _handle_mouse_up(self, event):
        self.dragging_event = None
        self.timeline_drag = False

    def _handle_mouse_move(self, event):
        mx, my = event.pos

        if self.dragging_event and self._in_canvas(mx, my):
            cx, cy = mx - CANVAS_OFFSET_X, my - CANVAS_OFFSET_Y
            self.dragging_event.x = max(0, min(int(cx - self.drag_offset[0]), CANVAS_W))
            self.dragging_event.y = max(0, min(int(cy - self.drag_offset[1]), CANVAS_H))

        if self.timeline_drag:
            tx = max(0, min(mx - TIMELINE_X, TIMELINE_W))
            self.play_frame = int((tx / TIMELINE_W) * self.pattern.duration)

    # ─── 更新 ────────────────────────────────────────────
    def _update(self):
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""

        if self.playing:
            self.play_frame = (self.play_frame + 1) % (self.pattern.duration + 60)
            if self.play_frame >= self.pattern.duration:
                self.stop_playing()
            self._spawn_preview_bullets()
        self._update_preview_bullets()

    def _update_preview_bullets(self):
        for b in self.preview_bullets[:]:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["life"] -= 1
            # 边界删除
            if (b["life"] <= 0 or b["x"] < -50 or b["x"] > CANVAS_W + 50 or
                b["y"] < -50 or b["y"] > CANVAS_H + 50):
                self.preview_bullets.remove(b)

    def _spawn_preview_bullets(self):
        """在当前 play_frame 生成预览子弹"""
        for evt in self.pattern.events:
            if evt.interval > 0:
                # 间隔生成：检查播放帧是否匹配 (time + n*interval)
                offset = self.play_frame - evt.time
                if offset >= 0 and offset % evt.interval == 0 and offset // evt.interval < evt.count:
                    self._spawn_event_bullet(evt)
            else:
                # 单次生成
                if evt.time == self.play_frame:
                    self._spawn_event_bullet(evt)

    def _spawn_event_bullet(self, evt):
        """根据 BulletEvent 生成一个预览子弹"""
        for i in range(evt.count):
            offset_x = i * (evt.spread_angle * 5 if evt.spread_angle else 0)
            self.preview_bullets.append({
                "x": evt.x + offset_x,
                "y": evt.y,
                "vx": evt.vx,
                "vy": evt.vy,
                "w": evt.width,
                "h": evt.height,
                "color": evt.color,
                "type": evt.btype,
                "life": 300,
                "warning": evt.warning,
            })

    # ─── 碰撞检测辅助 ─────────────────────────────────────
    def _in_canvas(self, mx, my):
        return (CANVAS_OFFSET_X <= mx <= CANVAS_OFFSET_X + CANVAS_W and
                CANVAS_OFFSET_Y <= my <= CANVAS_OFFSET_Y + CANVAS_H)

    def _in_timeline(self, mx, my):
        return (TIMELINE_X <= mx <= TIMELINE_X + TIMELINE_W and
                TIMELINE_Y <= my <= TIMELINE_Y + TIMELINE_H)

    def _in_panel(self, mx, my):
        return (PANEL_X <= mx <= PANEL_X + PANEL_W and
                PANEL_Y <= my <= PANEL_Y + 400)

    def _find_event_at(self, cx, cy):
        """在画布坐标找最近的弹幕事件，返回索引"""
        best, best_dist = None, 30
        for i, evt in enumerate(self.pattern.events):
            dist = math.hypot(evt.x - cx, evt.y - cy)
            if dist < best_dist:
                best_dist = dist
                best = i
        return best

    # ─── 播放控制 ─────────────────────────────────────────
    def _toggle_play(self):
        if self.playing:
            self.stop_playing()
        else:
            self.start_playing()

    def start_playing(self):
        self.playing = True
        self.play_frame = 0
        self.preview_bullets = []
        self.heart_pos = [CANVAS_W // 2, CANVAS_H // 2]

    def stop_playing(self):
        self.playing = False
        self.preview_bullets = []

    def _reset(self):
        self.pattern = BulletPattern()
        self.selected_idx = -1
        self.playing = False
        self.play_frame = 0
        self.preview_bullets = []
        self.show_message("已重置")

    def _delete_selected(self):
        if self.selected_idx >= 0 and self.selected_idx < len(self.pattern.events):
            evt = self.pattern.events[self.selected_idx]
            del self.pattern.events[self.selected_idx]
            self.selected_idx = -1
            self.show_message(f"已删除弹幕事件")

    def _quick_add_bullet(self, idx):
        """数字键 1-8 快速添加弹幕到当前帧、画布中央"""
        types = list(BULLET_TYPES.keys())
        if idx < len(types):
            btype = types[idx]
            evt = BulletEvent(self.play_frame, btype)
            evt.x, evt.y = CANVAS_W // 2, 20
            self.pattern.events.append(evt)
            self.selected_idx = len(self.pattern.events) - 1
            self.show_message(f"添加 {BULLET_TYPES[btype]['name']}")

    # ─── 属性面板交互 ────────────────────────────────────
    def _handle_panel_click(self, mx, my):
        """简化：点击面板修改选中弹幕的类型"""
        if self.selected_idx < 0:
            return
        evt = self.pattern.events[self.selected_idx]
        rel_y = my - PANEL_Y
        # 弹幕类型按钮
        types = list(BULLET_TYPES.keys())
        btn_h = 28
        for i, t in enumerate(types):
            btn_y = 30 + i * btn_h
            if btn_y <= rel_y <= btn_y + btn_h:
                evt.btype = t
                evt.color = list(BULLET_TYPES[t]["color"])
                evt.width, evt.height = BULLET_TYPES[t]["size"]
                self.show_message(f"类型改为: {BULLET_TYPES[t]['name']}")
                return

    # ─── 文件操作 ────────────────────────────────────────
    def _save(self):
        """保存为 .json 文件"""
        os.makedirs(self.patterns_dir, exist_ok=True)
        name = self.pattern.name.replace(" ", "_").lower()
        path = os.path.join(self.patterns_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.pattern.to_dict(), f, ensure_ascii=False, indent=2)
        self.current_file = path
        self.show_message(f"已保存: {path}")

    def _load_dialog(self):
        """列出已有模式供选择"""
        os.makedirs(self.patterns_dir, exist_ok=True)
        files = [f for f in os.listdir(self.patterns_dir) if f.endswith(".json")]
        if not files:
            self.show_message("没有找到已保存的模式")
            return
        # 自动加载第一个（简化版，后续可加菜单）
        path = os.path.join(self.patterns_dir, files[0])
        self._load_file(path)

    def _load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.pattern = BulletPattern.from_dict(data)
            self.current_file = path
            self.selected_idx = -1
            self.playing = False
            self.show_message(f"已加载: {os.path.basename(path)}")
        except Exception as e:
            self.show_message(f"加载失败: {e}")

    def _export(self):
        """导出（同保存）"""
        self._save()

    # ─── 绘制 ────────────────────────────────────────────
    def _draw(self):
        self.screen.fill((30, 30, 40))

        self._draw_canvas()
        self._draw_timeline()
        self._draw_panel()
        self._draw_status_bar()
        self._draw_message()

        pygame.display.flip()

    def _draw_canvas(self):
        # 背景
        pygame.draw.rect(self.screen, (15, 15, 25),
                         (CANVAS_OFFSET_X - 2, CANVAS_OFFSET_Y - 2,
                          CANVAS_W + 4, CANVAS_H + 4), 2)
        self.screen.blit(self.canvas_surf, (CANVAS_OFFSET_X, CANVAS_OFFSET_Y))
        self.canvas_surf.fill((10, 10, 18))

        # 网格
        self.canvas_surf.blit(self.grid_surf, (0, 0))

        # 弹幕事件
        for i, evt in enumerate(self.pattern.events):
            is_selected = (i == self.selected_idx)
            # 根据播放帧高亮
            alpha = 255 if not self.playing or evt.time > self.play_frame else 100
            color = evt.color
            if is_selected:
                color = (255, 200, 0)
                alpha = 255

            # 画形状
            x, y = evt.x, evt.y
            w, h = evt.width, evt.height

            # 小尺寸用圆，大尺寸用矩形
            if max(w, h) < 30:
                pygame.draw.circle(self.canvas_surf, color, (int(x), int(y)),
                                   max(4, min(w, h) // 2))
            else:
                r = pygame.Rect(x - w // 2, y - h // 2, w, h)
                pygame.draw.rect(self.canvas_surf, color, r, 2)

            if is_selected:
                # 选择高亮环
                pygame.draw.circle(self.canvas_surf, (255, 255, 0),
                                   (int(x), int(y)), 10, 1)

        # 预览子弹
        for b in self.preview_bullets:
            if b["type"] == "laser" and b["life"] > 300 - b["warning"]:
                # 预警状态
                r = pygame.Rect(b["x"] - b["w"] // 2, b["y"] - b["h"] // 2, b["w"], b["h"])
                w_surf = pygame.Surface((b["w"], b["h"]), pygame.SRCALPHA)
                w_surf.fill((255, 0, 0, 60))
                self.canvas_surf.blit(w_surf, (b["x"] - b["w"] // 2, b["y"] - b["h"] // 2))
            elif b["type"] == "laser_network":
                pygame.draw.line(self.canvas_surf, b["color"],
                                 (b["x"], b["y"]), (b["x"] + b["w"], b["y"] + b["h"]), 3)
            else:
                pygame.draw.circle(self.canvas_surf, b["color"],
                                   (int(b["x"]), int(b["y"])), max(3, b["w"] // 2))

        # 灵魂（预览时显示）
        if self.playing:
            hx, hy = int(self.heart_pos[0]), int(self.heart_pos[1])
            # 红色心形
            pygame.draw.rect(self.canvas_surf, (255, 0, 0),
                             (hx - HEART_SIZE // 2, hy - HEART_SIZE // 2,
                              HEART_SIZE, HEART_SIZE))
            # 白色边框
            pygame.draw.rect(self.canvas_surf, (255, 255, 255),
                             (hx - HEART_SIZE // 2, hy - HEART_SIZE // 2,
                              HEART_SIZE, HEART_SIZE), 1)

        # 画布标签
        label = self.font_sm.render(f"战斗区域 {CANVAS_W}×{CANVAS_H}", True, (150, 150, 150))
        self.screen.blit(label, (CANVAS_OFFSET_X, CANVAS_OFFSET_Y - 22))

    def _draw_timeline(self):
        # 时间线背景
        tl_rect = pygame.Rect(TIMELINE_X, TIMELINE_Y, TIMELINE_W, TIMELINE_H)
        pygame.draw.rect(self.screen, (40, 40, 55), tl_rect)
        pygame.draw.rect(self.screen, (80, 80, 100), tl_rect, 1)

        # 播放头
        head_x = TIMELINE_X + int((self.play_frame / self.pattern.duration) * TIMELINE_W)
        pygame.draw.line(self.screen, (255, 50, 50),
                         (head_x, TIMELINE_Y), (head_x, TIMELINE_Y + TIMELINE_H), 2)

        # 弹幕事件标记
        for i, evt in enumerate(self.pattern.events):
            ex = TIMELINE_X + int((evt.time / self.pattern.duration) * TIMELINE_W)
            color = (255, 200, 0) if i == self.selected_idx else evt.color
            pygame.draw.circle(self.screen, color,
                               (ex, TIMELINE_Y + TIMELINE_H // 2), 5)

        # 时间线刻度
        for sec in range(0, self.pattern.duration + 60, 60):
            tx = TIMELINE_X + int((sec / self.pattern.duration) * TIMELINE_W)
            pygame.draw.line(self.screen, (100, 100, 120),
                             (tx, TIMELINE_Y + TIMELINE_H + 2),
                             (tx, TIMELINE_Y + TIMELINE_H + 10), 1)
            lbl = self.font_sm.render(f"{sec//60}s", True, (120, 120, 140))
            self.screen.blit(lbl, (tx - 10, TIMELINE_Y + TIMELINE_H + 12))

        # 帧数显示
        frame_text = self.font_md.render(
            f"帧: {self.play_frame}/{self.pattern.duration}",
            True, (200, 200, 200))
        self.screen.blit(frame_text, (TIMELINE_X + TIMELINE_W + 10, TIMELINE_Y + 5))

        # 播放按钮
        btn_text = "⏸ 暂停" if self.playing else "▶ 播放"
        btn_color = (200, 150, 50) if self.playing else (100, 200, 100)
        btn = self.font_md.render(btn_text, True, btn_color)
        self.screen.blit(btn, (TIMELINE_X + TIMELINE_W + 10, TIMELINE_Y + 25))

        # 提示
        help_lines = [
            "空格: 播放/暂停",
            "方向键: 控制灵魂",
            "1-8: 快速添加弹幕",
            "Delete: 删除选中",
            "Ctrl+S: 保存",
            "Ctrl+R: 重置",
        ]
        for i, line in enumerate(help_lines):
            h = self.font_sm.render(line, True, (100, 100, 110))
            self.screen.blit(h, (TIMELINE_X, TIMELINE_Y + TIMELINE_H + 35 + i * 18))

    def _draw_panel(self):
        # 面板背景
        panel_rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, 480)
        pygame.draw.rect(self.screen, (35, 35, 50), panel_rect)
        pygame.draw.rect(self.screen, (80, 80, 100), panel_rect, 1)

        title = self.font_lg.render("弹幕类型", True, (200, 200, 200))
        self.screen.blit(title, (PANEL_X + 10, PANEL_Y + 2))

        # 弹幕类型按钮
        types = list(BULLET_TYPES.keys())
        for i, t in enumerate(types):
            info = BULLET_TYPES[t]
            btn_y = PANEL_Y + 30 + i * 28
            is_active = (self.selected_idx >= 0 and
                         self.pattern.events[self.selected_idx].btype == t)
            bg = (80, 60, 20) if is_active else (50, 50, 65)
            pygame.draw.rect(self.screen, bg,
                             (PANEL_X + 5, btn_y, PANEL_W - 10, 26))
            pygame.draw.rect(self.screen, info["color"],
                             (PANEL_X + 5, btn_y, PANEL_W - 10, 26), 1)

            icon = self.font_md.render(info["icon"], True, info["color"])
            lbl = self.font_sm.render(f"{i+1}. {info['name']}", True, (200, 200, 200))
            self.screen.blit(icon, (PANEL_X + 10, btn_y + 3))
            self.screen.blit(lbl, (PANEL_X + 30, btn_y + 4))

        # 选中事件的属性
        if self.selected_idx >= 0:
            evt = self.pattern.events[self.selected_idx]
            py = PANEL_Y + 30 + len(types) * 28 + 15
            self._draw_property_row(py, "帧", str(evt.time))
            self._draw_property_row(py + 25, "X", str(evt.x))
            self._draw_property_row(py + 50, "Y", str(evt.y))
            self._draw_property_row(py + 75, "VX", f"{evt.vx:.1f}")
            self._draw_property_row(py + 100, "VY", f"{evt.vy:.1f}")
            self._draw_property_row(py + 125, "数量", str(evt.count))
            self._draw_property_row(py + 150, "间隔", str(evt.interval))
            self._draw_property_row(py + 175, "伤害", str(evt.damage))

    def _draw_property_row(self, y, label, value):
        lbl = self.font_sm.render(f"{label}: ", True, (150, 150, 160))
        val = self.font_sm.render(value, True, (255, 255, 255))
        self.screen.blit(lbl, (PANEL_X + 10, y))
        self.screen.blit(val, (PANEL_X + 60, y))

    def _draw_status_bar(self):
        # 底部状态栏
        y = WINDOW_H - 25
        pygame.draw.line(self.screen, (60, 60, 80), (0, y), (WINDOW_W, y))
        status = f"事件: {len(self.pattern.events)} | 时长: {self.pattern.duration}帧 ({self.pattern.duration/60:.1f}s)"
        if self.current_file:
            status += f" | 文件: {os.path.basename(self.current_file)}"
        lbl = self.font_sm.render(status, True, (120, 120, 140))
        self.screen.blit(lbl, (10, y + 3))

    def _draw_message(self):
        if self.message:
            # 半透明浮动消息
            s = pygame.Surface((WINDOW_W - 40, 40), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            self.screen.blit(s, (20, WINDOW_H - 70))
            lbl = self.font_md.render(self.message, True, (255, 255, 100))
            self.screen.blit(lbl, (30, WINDOW_H - 65))


# ─── 入口 ───────────────────────────────────────────────
if __name__ == "__main__":
    app = BulletDesigner()
    app.run()
