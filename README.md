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
├── maps/                # [历史遗留] 旧版地图瓦片，已迁移到 assetsDB/maps/
├── savegame.json        # 存档文件
└── build_exe.py         # PyInstaller 打包脚本
```

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

- 部分资源路径引用的是旧路径，加载时依赖 `resource_path()` 的多路径回退机制
- `assetsDB/` 中有大量历史遗留素材未清理
- `main.py` 过于庞大（~2300行），地图和敌人配置硬编码在主文件中
- 中文文件名在非 Windows 系统可能出现问题

## 致谢

本项目使用 Trae + Claude 通过 vibecoding 方式开发完成。角色与场景素材由 AI 生成。
