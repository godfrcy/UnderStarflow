import pygame
import random
import math
from engine.utils import resource_path, get_font
from engine.config import *


class RenderMixin:
    def draw(self):
        if not self.running: return
        
        # Shake
        if self.shake_intensity > 0:
            self.shake_offset = [random.randint(-5, 5), random.randint(-5, 5)]
            self.shake_intensity -= 1
        else:
            self.shake_offset = [0, 0]

        # Render to temp surface for potential inversion
        render_surface = pygame.Surface(self.screen.get_size())
        render_surface.fill((0, 0, 0))
        
        # All drawing goes to render_surface instead of self.screen
        # Replace all self.screen with render_surface in this method block
        # Or just draw normally and flip self.screen at the end? 
        # But self.screen is the display surface. Flipping it using transform is expensive but works.
        # Actually, if I draw to self.screen, I can't flip it easily in place.
        # Better to draw everything to self.screen, then capture it, flip it, and blit back?
        # Or draw to a temp surface.
        # Since this method is long, replacing all 'self.screen' is risky/tedious with SearchReplace.
        # Let's try drawing to self.screen normally, and at the end of draw(), 
        # if inverted, copy screen to surface, flip, and blit back.
        
        self.screen.fill((0, 0, 0))

        # Draw Enemy
        enemy_draw_pos = self.enemy_rect.move(self.shake_offset)
        self.screen.blit(self.enemy_img, enemy_draw_pos)

        # 二阶段过渡红叉：随机打在左/右舞者身上，进入二阶段后保留
        if getattr(self, 'phase2_cross_side', None):
            side = self.phase2_cross_side
            cx = enemy_draw_pos.left + enemy_draw_pos.width * (0.35 if side == "left" else 0.70)
            cy = enemy_draw_pos.centery
            s = 32
            pygame.draw.line(self.screen, (255, 0, 0), (cx - s, cy - s), (cx + s, cy + s), 9)
            pygame.draw.line(self.screen, (255, 0, 0), (cx - s, cy + s), (cx + s, cy - s), 9)
        
        # Draw Energy Shield (REMOVED as per request - Legacy Effect)
        # if self.is_shield_active:
        #      # Draw blue circle/ellipse around enemy
        #      shield_rect = enemy_draw_pos.inflate(20, 20)
        #      pygame.draw.ellipse(self.screen, (0, 200, 255), shield_rect, 4)
        #      pygame.draw.ellipse(self.screen, (0, 255, 255), shield_rect.inflate(-10, -10), 1)

        
        # Draw Enemy HP Bar
        enemy_hp_bar_w, enemy_hp_bar_h = 100, 10
        enemy_hp_x = enemy_draw_pos.right + 20
        enemy_hp_y = enemy_draw_pos.centery
        if enemy_hp_x + enemy_hp_bar_w > SCREEN_WIDTH:
            enemy_hp_x = enemy_draw_pos.centerx - enemy_hp_bar_w // 2
            enemy_hp_y = enemy_draw_pos.bottom + 10
        pygame.draw.rect(self.screen, (100, 0, 0), (enemy_hp_x, enemy_hp_y, enemy_hp_bar_w, enemy_hp_bar_h))
        current_enemy_hp_w = int((self.enemy_hp / self.enemy_max_hp) * enemy_hp_bar_w)
        if current_enemy_hp_w > 0:
            pygame.draw.rect(self.screen, (0, 255, 0), (enemy_hp_x, enemy_hp_y, current_enemy_hp_w, enemy_hp_bar_h))
            
        # Draw Battle Box
        box_draw_rect = self.battle_box.move(self.shake_offset)
        box_color = (0, 255, 255) if "reroute" in self.active_skills else (255, 255, 255)
        if not getattr(self, 'is_dual_shield', False) and not getattr(self, 'is_failure_gravity_hall', False):
            pygame.draw.rect(self.screen, box_color, box_draw_rect, 4)
        
        # Draw Magnets
        for magnet in self.magnets:
             m_rect = magnet['rect'].move(self.shake_offset)
             pygame.draw.ellipse(self.screen, (100, 100, 100), m_rect)
             pygame.draw.ellipse(self.screen, (200, 200, 200), m_rect, 2)
        
        # Draw UI
        self.draw_ui(box_draw_rect)
        
        # Draw Phase Content
        if self.current_phase == self.PHASE_MENU:
            text_surf = self.dialog_font.render(self.dialog_text, True, (255, 255, 255))
            self.screen.blit(text_surf, (box_draw_rect.x + 20, box_draw_rect.y + 20))
            
        elif self.current_phase == self.PHASE_ACT_SELECT:
            self.draw_list_selection(box_draw_rect, self.get_act_options(), self.act_selection_idx)
            
        elif self.current_phase == self.PHASE_ITEM_SELECT:
            # Consolidate inventory to ensure display matches logic
            display_items, _ = self._build_consumable_list()
            self.draw_list_selection(box_draw_rect, display_items, self.item_selection_idx)
            
        elif self.current_phase == self.PHASE_MERCY_SELECT:
            self.draw_list_selection(box_draw_rect, ["取消", "宽恕"], self.mercy_selection_idx)
            
        elif self.current_phase == self.PHASE_FLEE_SELECT:
            self.draw_list_selection(box_draw_rect, ["取消", "逃跑"], self.flee_selection_idx)
            
        elif self.current_phase == self.PHASE_QTE:
            pygame.draw.rect(self.screen, (50, 50, 50), self.qte_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.qte_target_zone)
            pygame.draw.rect(self.screen, (255, 255, 0), self.qte_perfect_zone)
            pygame.draw.rect(self.screen, (255, 255, 255), self.qte_rect, 2)
            needle_draw_x = int(self.qte_needle_x)
            pygame.draw.line(self.screen, (255, 0, 0), (needle_draw_x, self.qte_rect.top), (needle_draw_x, self.qte_rect.bottom), 4)
            
        elif self.current_phase == self.PHASE_PLAYER_ANIM:
            if not self.is_attack_anim:
                text_surf = self.dialog_font.render(self.action_text, True, (255, 255, 255))
                self.screen.blit(text_surf, (box_draw_rect.x + 20, box_draw_rect.y + 20))
                
        elif self.current_phase == self.PHASE_ENEMY_TURN:
            # UFO 牵引：重力列纯紫色高亮（无害指示）+ 中间竖线向上滚动的紫色箭头
            if "ufo_tractor" in self.active_skills and hasattr(self, 'ufo_gravity_col'):
                col_w = self.battle_box.width // 3
                g_rect = pygame.Rect(
                    self.battle_box.left + self.ufo_gravity_col * col_w, self.battle_box.top,
                    col_w, self.battle_box.height).move(self.shake_offset)
                # 整列纯紫色半透明填充（非条纹）
                overlay = pygame.Surface((col_w, self.battle_box.height), pygame.SRCALPHA)
                overlay.fill((150, 70, 220, 80))
                self.screen.blit(overlay, (g_rect.x, g_rect.y))
                # 只有中间竖线刷向上滚动的紫色箭头（上下留边，提前消失不穿模边框）
                t = pygame.time.get_ticks()
                ax = g_rect.centerx
                margin = 10
                cycle = self.battle_box.height - 2 * margin
                for i in range(4):
                    off_y = ((i * 60) - (t // 6)) % cycle + margin
                    ay = g_rect.y + off_y
                    pts = [(ax, ay - 7), (ax - 7, ay + 5), (ax + 7, ay + 5)]
                    pygame.draw.polygon(self.screen, (205, 130, 255), pts)

            # 废料传送带：只画三条水平虚线轨道，红心挂在上面
            if "conveyor_belt" in self.active_skills:
                lane_h = self.battle_box.height // 3
                for i in range(3):
                    ry = self.battle_box.top + lane_h * (i + 0.5) + self.shake_offset[1]
                    for x in range(self.battle_box.left + self.shake_offset[0], self.battle_box.right + self.shake_offset[0], 16):
                        pygame.draw.line(self.screen, (170, 170, 180), (x, ry), (x + 8, ry), 2)

            # 单摆（重力摆锤）：圆形虚线轨道（可达下弧）+ 摆杆 + 枢轴
            if "pendulum" in self.active_skills:
                pivot = (self.battle_box.centerx + self.shake_offset[0], self.battle_box.top + self.shake_offset[1])
                r = getattr(self, 'pend_len', 150)
                max_a = getattr(self, 'pend_max_angle', 1.22)
                ang = getattr(self, 'pend_angle', 0.0)
                n = 24
                for i in range(n):
                    a1 = -max_a + (2 * max_a) * i / n
                    a2 = -max_a + (2 * max_a) * (i + 1) / n
                    if i % 2 == 0:
                        x1 = pivot[0] + r * math.sin(a1)
                        y1 = pivot[1] + r * math.cos(a1)
                        x2 = pivot[0] + r * math.sin(a2)
                        y2 = pivot[1] + r * math.cos(a2)
                        pygame.draw.line(self.screen, (170, 170, 180), (x1, y1), (x2, y2), 2)
                bx = pivot[0] + r * math.sin(ang)
                by = pivot[1] + r * math.cos(ang)
                pygame.draw.line(self.screen, (140, 140, 150), (pivot[0], pivot[1]), (bx, by), 2)
                pygame.draw.circle(self.screen, (170, 170, 180), (int(pivot[0]), int(pivot[1])), 4)

            # 弹簧振子：横置窄条，红心左右各一条水平像素弹簧（左/右两端），随水平振动伸缩
            if "spring_oscillator" in self.active_skills:
                strip = self.battle_box.move(self.shake_offset)
                hcx = self.heart_rect.centerx + self.shake_offset[0]
                cy = strip.centery
                # 平衡线（虚线，指示简谐振动中心——竖直中线）
                for y in range(strip.top + 4, strip.bottom - 4, 8):
                    pygame.draw.line(self.screen, (90, 90, 100),
                                     (strip.centerx, y), (strip.centerx, y + 4), 1)
                self._draw_spring_h(self.screen, strip.left + 8, hcx, cy)
                self._draw_spring_h(self.screen, hcx, strip.right - 8, cy)

            # 双生舞怜·苏联国徽单摆：金色地球 + 下半圆下摆（=摆锤轨道）+ 摆杆
            if "soviet_emblem" in self.active_skills:
                pivot = (self.battle_box.centerx + self.shake_offset[0], self.battle_box.top + 90 + self.shake_offset[1])
                r = getattr(self, 'pend_len', 120)
                ang = getattr(self, 'pend_angle', 0.0)
                gold = (255, 200, 60)
                earth_r = 45
                # 二阶段：中央重力域——覆盖整条单摆的圆形力场（脉冲时增亮扩张）
                if self.phase == 2:
                    grav_on = getattr(self, 'grav_pulse_on', False)
                    gr = r
                    field = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
                    alpha = 40 if grav_on else 20
                    pygame.draw.circle(field, (200, 70, 130, alpha), (gr, gr), gr)
                    self.screen.blit(field, (int(pivot[0] - gr), int(pivot[1] - gr)))
                    if grav_on:
                        pr = gr + (8 if (getattr(self, 'grav_pulse_timer', 0) // 5) % 2 == 0 else 0)
                        pygame.draw.circle(self.screen, (255, 120, 150), (int(pivot[0]), int(pivot[1])), pr, 3)
                        pygame.draw.circle(self.screen, (255, 190, 205), (int(pivot[0]), int(pivot[1])), gr, 1)
                    else:
                        pygame.draw.circle(self.screen, (150, 70, 100), (int(pivot[0]), int(pivot[1])), gr, 2)
                # 地球（圆）+ 经纬线
                pygame.draw.circle(self.screen, gold, (int(pivot[0]), int(pivot[1])), earth_r, 3)
                pygame.draw.line(self.screen, gold, (pivot[0] - earth_r, pivot[1]), (pivot[0] + earth_r, pivot[1]), 1)
                pygame.draw.line(self.screen, gold, (pivot[0], pivot[1] - earth_r), (pivot[0], pivot[1] + earth_r), 1)
                # 下半圆下摆（从 -90° 到 +90° 的下弧）
                n = 32
                for i in range(n):
                    a1 = -math.pi / 2 + math.pi * i / n
                    a2 = -math.pi / 2 + math.pi * (i + 1) / n
                    x1 = pivot[0] + r * math.sin(a1)
                    y1 = pivot[1] + r * math.cos(a1)
                    x2 = pivot[0] + r * math.sin(a2)
                    y2 = pivot[1] + r * math.cos(a2)
                    pygame.draw.line(self.screen, gold, (x1, y1), (x2, y2), 3)
                # 摆杆（枢轴 → 摆锤）
                bx = pivot[0] + r * math.sin(ang)
                by = pivot[1] + r * math.cos(ang)
                pygame.draw.line(self.screen, gold, (pivot[0], pivot[1]), (bx, by), 2)
                pygame.draw.circle(self.screen, gold, (int(pivot[0]), int(pivot[1])), 4)

            # 双生舞怜·田字格追逐：完整田字格（外框 + 十字），全虚线
            if "dancer_chase" in self.active_skills:
                cols = self.dancer_grid_cols
                rows = self.dancer_grid_rows
                L = int(cols[0] + self.shake_offset[0])
                R = int(cols[2] + self.shake_offset[0])
                T = int(rows[0] + self.shake_offset[1])
                B = int(rows[2] + self.shake_offset[1])
                Mx = int(cols[1] + self.shake_offset[0])
                My = int(rows[1] + self.shake_offset[1])
                # 外框四条边（虚线）
                for x in range(L, R, 16):
                    pygame.draw.line(self.screen, (170, 170, 180), (x, T), (min(x + 8, R), T), 2)
                    pygame.draw.line(self.screen, (170, 170, 180), (x, B), (min(x + 8, R), B), 2)
                for y in range(T, B, 16):
                    pygame.draw.line(self.screen, (170, 170, 180), (L, y), (L, min(y + 8, B)), 2)
                    pygame.draw.line(self.screen, (170, 170, 180), (R, y), (R, min(y + 8, B)), 2)
                # 中间十字（虚线）
                for y in range(T, B, 16):
                    pygame.draw.line(self.screen, (170, 170, 180), (Mx, y), (Mx, min(y + 8, B)), 2)
                for x in range(L, R, 16):
                    pygame.draw.line(self.screen, (170, 170, 180), (x, My), (min(x + 8, R), My), 2)
                # 二阶段：追击者走过的路径燃烧（红实线覆盖虚线）
                burned = getattr(self, 'dancer_burned_edges', None)
                if burned:
                    for (r1, c1), (r2, c2) in burned:
                        bx1 = int(cols[c1] + self.shake_offset[0])
                        by1 = int(rows[r1] + self.shake_offset[1])
                        bx2 = int(cols[c2] + self.shake_offset[0])
                        by2 = int(rows[r2] + self.shake_offset[1])
                        pygame.draw.line(self.screen, (150, 0, 0), (bx1, by1), (bx2, by2), 7)
                        pygame.draw.line(self.screen, (255, 40, 40), (bx1, by1), (bx2, by2), 3)

            for b in self.bullets:
                b.draw(self.screen, offset=self.shake_offset)

            # Draw Dusts (Skill A)
            if "escape_dust" in self.active_skills:
                for dust in self.dusts:
                    dust.draw(self.screen)

            # Draw Debris Particles
            for p in self.debris_particles:
                p.draw(self.screen)
            
            # Draw Shield and Arrows
            if hasattr(self, 'is_shield_mode') and self.is_shield_mode:
                # Shield
                shield_dist = 25
                shield_len = 32
                shield_thick = 5
                
                cx, cy = self.heart_rect.centerx + self.shake_offset[0], self.heart_rect.centery + self.shake_offset[1]
                shield_rect = pygame.Rect(0, 0, 0, 0)
                
                if self.shield_dir == "UP":
                    shield_rect = pygame.Rect(cx - shield_len//2, cy - shield_dist - shield_thick, shield_len, shield_thick)
                elif self.shield_dir == "DOWN":
                    shield_rect = pygame.Rect(cx - shield_len//2, cy + shield_dist, shield_len, shield_thick)
                elif self.shield_dir == "LEFT":
                    shield_rect = pygame.Rect(cx - shield_dist - shield_thick, cy - shield_len//2, shield_thick, shield_len)
                elif self.shield_dir == "RIGHT":
                    shield_rect = pygame.Rect(cx + shield_dist, cy - shield_len//2, shield_thick, shield_len)
                
                # Shield Color: Deep Blue normally, Light Blue if recovering (broken)
                shield_color = (0, 100, 255)
                if hasattr(self, 'shield_broken_timer') and self.shield_broken_timer > 0:
                    shield_color = (135, 206, 250) # Light Sky Blue
                
                pygame.draw.rect(self.screen, shield_color, shield_rect)
                self.current_shield_rect = shield_rect
                
                # Arrows
                for arrow in self.shield_arrows:
                    p = list(arrow['pos'])
                    p[0] += self.shake_offset[0]
                    p[1] += self.shake_offset[1]
                    
                    size = 10
                    points = []
                    arrow_type = arrow.get('type', 'white')
                    color = (255, 255, 255)
                    if arrow_type == 'blue':
                        color = (0, 191, 255) # Deep Sky Blue
                    
                    if arrow['dir'] == "UP": 
                        points = [[p[0], p[1]+size], [p[0]-size/2, p[1]-size], [p[0]+size/2, p[1]-size]]
                    elif arrow['dir'] == "DOWN": 
                        points = [[p[0], p[1]-size], [p[0]-size/2, p[1]+size], [p[0]+size/2, p[1]+size]]
                    elif arrow['dir'] == "LEFT": 
                        points = [[p[0]+size, p[1]], [p[0]-size, p[1]-size/2], [p[0]-size, p[1]+size/2]]
                    elif arrow['dir'] == "RIGHT": 
                        points = [[p[0]-size, p[1]], [p[0]+size, p[1]-size/2], [p[0]+size, p[1]+size/2]]
                    
                    # Color based on type
                    color = (255, 255, 255)
                    if arrow.get('type') == 'blue':
                        color = (0, 100, 255) # Same as energy shield color
                    
                    pygame.draw.polygon(self.screen, color, points)

            # 失败之作·镜像双心：左右两个对称区域（实线框）+ 中间挡板 + 蓝白箭头 + 双护盾（右心在下方红心 blit 后补画）
            if getattr(self, 'is_dual_shield', False):
                lr = self.dual_left_rect.move(self.shake_offset)
                rr = self.dual_right_rect.move(self.shake_offset)
                pygame.draw.rect(self.screen, (255, 255, 255), lr, 2)
                pygame.draw.rect(self.screen, (255, 255, 255), rr, 2)
                # 中间挡板（两个区域之间）
                mid_x = self.battle_box.centerx + self.shake_offset[0]
                pygame.draw.rect(self.screen, (120, 120, 130), (mid_x - 3, lr.top, 6, lr.height))
                # 蓝白箭头（复用能量护盾的箭头绘制：dir 定朝向，type 定颜色）
                for b in self.dual_bullets:
                    p = [int(b['pos'][0]) + self.shake_offset[0], int(b['pos'][1]) + self.shake_offset[1]]
                    size = 10
                    if b['dir'] == "UP":
                        points = [[p[0], p[1] + size], [p[0] - size / 2, p[1] - size], [p[0] + size / 2, p[1] - size]]
                    elif b['dir'] == "DOWN":
                        points = [[p[0], p[1] - size], [p[0] - size / 2, p[1] + size], [p[0] + size / 2, p[1] + size]]
                    elif b['dir'] == "LEFT":
                        points = [[p[0] + size, p[1]], [p[0] - size, p[1] - size / 2], [p[0] - size, p[1] + size / 2]]
                    elif b['dir'] == "RIGHT":
                        points = [[p[0] - size, p[1]], [p[0] + size, p[1] - size / 2], [p[0] + size, p[1] + size / 2]]
                    color = (0, 100, 255) if b.get('type', 'white') == 'blue' else (255, 255, 255)
                    pygame.draw.polygon(self.screen, color, points)
                # 双护盾（破损时变浅天蓝，提示该侧已失效——与能量护盾一致）
                lc = (int(self.dual_left_center[0] + self.shake_offset[0]), int(self.dual_left_center[1] + self.shake_offset[1]))
                rc = (int(self.dual_right_center[0] + self.shake_offset[0]), int(self.dual_right_center[1] + self.shake_offset[1]))
                lshield_col = (135, 206, 250) if getattr(self, 'left_shield_broken_timer', 0) > 0 else (0, 100, 255)
                rshield_col = (135, 206, 250) if getattr(self, 'right_shield_broken_timer', 0) > 0 else (0, 100, 255)
                pygame.draw.rect(self.screen, lshield_col, self._dual_shield_rect(lc, self.left_shield_dir))
                pygame.draw.rect(self.screen, rshield_col, self._dual_shield_rect(rc, self.right_shield_dir))

            # 失败之作·重力走廊：横向长条（边框）+ 上下白色柱子（中间留缝隙）
            if getattr(self, 'is_failure_gravity_hall', False):
                hr = self.hall_rect.move(self.shake_offset)
                pygame.draw.rect(self.screen, (255, 255, 255), hr, 2)
                for p in self.hall_pillars:
                    px = int(p['x']) + self.shake_offset[0]
                    top_h = p['gap_top'] - self.hall_rect.top
                    bot_h = self.hall_rect.bottom - (p['gap_top'] + p['gap_h'])
                    # 上柱（从顶向下伸）
                    pygame.draw.rect(self.screen, (255, 255, 255), (px, hr.top, 20, top_h))
                    # 下柱（从底向上伸）
                    pygame.draw.rect(self.screen, (255, 255, 255), (px, hr.top + top_h + p['gap_h'], 20, bot_h))

            # 失败之作·5×5 激光列：绿色安全列 + 感叹号（频闪预警）+ 蓝色激光（覆盖非安全侧 4 列）
            if getattr(self, 'is_failure_laser_grid', False):
                gr = self.laser_grid_rect.move(self.shake_offset)
                cw = int(self.laser_cell_w)
                pygame.draw.rect(self.screen, (255, 255, 255), gr, 2)
                if getattr(self, 'laser_gravity_phase', False):
                    # 重力幽灵斩阶段：只保留外框，幽灵斩由 GroundSlash 自身渲染
                    pass
                else:
                    # 绿色安全列（左下感叹号→最右列安全；右下感叹号→最左列安全）
                    safe_x = gr.right - cw if self.laser_exclaim_side == 'left' else gr.left
                    safe_surf = pygame.Surface((cw, gr.height), pygame.SRCALPHA)
                    safe_surf.fill((120, 255, 120, 40))
                    self.screen.blit(safe_surf, (int(safe_x), gr.top))
                    # 感叹号（左下/右下角），warn 状态频闪 2 次
                    if self.laser_state == 'warn':
                        if (self.laser_timer // 18) % 2 == 0:
                            ecx = gr.left + cw / 2.0 if self.laser_exclaim_side == 'left' else gr.right - cw / 2.0
                            ecy = gr.bottom - 30
                            bang = get_font(40).render("!", True, (255, 220, 60))
                            self.screen.blit(bang, bang.get_rect(center=(int(ecx), int(ecy))))
                    # 蓝色激光条（active 状态）：苗条竖条从感叹号侧快速平移（竖条 + 白热核心）
                    elif self.laser_state == 'active':
                        bar_w = getattr(self, 'laser_bar_w', 30)
                        bar_x = int(gr.left + (getattr(self, 'laser_bar_x', 0) - self.laser_grid_rect.left))
                        laser_surf = pygame.Surface((bar_w, gr.height), pygame.SRCALPHA)
                        laser_surf.fill((0, 120, 255, 170))
                        self.screen.blit(laser_surf, (bar_x, gr.top))
                        core_w = max(4, int(bar_w * 0.3))
                        core = pygame.Surface((core_w, gr.height), pygame.SRCALPHA)
                        core.fill((180, 220, 255, 220))
                        self.screen.blit(core, (int(bar_x + bar_w / 2 - core_w / 2), gr.top))

            if self.damage_flash_timer > 0:
                self.damage_flash_timer -= 1
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                flash_surf.fill((255, 0, 0))
                flash_surf.set_alpha(100)
                self.screen.blit(flash_surf, (0, 0))
            # 重力走廊全程：心保持旋转 90°（下方朝右），不恢复自然朝向
            if getattr(self, 'is_failure_gravity_hall', False):
                heart_img = getattr(self, 'hall_heart_img', None) or self.heart_img
            else:
                heart_img = self.heart_img
            self.screen.blit(heart_img, self.heart_rect.move(self.shake_offset))

            # 失败之作·镜像双心：右心（左心已由上方主红心 blit 画出）
            if getattr(self, 'is_dual_shield', False):
                rheart = self.heart_img.get_rect(center=(int(self.dual_right_center[0] + self.shake_offset[0]), int(self.dual_right_center[1] + self.shake_offset[1])))
                self.screen.blit(self.heart_img, rheart)

            # --- Debug Draw Circular Hitbox ---
            # Toggle this via a flag if needed, currently always drawing for verification as requested
            heart_draw_pos = self.heart_rect.move(self.shake_offset)
            pygame.draw.circle(self.screen, (0, 255, 0), heart_draw_pos.center, getattr(self.player, 'hitbox_radius', 4), 1)
            # ----------------------------------
            
        # Draw Damage Popups
        for popup in self.damage_popups:
            text_str, color, pos = popup['val'], popup['color'], popup['pos']
            stroke_color = (0, 0, 0)
            for dx in [-2, 0, 2]:
                for dy in [-2, 0, 2]:
                    self.screen.blit(self.damage_font.render(text_str, True, stroke_color), (pos[0] + dx, pos[1] + dy))
            self.screen.blit(self.damage_font.render(text_str, True, color), pos)

        # DEBUG OVERLAY
        # if "变量" in self.enemy_data.get("name", ""):
        #     debug_str = f"Phase: {self.current_phase} (0=MENU, 2=ENEMY)"
        #     debug_surf = self.font.render(debug_str, True, (0, 255, 0))
        #     self.screen.blit(debug_surf, (10, 10))
            
        # Handle Screen Inversion (Skill B)
        # Capture the screen, flip it, and blit it back
        if hasattr(self, 'is_screen_inverted') and self.is_screen_inverted:
             # This is expensive, but effective for "completely flip screen"
             # Copy current display
             screen_copy = self.screen.copy()
             # Flip (180 degrees = flip x and y)
             flipped = pygame.transform.flip(screen_copy, True, True)
             self.screen.blit(flipped, (0, 0))

        # 「明日指针」金瞳故障闪屏（EMP 瓦解失败之作后触发，一次性 ~1.5s）
        if self.anthe_glitch_timer > 0:
            self.anthe_glitch_timer -= 1
            t = self.anthe_glitch_timer
            if t > 75:
                a = int(255 * (90 - t) / 15)   # 淡入
            elif t < 30:
                a = int(255 * t / 30)          # 淡出
            else:
                a = 255
            a = max(0, min(255, a))

            # 横向噪点条纹
            glitch_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for _ in range(18):
                h = random.randint(2, 12)
                y = random.randint(0, SCREEN_HEIGHT - h)
                shade = random.randint(0, 40)
                pygame.draw.rect(glitch_surf, (shade, shade, shade, random.randint(60, 200)), (0, y, SCREEN_WIDTH, h))
            self.screen.blit(glitch_surf, (0, 0))

            # 浮动文字「明日指针」
            word = get_font(64).render("明日指针", True, (255, 200, 80))
            word.set_alpha(a)
            wobble = int(8 * math.sin(t / 6.0))
            wrect = word.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + wobble))
            self.screen.blit(word, wrect)

    def _draw_spring_h(self, screen, x_left, x_right, y, color=(120, 200, 255), amp=7):
        """在固定 y 坐标处画一段水平像素弹簧（锯齿折线），从 x_left 连到 x_right。"""
        if x_right - x_left < 2:
            return
        segs = max(2, int((x_right - x_left) // 10))
        pts = [(x_left, y)]
        for i in range(1, segs):
            xx = x_left + (x_right - x_left) * i / segs
            yy = y + (amp if i % 2 == 1 else -amp)
            pts.append((xx, yy))
        pts.append((x_right, y))
        pygame.draw.lines(screen, color, False, pts, 2)

    def draw_ui(self, box_draw_rect):
        status_y = 620
        btn_y = 650
        
        if self.current_phase == self.PHASE_VICTORY:
             # Draw black box at bottom
             dialog_rect = pygame.Rect(50, 600, SCREEN_WIDTH - 100, 150)
             pygame.draw.rect(self.screen, (0, 0, 0), dialog_rect)
             pygame.draw.rect(self.screen, (255, 255, 255), dialog_rect, 2)
             
             # Draw messages
             start_y = 620
             for i, msg in enumerate(self.victory_messages):
                 text_surf = self.dialog_font.render(msg, True, (255, 255, 255))
                 self.screen.blit(text_surf, (80, start_y + i * 30))
             
             # Draw "Press SPACE to continue"
             cont_surf = self.font.render("[SPACE] Continue", True, (150, 150, 150))
             self.screen.blit(cont_surf, (dialog_rect.right - 150, dialog_rect.bottom - 30))
             return
             
        name_surf = self.font.render(f"ANTHE   LV 1", True, (255, 255, 255))
        self.screen.blit(name_surf, (box_draw_rect.left, status_y))
        
        hp_bar_width, hp_bar_height = 100, 20
        hp_x = box_draw_rect.left + 150
        pygame.draw.rect(self.screen, (255, 0, 0), (hp_x, status_y, hp_bar_width, hp_bar_height))
        current_hp_width = int((self.player.hp / self.player.max_hp) * hp_bar_width)
        if current_hp_width > 0:
            pygame.draw.rect(self.screen, (255, 255, 0), (hp_x, status_y, current_hp_width, hp_bar_height))
        hp_text = self.font.render(f"HP {self.player.hp} / {self.player.max_hp}", True, (255, 255, 255))
        self.screen.blit(hp_text, (hp_x + hp_bar_width + 20, status_y))
        
        buttons = ["FIGHT", "ACT", "ITEM", "MERCY"]
        btn_width = 150
        start_x = (SCREEN_WIDTH - (btn_width * 4 + 30)) // 2
        for i, btn_text in enumerate(buttons):
            btn_rect = pygame.Rect(start_x + i * (btn_width + 10), btn_y, btn_width, 40)
            color = (255, 255, 0) if self.current_phase == self.PHASE_MENU and i == self.selected_btn_idx else (255, 165, 0)
            width = 4 if self.current_phase == self.PHASE_MENU and i == self.selected_btn_idx else 2
            pygame.draw.rect(self.screen, color, btn_rect, width)
            text_surf = self.font.render(btn_text, True, color)
            text_rect = text_surf.get_rect(center=btn_rect.center)
            self.screen.blit(text_surf, text_rect)

    def draw_list_selection(self, box_rect, items, selected_idx):
        start_x = box_rect.x + 40
        start_y = box_rect.y + 20
        for i, item in enumerate(items):
            col = i % 2
            row = i // 2
            x = start_x + col * 200
            y = start_y + row * 30
            prefix = "* " if i == selected_idx else "  "
            text_surf = self.dialog_font.render(prefix + item, True, (255, 255, 255))
            self.screen.blit(text_surf, (x, y))
            if i == selected_idx:
                pygame.draw.rect(self.screen, (255, 0, 0), (x - 20, y + 5, 10, 10))
