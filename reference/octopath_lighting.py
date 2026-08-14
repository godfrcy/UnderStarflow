"""
备用代码 —— 歧路旅人(HD-2D)风格全屏光影滤镜（未接入游戏）。

记录于 2026-08-14。当时按用户要求试做了一版，用户看完决定「取消这种想法」，
但要求把滤镜效果「记下来」，以后用得上时复用。此文件不参与游戏运行，仅存档。

复用方法：
  1. 把本文件复制为 ui/lighting.py（或在 ui/lighting.py 里 import 本类）。
  2. 在 main.py 的 Game.__init__ 里：
         self.octopath_lighting = OctopathLighting()
         self.octopath_lighting_enabled = True
  3. 在大地图渲染循环末尾（Particles 之后、UI Overlay 之前）：
         if self.octopath_lighting_enabled:
             player_screen = self.camera.apply(self.player).center
             bonfire_screen = [self.camera.apply(s).center for s in self.bonfire_group]
             self.octopath_lighting.draw(self.screen, player_screen, bonfire_screen)
  4. 可选：在 KEYDOWN 里绑 L 键实时开关对比。

四层组成：暖色滤镜 / 光池辉光(篝火+玩家 additive bloom) / 径向暗角 / 漂浮尘粒。
"""

import pygame
import math
import random
from engine.config import SCREEN_WIDTH, SCREEN_HEIGHT


class OctopathLighting:
    """歧路旅人(HD-2D)风格的全屏光影后处理。

    由四层组成（全部预生成，每帧只做几次 blit，开销极小）：
      1. 暖色滤镜 —— 全屏金黄偏暖的色调，营造 HD-2D 的「黄昏/暖阳」质感。
      2. 光池辉光 —— 篝火、玩家等光源的软 Bloom，用 additive 叠加，光里更暖更亮。
      3. 暗角 —— 径向渐变，边缘压暗、四角偏冷，把视线收拢到画面中心。
      4. 漂浮尘粒 —— 在光里缓缓漂浮的暖色微尘，让空气「活」起来。
    """

    def __init__(self):
        self.W = SCREEN_WIDTH
        self.H = SCREEN_HEIGHT

        # 1) 暖色滤镜（全屏，很轻的一层）
        self.warm_grade = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self.warm_grade.fill((255, 176, 88, 18))

        # 2) 光池辉光（篝火大光、玩家小光，预生成）
        self.glow_big = self._make_glow(520, (255, 165, 60), 120)
        self.glow_small = self._make_glow(260, (255, 200, 120), 80)

        # 3) 暗角（径向，边缘压暗 + 冷色）
        self.vignette = self._make_vignette()

        # 4) 漂浮尘粒
        self.mote_dot = pygame.Surface((3, 3))
        self.mote_dot.fill((255, 210, 150))
        self.motes = []
        for _ in range(55):
            self.motes.append({
                "x": random.uniform(0, self.W),
                "y": random.uniform(0, self.H),
                "vx": random.uniform(-0.15, 0.15),
                "vy": random.uniform(-0.12, 0.06),
                "a": random.randint(18, 70),
                "tw": random.uniform(0, math.pi * 2),
            })

    def _make_glow(self, size_px, color, center_alpha):
        """生成一张中心亮、边缘透明的径向光斑（256 基准，smoothscale 放大更平滑）。"""
        base = 128
        surf = pygame.Surface((base, base), pygame.SRCALPHA)
        c = base / 2.0
        for y in range(base):
            for x in range(base):
                dx = x - c + 0.5
                dy = y - c + 0.5
                d = math.hypot(dx, dy) / (base / 2.0)
                if d <= 1.0:
                    a = int(center_alpha * (1.0 - d) ** 2)
                    surf.set_at((x, y), (color[0], color[1], color[2], a))
        if size_px != base:
            surf = pygame.transform.smoothscale(surf, (size_px, size_px))
        return surf

    def _make_vignette(self):
        """径向暗角：中心透明、四角最暗，暗色偏冷以对比暖光。"""
        base = 256
        surf = pygame.Surface((base, base), pygame.SRCALPHA)
        c = base / 2.0
        max_r = base / 2.0 * math.sqrt(2.0)
        for y in range(base):
            for x in range(base):
                dx = x - c + 0.5
                dy = y - c + 0.5
                d = min(1.0, math.hypot(dx, dy) / max_r)
                a = int(150 * (d ** 2.2))
                surf.set_at((x, y), (6, 8, 16, a))
        return pygame.transform.smoothscale(surf, (self.W, self.H))

    def draw(self, screen, player_pos, bonfire_positions):
        # 1) 暖色滤镜
        screen.blit(self.warm_grade, (0, 0))

        # 2) 光池辉光（先打光，再压暗角，边缘的光自然衰减）
        for (x, y) in bonfire_positions:
            screen.blit(
                self.glow_big,
                (int(x - self.glow_big.get_width() / 2), int(y - self.glow_big.get_height() / 2)),
                special_flags=pygame.BLEND_ADD,
            )
        if player_pos is not None:
            x, y = player_pos
            screen.blit(
                self.glow_small,
                (int(x - self.glow_small.get_width() / 2), int(y - self.glow_small.get_height() / 2)),
                special_flags=pygame.BLEND_ADD,
            )

        # 3) 暗角
        screen.blit(self.vignette, (0, 0))

        # 4) 漂浮尘粒（缓缓漂移 + 闪烁）
        for m in self.motes:
            m["x"] += m["vx"]
            m["y"] += m["vy"]
            m["tw"] += 0.04
            if m["x"] < 0:
                m["x"] = self.W
            elif m["x"] > self.W:
                m["x"] = 0
            if m["y"] < 0:
                m["y"] = self.H
            elif m["y"] > self.H:
                m["y"] = 0

            a = int(m["a"] * (0.55 + 0.45 * math.sin(m["tw"])))
            if a <= 0:
                continue
            self.mote_dot.set_alpha(a)
            screen.blit(self.mote_dot, (int(m["x"]), int(m["y"])))
