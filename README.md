# Under Starflow

一个基于 **Pygame** 的 2D 俯视角弹幕躲避 RPG 游戏。结合了 Undertale 式的弹幕战斗和黑暗之魂式的地图探索/篝火存档机制。

## 快速开始

```bash
pip install pygame
python main.py
```

## 项目结构

```
UnderStarflow/
├── main.py              # 主入口（游戏循环 + 地图配置 + 存档系统）
├── engine/              # 核心引擎
│   ├── config.py        # 全局常量（屏幕、颜色、速度等）
│   ├── game_state.py    # 游戏状态管理（篝火/道具/BOSS持久化）
│   ├── battle_system.py # 弹幕战斗系统
│   ├── camera.py        # 摄像机跟随
│   ├── tile_manager.py  # 瓦片地图加载与碰撞
│   ├── audio.py         # BGM 加载/切换
│   └── utils.py         # 资源路径解析、字体加载
├── entities/            # 实体系统
│   ├── player.py        # 玩家（动画、背包、属性）
│   ├── enemies.py       # 大地图敌人（OverworldEnemy、Bonfire、FailureEnemy）
│   ├── bullets.py       # 弹幕子弹（普通/激光/方块/等离子刃）
│   └── items.py         # 可收集道具
├── ui/                  # UI 系统
│   ├── menus.py         # 标题/暂停/篝火/传送/背包/音量菜单
│   ├── dialogue.py      # 对话系统（肖像框 + 文字）
│   └── effects.py       # 特效（雪花、雾气、数据尘埃、雾门）
├── assetsDB/            # 资源仓库（图片/音频/地图瓦片）
│   ├── audio/           # BGM + 音效
│   ├── characters/      # 角色精灵（玩家 + 敌人）
│   ├── items/           # 道具动画
│   ├── maps/            # 地图瓦片集
│   ├── objects/         # 场景物件（篝火等）
│   └── ui/              # UI 素材（背景/肖像/图标）
├── savegame.json        # 存档文件
└── build_exe.py         # PyInstaller 打包脚本
└── build_game.py        #  备选打包脚本
```

## 资源中英文对照

| 英文路径 | 中文原名 | 用途 |
|----------|----------|------|
| **敌人 (Enemies)** | | |
| `characters/enemies/abandoned_robot/` | 废弃机器人 | 废弃机器人精灵 |
| `characters/enemies/abandoned_robot_mk2/` | 废弃机器人二型 | 废弃机器人变体 |
| `characters/enemies/berserk_variable/` | 新版变量 | 变量敌人精灵 |
| `characters/enemies/black_ranger/` | 黑游侠 | 黑游侠BOSS精灵 |
| `characters/enemies/failure_boss/` | 失败之作 | 失败之作BOSS |
| `characters/enemies/ghost_soldier/` | 幽灵士兵 | 幽灵士兵精灵 |
| `characters/enemies/ghost_soldier_mk2/` | d2f465..网格 | 幽灵士兵变体 |
| `characters/enemies/machine_soldier/` | 机凯种 (jikaizhong) | 机械士兵精灵 |
| `characters/enemies/new_soldier/` | 新型士兵 | 新型士兵精灵 |
| `characters/enemies/rebel_leader/` | 义军首领 / 最后一版 | 义军首领精灵 |
| `characters/enemies/rebel_walker/` | 义军行走 | 义军行走精灵 |
| `characters/enemies/samurai_ghost/` | 鬼武士 | 鬼武士BOSS精灵 |
| `characters/enemies/variable/` | 变量 | 原版变量敌人 |
| `characters/enemies/variable_anim/` | 变量动画 | 变量动画帧 |
| `characters/enemies/variable_jump/` | 暴走变量_跳跃 | 跳跃型暴走变量 |
| `characters/enemies/variable_laser/` | 暴走变量_激光 | 激光型暴走变量 |
| **地图 (Maps)** | | |
| `maps/base_4/` | 基地4 | 基地第四层地图 |
| `maps/demo_map/` | demo地图 | 演示地图 |
| `maps/pipe_nightmare_2_2/` | 管道噩梦2-2 | 鬼武士BOSS房间 |
| `maps/pipe_nightmare_3_2/` | 管道噩梦3-2 | 深层管道地图 |
| `maps/pipe_nightmare_3_3/` | 管道噩梦3-3 | 失败之作BOSS房间 |
| `maps/snow_1_2/` | 雪地1.2 | 雪地第二层 |
| `maps/snow_1_3/` | 雪地1.3 | 雪地第三层 |
| `maps/snow_start/` | 雪地grid | 起始雪地 |
| `maps/tileset_generic/` | 瓦片地图01 | 通用瓦片集 |
| **物件 (Objects)** | | |
| `objects/console/` | 操作台 | 控制台道具 |
| `objects/props/` | 路灯/显示器 | 场景道具 |
| `objects/bonfire/` | fire_grid | 篝火动画 |
| **音频 (Audio)** | | |
| `audio/bgm/city_ruins.mp3` | city ruins.mp3 | 城市废墟BGM |
| `audio/bgm/heroism.mp3` | 英雄主义.mp3 | 英雄主义BGM |
| `audio/bgm/hi.mp3` | Hi.MP3 | Hi BGM |
| `audio/bgm/machine_knight.mp3` | jikaizhong.mp3 | 机凯种战斗BGM |
| `audio/bgm/new_items.mp3` | new items.mp3 | 道具获取BGM |
| `audio/bgm/new_map.mp3` | new map.mp3 | 新地图BGM |
| `audio/bgm/old_doll.mp3` | old doll.mp3 | 旧玩偶BGM |
| `audio/bgm/oldcore.mp3` | 旧核.mp3 | 管道噩梦BGM |
| `audio/bgm/the_fish.mp3` | the fish.MP3 | 义军首领BGM |
| `audio/bgm/the_tree.mp3` | the tree.mp3 | 树BGM |
| `audio/sfx/glitch.mp3` | 故障音.mp3 | 故障音效 |
| `audio/sfx/hit_sound.mp3` | sound.MP3 | 击中音效 |
| **UI** | | |
| `ui/portraits/anthe_portrait.png` | 阿尔忒半身像 | 对话肖像 |
| `ui/portraits/portrait_frame.png` | 头像框 | 肖像边框 |
| `ui/inventory/new_backpack.png` | 新背包图片 | 背包UI |
| `ui/misc/dialog_box.png` | 对话框 | 对话框背景 |
| `ui/misc/light_point.png` | 光点透明图 | 光点特效 |
| `ui/sync_rate.png` | 同步率 | 同步率图标 |

