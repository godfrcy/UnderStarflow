import pygame
import random
import math
from engine.utils import resource_path, get_font
from engine.config import *


class MenuMixin:
    def mercy_available(self):
        """宽恕是否可用：二周目（击败过最终boss）或本周目已解锁彩蛋。"""
        if self.game_state is None:
            return False
        return bool(getattr(self.game_state, "final_boss_defeated", False)) or \
               bool(getattr(self.game_state, "mercy_unlocked", False))

    def confirm_menu_selection(self):
        if self.selected_btn_idx == 0: # FIGHT
            self.silent_streak = 0
            self.start_qte()
        elif self.selected_btn_idx == 1: # ACT
            self.current_phase = self.PHASE_ACT_SELECT
            self.act_selection_idx = 0
        elif self.selected_btn_idx == 2: # ITEM
            self.silent_streak = 0
            self.current_phase = self.PHASE_ITEM_SELECT
            self.item_selection_idx = 0
        elif self.selected_btn_idx == 3: # MERCY
            if self.mercy_available():
                self.current_phase = self.PHASE_MERCY_SELECT
                self.mercy_selection_idx = 0
            else:
                # 一周目未解锁：宽恕不可用
                self.action_text = "* 宽恕……现在还不是时候。"
                self.current_phase = self.PHASE_PLAYER_ANIM
                self.next_phase_after_anim = self.PHASE_MENU
                self.action_timer = 60

    def start_qte(self):
        self.current_phase = self.PHASE_QTE
        start_side = random.choice(["left", "right"])
        qte_speed_val = 8
        
        if start_side == "left":
            self.qte_needle_x = self.qte_rect.left
            self.qte_needle_speed = qte_speed_val
        else:
            self.qte_needle_x = self.qte_rect.right
            self.qte_needle_speed = -qte_speed_val
            
        # Optimization: Increase area by 10% (80 -> 88)
        zone_width = 88
        
        # Limit to middle 70% (15% margin on each side)
        # This prevents the zone from being too close to the start/end points
        margin = int(self.qte_rect.width * 0.15)
        
        min_x = self.qte_rect.left + margin
        max_x = self.qte_rect.right - margin - zone_width
        
        # Safety check
        if max_x < min_x:
            max_x = min_x
            
        zone_x = random.randint(min_x, max_x)
        self.qte_target_zone = pygame.Rect(zone_x, self.qte_rect.y, zone_width, self.qte_rect.height)
        
        perfect_width = 24
        perfect_x = zone_x + (zone_width - perfect_width) // 2
        self.qte_perfect_zone = pygame.Rect(perfect_x, self.qte_rect.y, perfect_width, self.qte_rect.height)

    def resolve_qte(self):
        hit_x = self.qte_needle_x
        needle_rect = pygame.Rect(int(hit_x), self.qte_rect.y, 4, self.qte_rect.height)
        
        if needle_rect.colliderect(self.qte_perfect_zone):
            self.damage_multiplier = 1.5
            if self.calibration_sfx: self.calibration_sfx.play()
        elif needle_rect.colliderect(self.qte_target_zone):
            self.damage_multiplier = 1.0
            if self.calibration_sfx: self.calibration_sfx.play()
        else:
            self.damage_multiplier = 0.0
            
        base_damage = 10
        if self.player and hasattr(self.player, "attack"):
            base_damage = self.player.attack
            
        final_damage = int(base_damage * self.damage_multiplier)
        
        if final_damage > 0:
            self.enemy_hp -= final_damage
            self._spawn_damage_popup(final_damage, (255, 0, 0), [self.enemy_rect.centerx, self.enemy_rect.top - 30])
        else:
            self._spawn_damage_popup("MISS", (150, 150, 150), [self.enemy_rect.centerx, self.enemy_rect.top - 30])
            
        if self.enemy_hp < 0: self.enemy_hp = 0
        
        self.is_attack_anim = True
        self.current_phase = self.PHASE_PLAYER_ANIM
        self.next_phase_after_anim = self.PHASE_ENEMY_TURN
        self.action_timer = 60

    def get_act_options(self):
        options = ["取消", "骇入", "逃跑"]
        # 特化：仅「变量」拥有「静默」动作（三回合静默解锁宽恕的隐藏彩蛋）
        if self.enemy_data and self.enemy_data.get("id") == "snow_1_2_variable":
            options.append("静默")
        return options

    def handle_act_input(self, event):
        display_actions = self.get_act_options()
        
        if event.key == pygame.K_x or event.key == pygame.K_ESCAPE:
            self.current_phase = self.PHASE_MENU
            self.act_selection_idx = 0
        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
            self.act_selection_idx = (self.act_selection_idx - 1) % len(display_actions)
        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
            self.act_selection_idx = (self.act_selection_idx + 1) % len(display_actions)
        elif event.key == pygame.K_UP or event.key == pygame.K_w:
            self.act_selection_idx = (self.act_selection_idx - 2) % len(display_actions)
        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
            self.act_selection_idx = (self.act_selection_idx + 2) % len(display_actions)
        elif event.key == pygame.K_z or event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            selected_act = display_actions[self.act_selection_idx]
            if selected_act == "取消":
                self.current_phase = self.PHASE_MENU
                self.act_selection_idx = 0
            elif selected_act == "骇入":
                self.silent_streak = 0
                self.do_hack()
            elif selected_act == "逃跑":
                self.silent_streak = 0
                self.action_text = "* 你逃跑了。"
                self._exit_battle()
            elif selected_act == "静默":
                # 变量彩蛋：三回合静默解锁宽恕
                self.silent_streak += 1
                if self.silent_streak >= 3:
                    self.silent_streak = 3
                    if self.game_state is not None:
                        self.game_state.mercy_unlocked = True
                    self.action_text = "* 你第三次沉默。某种边界，悄然松动了。"
                else:
                    self.action_text = "* 你沉默不语。"
                self.current_phase = self.PHASE_PLAYER_ANIM
                self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                self.action_timer = 60
            else:
                 self.action_text = f"* 你进行了 {selected_act}。"
                 self.current_phase = self.PHASE_PLAYER_ANIM
                 self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                 self.action_timer = 60

    def do_hack(self):
        if self.hack_count < 5:
            self.hack_count += 1
            # Increased slow-down effect from 10% to 15% per hack based on user feedback
            factor = 0.85 
            self.bullet_speed_multiplier *= factor
            for b in self.bullets:
                if hasattr(b, 'vx'): b.vx *= factor
                if hasattr(b, 'vy'): b.vy *= factor
                if hasattr(b, 'speed'): b.speed *= factor
                # Fix for YellowBullet in WAIT state
                if hasattr(b, 'target_vx'): b.target_vx *= factor
                if hasattr(b, 'target_vy'): b.target_vy *= factor
            
            # Also slow down shield arrows if active
            if hasattr(self, 'shield_arrows'):
                for arrow in self.shield_arrows:
                    if 'speed' in arrow:
                        arrow['speed'] *= factor
                        
            self.action_text = f"* 骇入成功！弹幕速度降低15% (剩余次数: {5 - self.hack_count})"
        else:
            self.action_text = "* 骇入次数已耗尽。"
        
        self.current_phase = self.PHASE_PLAYER_ANIM
        self.next_phase_after_anim = self.PHASE_ENEMY_TURN
        self.action_timer = 60

    def handle_item_input(self, event):
        # Consolidate inventory to merge duplicates before filtering
        display_items, consumables = self._build_consumable_list()
        
        if event.key == pygame.K_x or event.key == pygame.K_ESCAPE:
            self.current_phase = self.PHASE_MENU
            self.item_selection_idx = 0
        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
            self.item_selection_idx = (self.item_selection_idx - 1) % len(display_items)
        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
            self.item_selection_idx = (self.item_selection_idx + 1) % len(display_items)
        elif event.key == pygame.K_UP or event.key == pygame.K_w:
            self.item_selection_idx = (self.item_selection_idx - 2) % len(display_items)
        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
            self.item_selection_idx = (self.item_selection_idx + 2) % len(display_items)
        elif event.key == pygame.K_z or event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            self.use_item(display_items, consumables)

    def use_item(self, display_items, consumables_list=None):
        if self.item_selection_idx == 0: # Cancel
            self.current_phase = self.PHASE_MENU
            self.item_selection_idx = 0
        elif self.item_selection_idx == 1: # Battery
            if self.player.battery_count > 0:
                if self.player.hp < self.player.max_hp:
                    self.player.hp = min(self.player.hp + 10, self.player.max_hp)
                    self.player.battery_count -= 1
                    self.action_text = "* 你使用了能量电池。 HP +10。"
                    self.current_phase = self.PHASE_PLAYER_ANIM
                    self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                    self.action_timer = 60
                    self.item_selection_idx = 0
                else:
                    self.action_text = "* 你的HP已满。"
                    self.current_phase = self.PHASE_PLAYER_ANIM
                    self.next_phase_after_anim = self.PHASE_MENU
                    self.action_timer = 60
            else:
                self.action_text = "* 你没有能量电池了。"
                self.current_phase = self.PHASE_PLAYER_ANIM
                self.next_phase_after_anim = self.PHASE_MENU
                self.action_timer = 60
        else:
            # Other items from filtered consumables list
            real_item_idx = self.item_selection_idx - 2
            
            # Use passed consumables list if available, otherwise fallback
            target_list = consumables_list if consumables_list is not None else self.player.inventory
            
            if 0 <= real_item_idx < len(target_list):
                item = target_list[real_item_idx]
                item_name = item.get("name", "Unknown")
                
                # Use Logic
                if item_name == "投掷电池":
                     damage = 20
                     self.enemy_hp -= damage
                     self._spawn_damage_popup(damage, (255, 0, 0), [self.enemy_rect.centerx, self.enemy_rect.top - 30])
                     if self.enemy_hp < 0: self.enemy_hp = 0

                     # Decrement/Remove
                     if hasattr(self.player, 'remove_item'):
                         self.player.remove_item(item_name, 1)
                     else:
                         if item in self.player.inventory:
                             self.player.inventory.remove(item)

                     self.action_text = f"* 你投掷了电池！对敌人造成了 {damage} 点伤害。"

                     self.current_phase = self.PHASE_PLAYER_ANIM
                     self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                     self.action_timer = 90
                     self.item_selection_idx = 0
                elif item_name == "测试":
                     damage = 1000
                     self.enemy_hp -= damage
                     self._spawn_damage_popup(damage, (255, 0, 0), [self.enemy_rect.centerx, self.enemy_rect.top - 30])
                     if self.enemy_hp < 0: self.enemy_hp = 0

                     self.action_text = f"* 你使用了测试道具，对敌人造成了 {damage} 点伤害！"

                     # 测试道具不消耗，方便反复秒杀
                     self.current_phase = self.PHASE_PLAYER_ANIM
                     self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                     self.action_timer = 90
                     self.item_selection_idx = 0
                elif item_name == "电磁脉冲":
                     # 只对失败之作有效：瓦解它的秒杀机制（永久）
                     if "failure_enemy" in self.enemy_data.get("id", ""):
                         self.failure_emp_used = True
                         if self.game_state is not None:
                             self.game_state.failure_emp_used = True
                         self.anthe_glitch_timer = 90
                         self.action_text = "* 你释放了电磁脉冲！失败之作的秒杀机制被瓦解了。"

                         # 消耗道具
                         if hasattr(self.player, 'remove_item'):
                             self.player.remove_item(item_name, 1)
                         else:
                             if item in self.player.inventory:
                                 self.player.inventory.remove(item)

                         self.current_phase = self.PHASE_PLAYER_ANIM
                         self.next_phase_after_anim = self.PHASE_ENEMY_TURN
                         self.action_timer = 90
                         self.item_selection_idx = 0
                     else:
                         self.action_text = "* 电磁脉冲对眼前的敌人没有效果。"
                         self.current_phase = self.PHASE_PLAYER_ANIM
                         self.next_phase_after_anim = self.PHASE_MENU
                         self.action_timer = 60
                         self.item_selection_idx = 0
                else:
                    self.action_text = f"* 使用了 {item_name}，但什么也没发生。"
                    self.current_phase = self.PHASE_PLAYER_ANIM
                    self.next_phase_after_anim = self.PHASE_MENU
                    self.action_timer = 60
                    self.item_selection_idx = 0

    def handle_mercy_input(self, event):
        display_mercy = ["取消", "宽恕"]
        if event.key == pygame.K_x or event.key == pygame.K_ESCAPE:
            self.current_phase = self.PHASE_MENU
            self.mercy_selection_idx = 0
        elif event.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
             self.mercy_selection_idx = (self.mercy_selection_idx + 1) % 2
        elif event.key in [pygame.K_z, pygame.K_RETURN, pygame.K_SPACE]:
            if self.mercy_selection_idx == 0:
                self.current_phase = self.PHASE_MENU
                self.mercy_selection_idx = 0
            else:
                self.action_text = f"* 你原谅了 {self.enemy_data.get('name', '敌人')}。"
                self._exit_battle()

    def handle_flee_input(self, event):
        display_flee = ["取消", "逃跑"]
        if event.key == pygame.K_x or event.key == pygame.K_ESCAPE:
            self.current_phase = self.PHASE_MENU
            self.flee_selection_idx = 0
        elif event.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
             self.flee_selection_idx = (self.flee_selection_idx + 1) % 2
        elif event.key in [pygame.K_z, pygame.K_RETURN, pygame.K_SPACE]:
            if self.flee_selection_idx == 0:
                self.current_phase = self.PHASE_MENU
                self.flee_selection_idx = 0
            else:
                self.action_text = "* 你逃跑了。"
                self._exit_battle()
