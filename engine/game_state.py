class GameState:
    def __init__(self):
        self.sync_rate = 50
        self.current_era = 'Ice_Wind_Era'
        self.show_terminal_dialog = False
        self.activated_bonfires = ["start"] # Default: Start bonfire is active
        self.collected_items = [] # IDs of collected items to prevent respawn
        self.cleared_bosses = [] # IDs of defeated bosses/cleared fog gates
        self.temp_killed_enemies = [] # IDs of enemies killed in current cycle (reset on rest/death)
        
        # Respawn Logic
        self.last_rest_map_id = "start"
        self.last_rest_pos = (128 * 3, 128 * 5)
        
        # Navigation State
        self.last_entry_type = None