## 游戏机制

### 地图系统
- 地图为 **6×6 瓦片** 网格（768×768 px）
- 每个瓦片 128×128 px，前两行为默认障碍物
- 地图之间通过上下左右边缘过渡连接
- 支持管道通道（限制可通行列/行）、迷宫障碍物、雾墙等机制

### 地图链路
```
雪地区域：  start → snow_1_2 → snow_1_3
基地区域：  base_1 → base_2 → base_3 → base_4 → base_5
管道噩梦：  pipe_nightmare_1 → pipe_nightmare_2
            pipe_nightmare_1_2 → pipe_nightmare_1_3
            pipe_nightmare_2_1 → pipe_nightmare_2_2 → pipe_nightmare_2_3
            pipe_nightmare_3_1 → pipe_nightmare_3_2 → pipe_nightmare_3_3
```

### 战斗系统
- 回合制 + 实时弹幕躲避混合
- 战斗区域为屏幕底部弹幕盒
- 多种弹幕类型：普通子弹、延时激光（部分追踪）、方块、等离子刃、激光网络
- 通过 ACT 菜单推进战斗进度

### 敌人
| 敌人 | 位置 | 类型 | 特色 |
|---|---|---|---|
| 变量 | snow_1_2 | 普通 | laser/cube |
| 机凯种 | base_2 | 普通 | 激光网络 |
| 义军首领 | base_3 | 追逐型 | 主动追玩家 |
| 黑游侠EX | base_5 | BOSS | 雾门封锁 |
| 暴走变量×2 | pipe_nightmare_1 | 普通 | 激光/跳跃 |
| 废弃机器人 | pipe_nightmare_1_3, 2_3 | 追逐型 | AI追玩家 |
| 鬼武士 | pipe_nightmare_2_2 | BOSS | 黑暗弹/火焰墙/重力跳 |
| 失败之作 | pipe_nightmare_3_3 | BOSS | 噪音机制 |

### 存档系统
- 篝火存档（类似魂系），休息后敌人刷新
- 已击败的 BOSS 永久清除
- 已收集的道具不重复生成
- 原子写入防存档损坏

## 操作

- **方向键**：移动 / 菜单选择
- **Z / Enter**：确认 / 交互
- **X / Esc**：取消 / 打开菜单
- **C**：冲刺（战斗中）

## 技术栈

- Python 3.8+
- Pygame
- PyInstaller（打包为 exe）

## 已知问题

- `main.py` 过于庞大（~2300行），地图和敌人配置硬编码在主文件中，后续需拆分
- 部分中文文件名在非 Windows 系统可能出现编码问题
- `build_exe.py` 路径断言未充分测试

## 致谢

本项目使用 Trae + Claude 通过 vibecoding 方式开发完成。角色与场景素材由 AI 生成。

更新日志见 [CHANGELOG.md](CHANGELOG.md)
