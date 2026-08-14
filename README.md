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
├── main.py              # 主入口（Game 类 + 状态机）
├── bullet_designer.py   # 可视化弹幕设计器
├── engine/              # 核心引擎
│   ├── config.py        # 全局常量（屏幕、颜色、速度等）
│   ├── game_state.py    # 游戏状态管理（篝火/道具/BOSS持久化）
│   ├── map_data.py      # MAP_CONFIG 地图配置
│   ├── enemy_data.py    # BATTLE_DATA 敌人战斗数据
│   ├── save_system.py   # 存档 / 读档
│   ├── map_builder.py   # 每张地图的实体/道具/雾门生成
│   ├── battle_system.py # BattleManager 核心（组装各 mixin）
│   ├── battle_menus.py  # 战斗菜单 mixin（QTE/ACT/ITEM/MERCY/FLEE）
│   ├── battle_spawner.py# 弹幕生成 mixin
│   ├── battle_shield.py # 护盾小游戏 mixin
│   ├── battle_render.py # 战斗渲染 mixin
│   ├── pattern_loader.py# JSON 弹幕模式加载器
│   ├── camera.py        # 摄像机跟随
│   ├── tile_manager.py  # 瓦片地图加载与碰撞
│   ├── audio.py         # BGM 加载/切换
│   └── utils.py         # 资源路径解析、字体加载
├── entities/            # 实体系统
│   ├── player.py        # 玩家（动画、背包、属性）
│   ├── enemies.py       # 大地图敌人（OverworldEnemy、Bonfire、FailureEnemy）
│   ├── bullets.py       # 弹幕子弹（普通/激光/方块/等离子刃）
│   ├── items.py         # 可收集道具
│   ├── props.py         # 场景道具 Prop
│   └── particles.py     # 战斗粒子（BattleDust / DebrisParticle）
├── ui/                  # UI 系统
│   ├── menus.py         # 标题/暂停/篝火/传送/背包/音量菜单
│   ├── dialogue.py      # 对话系统（肖像框 + 文字）
│   ├── effects.py       # 特效（雪花、雾气、数据尘埃、雾门）
│   └── atmosphere.py    # 大气特效（Pipe/Pulse Atmosphere、FogMaze）
├── assetsDB/            # 资源仓库（图片/音频/地图瓦片）
│   ├── audio/           # BGM + 音效
│   ├── characters/      # 角色精灵（玩家 + 敌人）
│   ├── items/           # 道具动画
│   ├── maps/            # 地图瓦片集
│   ├── objects/         # 场景物件（篝火等）
│   └── ui/              # UI 素材（背景/肖像/图标）
├── savegame.json        # 存档文件
└── build_exe.py         # PyInstaller 打包脚本
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
| `maps/star_sea_plaza/` | 星海广场 | 上升路线终点 |
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
| `audio/bgm/new_items.wav` | new items.wav | 道具获取BGM |
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
上升路线（击败鬼武士后向左，通往地表）：
            pipe_nightmare_2_2 → pipe_ascent_1 → pipe_ascent_2 → pipe_ascent_3 → star_sea_plaza
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
| 失败之作 | pipe_nightmare_3_3 → 鬼武士死后转移到 pipe_ascent_3 | BOSS | 噪音机制 + 秒杀（需电磁脉冲瓦解） |

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

- 部分中文文件名在非 Windows 系统可能出现编码问题
- `build_exe.py` 路径断言未充分测试
- 失败之作「电磁脉冲解除秒杀」后的正式攻击弹幕尚未实装（当前仅解除秒杀后按普通流程对战）

## 本次更新（2026-08-14）

- 🆕 **上升管道路线**：击败鬼武士后，向左进入通往地表的三张连续管道图 `pipe_ascent_1 → pipe_ascent_2 → pipe_ascent_3`，复用「管道噩梦1-2」的横向管道素材（`maps/pipe_nightmare_3` + `is_pipe_channel`），一路向左指引。
- 🕯️ **阴湿管道篝火**：`pipe_ascent_2`（改名「阴湿管道」）屏幕正中间新增篝火存档点。
- ⚡ **电磁脉冲道具**：`pipe_ascent_1` 放置光点「电磁脉冲」（id=`emp_pulse`），战斗中用于瓦解失败之作的秒杀机制（永久生效，读档不失效）。
- 👻 **失败之作转移**：鬼武士死亡后，失败之作从 `pipe_nightmare_3_3` 消失，转而出现在 `pipe_ascent_3` 最左侧，把守通往地表的路。
- 🚶 **失败之作缓慢漂移**：在上升管道3中它只显示「向右移动」贴图，缓慢向右行走营造压迫感；仅当玩家距离 ≤90px 时转为正常追逐（可上下移动，用正常动作贴图）。
- 🔫 **失败之作战斗**：此战玩家必先手，等待使用电磁脉冲解除其秒杀；EMP 后按普通流程对战（正式攻击弹幕待后续实装）。
- 🧪 **测试道具「测试」**：开局自动加入背包，战斗中造成 1000 伤害且不消耗，便于快速测试路线。

## 开发认知（备忘）

- **地图边方向语义**：`MAP_CONFIG` 中 `next`=右边缘、`prev`=左边缘、`down`=底边、`up`=顶边；`run_transition` 按进入方向在对应边缘生成出生点（left→x=20、right→x=W-w-20 等）。
- **`is_pipe_channel`**：设为 `True` 会把上两行 + 下两行设为障碍，只留第 2、3 行可通行（y∈[256,512)），并限制玩家 Y 坐标；`is_vertical_pipe_channel` 是 X 轴等价物。
- **失败之作秒杀机制**：在 `start_enemy_turn` 中当 `enemy_data["id"]` 含 `failure_enemy` 时调用 `handle_player_death()`；战斗默认玩家先手（`PHASE_MENU`），故秒杀只在敌方回合触发。
- **失败之作帧语义**：`default_facing="left"` 表示基础帧朝左；`01.png`=待机、`02.png`=战斗立绘、`03~12.png`=动作帧。朝右需水平翻转。
- **EMP 持久化**：用 `game_state.failure_emp_used`（写入存档）记录是否已瓦解，避免死亡/读档后重新陷入秒杀软锁。
- **亚像素移动**：`self.pos` 必须是浮点累加器；若用 `int(self.rect.x)` 反向覆盖会丢失小数位移，导致漂移等缓速移动失效。

## 致谢

本项目使用 Trae + Claude 通过 vibecoding 方式开发完成。角色与场景素材由 AI 生成。

更新日志见 [CHANGELOG.md](CHANGELOG.md)
