import json
import os


# --- Save/Load System ---

def save_game(player, game_state, current_map_id, difficulty="explore"):
    """
    Save game data to savegame.json using atomic write to prevent corruption.
    """
    data = {
        "difficulty": difficulty,
        "player": {
            "hp": player.hp,
            "max_hp": player.max_hp,
            "level": getattr(player, "level", 1),
            "exp": getattr(player, "exp", 0),
            "max_exp": getattr(player, "max_exp", 100),
            "attack": getattr(player, "attack", 10),
            "x": player.rect.x,
            "y": player.rect.y,
            "inventory": player.inventory,
            "battery_count": player.battery_count
        },
        "game_state": {
            "current_era": game_state.current_era,
            "sync_rate": game_state.sync_rate,
            "show_terminal_dialog": game_state.show_terminal_dialog,
            "activated_bonfires": game_state.activated_bonfires,
            "collected_items": game_state.collected_items,
            "cleared_bosses": game_state.cleared_bosses,
            "last_rest_map_id": game_state.last_rest_map_id,
            "last_rest_pos": game_state.last_rest_pos,
            "current_map_id": current_map_id,
            "last_entry_type": game_state.last_entry_type,
            "failure_emp_used": game_state.failure_emp_used,
            "seen_lines": game_state.seen_lines,
            "final_boss_defeated": game_state.final_boss_defeated,
            "mercy_unlocked": game_state.mercy_unlocked
        }
    }

    target_file = "savegame.json"
    temp_file = f"{target_file}.tmp"

    try:
        with open(temp_file, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # Atomic replace
        if os.path.exists(target_file):
            os.remove(target_file)
        os.rename(temp_file, target_file)

        print("Game Saved Successfully.")
        return True
    except Exception as e:
        print(f"Failed to save game: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False


def load_game(player, game_state):
    """
    Load game data from savegame.json with error handling.
    Returns (success, map_id)
    """
    if not os.path.exists("savegame.json"):
        print("No save file found.")
        return False, "start", "explore"

    try:
        with open("savegame.json", "r", encoding='utf-8') as f:
            data = json.load(f)

        # Validate critical fields
        if "player" not in data or "game_state" not in data:
            raise ValueError("Invalid save file structure")

        p_data = data["player"]
        player.level = p_data.get("level", 1)
        player.exp = p_data.get("exp", 0)
        # 经验需求随等级递增，读取时按等级重算（忽略旧档的固定 max_exp）
        player.max_exp = 10 * player.level
        # 数值大换血：HP +3/级、ATK +2/级，读档按等级重算（旧档 +10/+10 自动迁移）
        player.max_hp = 20 + (player.level - 1) * 3
        player.attack = 10 + (player.level - 1) * 2
        # 旧档满级 hp 可能达 210，收敛到新上限 77
        player.hp = min(p_data.get("hp", player.max_hp), player.max_hp)
        player.rect.x = p_data.get("x", 128 * 2)
        player.rect.y = p_data.get("y", 128 * 5)
        player.inventory = p_data.get("inventory", [])
        player.battery_count = p_data.get("battery_count", 3)

        # 物品迁移：boss 战利品统一命名 + 补特殊 tag（兼容旧存档）
        for item in player.inventory:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if name == "鬼武士的断刃":
                item["name"] = "鬼武士的动力炉"
                item["description"] = "鬼武士的核心部件"
                item["tag"] = "boss_trophy"
            elif name in ("黑色游侠的动力炉", "鬼武士的动力炉"):
                item.setdefault("tag", "boss_trophy")

        g_data = data["game_state"]
        game_state.current_era = g_data.get("current_era", "Ice_Wind_Era")
        game_state.sync_rate = g_data.get("sync_rate", 50)
        game_state.show_terminal_dialog = g_data.get("show_terminal_dialog", False)
        game_state.activated_bonfires = g_data.get("activated_bonfires", ["start"])
        game_state.collected_items = g_data.get("collected_items", [])
        game_state.cleared_bosses = g_data.get("cleared_bosses", [])
        game_state.last_rest_map_id = g_data.get("last_rest_map_id", "start")
        game_state.last_rest_pos = tuple(g_data.get("last_rest_pos", (128 * 3, 128 * 5)))
        game_state.last_entry_type = g_data.get("last_entry_type", None)
        game_state.failure_emp_used = g_data.get("failure_emp_used", False)
        game_state.seen_lines = g_data.get("seen_lines", [])
        game_state.final_boss_defeated = g_data.get("final_boss_defeated", False)
        game_state.mercy_unlocked = g_data.get("mercy_unlocked", False)
        map_id = g_data.get("current_map_id", "start")
        difficulty = data.get("difficulty", "explore")

        print("Game Loaded Successfully.")
        return True, map_id, difficulty

    except json.JSONDecodeError:
        print("Error: Save file is corrupted (JSON Decode Error).")
        return False, "start", "explore"
    except Exception as e:
        print(f"Failed to load game: {e}")
        return False, "start", "explore"
