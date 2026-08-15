# --- 敌人战斗数据定义（原 main.py load_map 内联 dict 搬来） ---

# 废弃机器人：1-3 与 2-3 两份实例共享同一份数据，id 在生成时区分
ABANDONED_ROBOT_DATA = {
    "name": "废弃机器人",
    "hp": 80,
    "skills": ["escape_dust"],
    "acts": ["观察"],
    "image_folder": "characters/enemies/abandoned_robot",
    "image_prefix": "abandoned_robot",
    "is_grid": True,
    "bgm": "audio/bgm/hi.mp3",
}

# 废弃机器人MK2：管道噩梦3-1 的加强版废弃机体，16 帧全用
ABANDONED_ROBOT_MK2_DATA = {
    "name": "废弃机器人MK2",
    "hp": 100,
    "skills": ["conveyor_belt", "pendulum"],
    "acts": ["观察"],
    "image_folder": "characters/enemies/abandoned_robot_mk2",
    "image_prefix": "abandoned_robot_mk2",
    "is_grid": True,
    # 地狱王子：前 16s 已裁剪掉，整体 1.5 倍速；再跳过开头 0.5s（保险起见用 start 而非裁剪）
    "bgm": "audio/bgm/hell_prince_fast.wav",
    "bgm_start": 1,
}

# 双生舞怜：管道噩梦3-2 的舞者人偶（boss，击败后不再刷新）
# 双阶段战斗：一阶段循环 Angela 前 1:32；血量降到 50% 进二阶段，切 Angela 3:05~结尾
TWIN_DANCER_DATA = {
    "name": "双生舞怜",
    "boss_id": "pipe_3_2_boss",
    "hp": 160,
    "skills": ["dancer_dash", "dancer_chase", "soviet_emblem"],
    "acts": ["观察"],
    "image_folder": "characters/enemies/twin_dancer",
    "image_prefix": "twin_dancer",
    "is_grid": True,
    "bgm": "audio/bgm/angela_phase1.wav",
    "bgm_phase2": "audio/bgm/angela_phase2.wav",
    "phase2_hp_ratio": 0.75,
}

# UFO：管道噩梦3-1 的飞行器（占位战斗数据，技能/数值 待补充）
UFO_DATA = {
    "name": "UFO",
    "hp": 90,
    "skills": ["ufo_tractor"],
    "acts": ["观察"],
    "image_folder": "characters/enemies/ufo",
    "image_prefix": "ufo",
    "is_grid": True,
    "bgm": "audio/bgm/UFO.mp3",
}

BATTLE_DATA = {
    "ghost_samurai": {
        "id": "pipe_2_2_boss",
        "boss_id": "pipe_2_2_boss",
        "name": "鬼武士",
        "hp": 120,
        "skills": ["dark_orb", "samurai_fire_walls", "samurai_gravity_jump"],
        "acts": ["看破"],
        "image_folder": "characters/enemies/samurai_ghost",
        "image_prefix": "samurai_ghost",
        "is_grid": True,
        "bgm": "audio/bgm/brutal.mp3",
    },
    "variable": {
        "id": "snow_1_2_variable",
        "name": "变量",
        "hp": 50,
        "skills": ["laser", "cube", "random_particles"],
        "acts": ["嘲讽", "观察"],
        "image_folder": "characters/enemies/berserk_variable/berserk_variable.png",
        "image_prefix": "variable",
        "is_grid": True,
        # 弃用有透明瑕疵的帧，不删除图片
        "skip_frames": [12, 14],
        "bgm": "audio/bgm/monster_song.mp3",
    },
    "berserk_laser": {
        "id": "pipe_nightmare_1_laser",
        "name": "暴走变量_激光",
        "hp": 80,
        "skills": ["laser", "cube", "random_particles"],
        "acts": ["观察"],
        "image_folder": "characters/enemies/variable_laser/variable_laser_透明.png",
        "image_prefix": "variable_laser",
        "is_grid": True,
        "bgm": "audio/bgm/monster_song.mp3",
    },
    "berserk_jump": {
        "id": "pipe_nightmare_1_jump",
        "name": "暴走变量_跳跃",
        "hp": 80,
        "skills": ["laser", "cube", "random_particles"],
        "acts": ["观察"],
        "image_folder": "characters/enemies/variable_jump/variable_jump透明.png",
        "image_prefix": "variable_jump",
        "is_grid": True,
        "bgm": "audio/bgm/monster_song.mp3",
    },
    "failure": {
        "id": "failure_enemy_01",
        "name": "失败之作",
        "hp": 100,
        "skills": ["noise_attack"],
        "acts": ["聆听"],
        "image_folder": "characters/enemies/failure_boss",
        "image_prefix": "failure",
        "bgm": "audio/bgm/old_doll.mp3",
        "bgm_start": 4.0,
        "bgm_volume": 0.5,
    },
    "black_ranger": {
        "name": "黑游侠EX",
        "hp": 150,
        "skills": ["black_ranger_a", "black_ranger_b", "black_ranger_c"],
        "acts": ["嘲讽", "观察"],
        "boss_id": "base_5_boss",
        "bgm": "audio/bgm/heroism.mp3",
        "image_folder": "characters/enemies/black_ranger",
        "image_prefix": "black_ranger",
        "is_grid": True,
        "flip": True,
    },
    "machine_soldier": {
        "id": "base_2_machine",
        "name": "机凯种",
        "hp": 50,
        "skills": ["ruin_cutting_sequence", "laser_network"],
        "acts": ["嘲讽", "观察"],
        "image_folder": "characters/enemies/machine_soldier",
        "image_prefix": "jikaizhong",
        "is_grid": True,
        # 弃用有白块瑕疵的帧，不删除图片
        "skip_frames": [1, 10, 11, 12, 13],
        "bgm": "audio/bgm/machine_knight.mp3",
        "bgm_start": 17.5,
    },
    "admin": {
        "id": "base_3_admin",
        "name": "admin",
        "hp": 100,
        "skills": ["admin_shield", "admin_laser_cut", "admin_particle_sphere"],
        "acts": ["嘲讽", "观察"],
        "image_folder": "characters/enemies/rebel_leader",
        "image_prefix": "rebel_leader",
        "is_grid": True,
        "bgm": "audio/bgm/the_fish.mp3",
        "anim_speed": 12,
    },
    "rebel_soldier": {
        "id": "base_4_rebel_soldier",
        "name": "义军士兵",
        "hp": 60,
        "skills": ["ruin_cutting_sequence", "laser_network"],
        "acts": ["观察"],
        "image_folder": "characters/enemies/rebel_soldier",
        "image_prefix": "rebel_soldier",
        "is_grid": True,
        # 保留 1_1 ~ 2_2 六帧作行走循环，其余 10 帧跳过
        "skip_frames": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        "bgm": "audio/bgm/the_fish.mp3",
        "anim_speed": 12,  # 战斗立绘动画与地图实体 ANIM_SPEED=12 保持一致
    },
}
