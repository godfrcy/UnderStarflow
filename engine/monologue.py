# 阿尔忒的独白触发表（2026-08-14）
# 侦察报告式：辨认 + 评估，短句、冷克制，不抒情。
# 去重用 game_state.seen_lines（列表），见键即弹过一次不再重复。
# 显示时按标点断行，保证每行不超过 20 字。

MAX_LINE_CHARS = 20
_SPLIT_CHARS = "，。？！；："


def _split_lines(text, max_chars=MAX_LINE_CHARS):
    """按逗号/句号等标点断行，保证每行不超过 max_chars 字。"""
    lines = []
    current = ""
    for ch in text:
        current += ch
        if ch in _SPLIT_CHARS:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)

    # 超长行二次硬截断
    result = []
    for line in lines:
        while len(line) > max_chars:
            result.append(line[:max_chars])
            line = line[max_chars:]
        if line:
            result.append(line)
    return result


# --- 区域进入（按 map_id） ---
AREA_LINES = {
    "start": "...真冷啊",
    "base_1": "机凯种已经放弃的外围基地，设施还在自动运转。",
    "pipe_nightmare_3": "旧时代的地下管道网络，二十世纪的北方地底。",
    "pipe_ascent_1": "向上的通道，离地表很近了。",
    "star_sea_plaza": "旧时代的大连星海广场。这里曾是看海、看星的地方。",
}

# --- 敌人遭遇（按「类型」去重；两个暴走变量、两处废弃机器人共用一句） ---
ENCOUNTER_LINES = {
    "variable": "……离开主机网络的劣等机器，清理掉就好。",
    "machine": "机凯种。和我一样，被主机操纵着。",
    "rebel": "格里菲斯的部队，为什么会出现在这里？",
    "rebel_soldier": "格里菲斯的残兵，装备是搜刮来的旧军火。",
    "black_ranger": "黑游侠，旧时代遗留的武装机体。",
    "berserk": "劣等机器，在这里失控暴走了。",
    "abandoned_robot": "被主机淘汰的废弃机体，和我同款。",
    "ghost_samurai": "旧时代的守卫。它为什么会守在这里？",
    "failure": "失败之作，被主机封锁的禁忌原型。",
    "twin_dancer": "……没有呼吸的舞者，被主机留在管道里的旧人偶。",
    "ufo": "……还在自动巡航的旧飞行器，主机没有回收它。",
}

# battle_data 的 id / boss_id → 遭遇类型
_ENCOUNTER_TYPE_BY_KEY = {
    "snow_1_2_variable": "variable",
    "base_2_machine": "machine",
    "base_3_admin": "rebel",
    "base_4_rebel_soldier": "rebel_soldier",
    "base_5_boss": "black_ranger",
    "pipe_nightmare_1_laser": "berserk",
    "pipe_nightmare_1_jump": "berserk",
    "pipe_nightmare_1_3_robot": "abandoned_robot",
    "pipe_nightmare_2_3_robot": "abandoned_robot",
    "pipe_nightmare_3_1_robot_mk2": "abandoned_robot",
    "pipe_nightmare_3_2_twin_dancer": "twin_dancer",
    "pipe_nightmare_3_1_ufo": "ufo",
    "pipe_2_2_boss": "ghost_samurai",
    "failure_enemy_01": "failure",
}


def area_line(map_id):
    """返回该地图的区域独白（已断行的行列表）；无则 None。"""
    text = AREA_LINES.get(map_id)
    return _split_lines(text) if text else None


def encounter_line(battle_data):
    """返回 (seen_key, lines)；该敌人无独白时返回 (None, None)。"""
    if not battle_data:
        return None, None
    key = battle_data.get("id") or battle_data.get("boss_id")
    if key is None:
        return None, None
    etype = _ENCOUNTER_TYPE_BY_KEY.get(key)
    if etype is None:
        return None, None
    return f"encounter:{etype}", _split_lines(ENCOUNTER_LINES[etype])
