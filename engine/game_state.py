class GameState:
    def __init__(self):
        self.sync_rate = 50
        self.current_era = 'Ice_Wind_Era'
        self.show_terminal_dialog = False
        self.activated_bonfires = ["start"] # Default: Start bonfire is active
        self.collected_items = [] # IDs of collected items to prevent respawn
        self.cleared_bosses = [] # IDs of defeated bosses/cleared fog gates
        self.temp_killed_enemies = [] # IDs of enemies killed in current cycle (reset on rest/death)
        self.failure_emp_used = False # 失败之作的秒杀机制是否已被电磁脉冲瓦解（永久）
        self.seen_lines = [] # 阿尔忒独白去重（区域/遭遇/特殊，永久）
        self.final_boss_defeated = False # 是否已击败最终boss（二周目信号；当前无最终boss，恒为False）
        self.mercy_unlocked = False # 本周目是否解锁宽恕（变量处三回合静默彩蛋；每周目重置）
        
        # Respawn Logic
        self.last_rest_map_id = "start"
        self.last_rest_pos = (128 * 3, 128 * 5)
        
        # Navigation State
        self.last_entry_type = None
