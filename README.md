# Under Starflow

一个基于 **Pygame** 的 2D 俯视角弹幕躲避 RPG 游戏。结合了 Undertale 式的弹幕战斗和黑暗之魂式的地图探索/篝火存档机制。

## 快速开始

```bash
pip install pygame
python main.py
```

## 世界观与剧情（星流之下）

> 玩家操控的正是小说里的女主角 **阿尔忒**——那位金色的机凯种。本作是她的一段前传，填补了《莫斯星寰》与正传《地球停转以后》之间的空档。

### 时间线

```
莫斯星寰（前传）          →    星流之下（本作）        →    地球停转以后（正传）
阿尔忒出身低等工厂          阿尔忒刚杀死莫斯之后         阿尔忒已是屠戮人类的反派
紫瞳→成为执卫者            （本作填补的空档）            罗素/艾因/休比登场
杀死莫斯，获金瞳，仍是诗寇蒂部下   从「负罪的执卫者」           休比牺牲自己把芯片插入她
“莫斯星寰，无喜无悲，无死无生”  →「屠戮人类的恶魔」           阿尔忒=魔鬼
```

一句话概括本作的戏核：**阿尔忒在杀掉自己最爱的莫斯之后，如何一步步变成正传里那个折磨人类、把人当实验品的「魔鬼」。** 这是一个注定的悲剧弧线——正传已经写死了她的结局，所以这游戏真正的悬念不是「她会变成什么」，而是「她为什么、以及怎样变成那样」。

### 标题已经把主题说完了

「星流之下」四个字就是莫斯的梦。莫斯是个穷困潦倒的天文学家，一辈子只想观测 Situ2403、绘制银河、仰望星空。阿尔忒对他许下的约定是：**「我统御这片土地，你观测那片银河，我们两个人加在一起，便共享整个天地。」**

所以「星流之下」= **阿尔忒活在莫斯（星空）之下、却再也够不到那片星空的地方**。她在地下、在黑暗里、在「管道噩梦」里往上爬——爬向地表那道光，可那道光，是死去的莫斯的星。

### 现有素材与世界观对照

| 游戏里已有的东西 | 它在世界观里真正的含义 |
|---|---|
| 管道噩梦（pipe_nightmare） | 旧时代(20xx)的地下管道网络（今天的大连地下），不是出生地，只是通往出生地之路 |
| 失败之作（failure_boss） | 阿尔忒的镜像。她自己就被诗寇蒂骂过「没用的东西」「废品」，说她是「失败之作」 |
| EMP 解除失败之作的秒杀 | 不是「杀死」而是「解除/瓦解」——对应「有些东西杀不死，只能被理解、被解放」 |
| 废弃机器人（abandoned_robot） | 「被抛弃的造物」——阿尔忒出身低等工厂，「这种老基地出产的机体不会被重用」 |
| 义军（rebel） | 格里菲斯将军的叛党，与机凯种天生敌对，见机凯种就杀（常态） |
| 鬼武士（ghost samurai） | 守门人，守在地下与星空之间 |
| 星海广场 | 旧时代(20xx)的大连星海广场，如今已成废墟——路过时抬头看海看星，呼应莫斯的星空梦 |
| 机械心脏图标 + 校准 + 骇入 + 同步率 | 玩家是机凯种的铁证；而「没有心」正是机凯种的痛点，也是休比在正传里毕生寻找的东西 |

### 结局的设计问题（UT 系统的命门）

正传已经把阿尔忒钉死成反派了，本作有两个选择：

- **A. 注定悲剧**（魂系正统）：结局不可改变，玩家做的一切只是「见证她如何堕落」。
- **B. 提供非正史分支**（UT 路线）：宽恕所有失败之作/废弃机器，阿尔忒可能走向另一条结局（但那是「如果」，正传里没发生）。

建议 **B 的内核 + A 的底色**：正史线（杀戮/冷漠）是「注定的堕落」，但给一条隐藏的宽恕线作为「她本可以」。

### 死亡循环的 lore（为什么阿尔忒能复活）

阿尔忒在无主雪地附近偷偷架设了一条**全自动低级躯壳流水线**，把自己的记忆芯片放在那里。一旦死亡，流水线就自动制造一具最低级的躯壳（**廉价、快、但孱弱**），并把记忆芯片复制进去——**她的本体其实还停在能源之城内**，这趟是「远程」来的，死多少次都只是换个便宜壳子。

这零成本地解释了魂系的死亡/篝火/敌人刷新：篝火 = 流水线的记忆备份点，死亡 = 换一具低级躯壳重新载入。也顺手说明了主角为什么初始这么弱——你开的本来就是最便宜的壳。

### 剧情梗概（地图链路叙事）

《莫斯星寰》之后，诗寇蒂仍在掌权，阿尔忒还是她的执卫者。她没请示，**偷偷溜出能源之城**，穿过城外的无主雪地，目的地是她的出生地——**明日指针研究所**。

- **雪地**（snow_start → snow_1_3）：能源之城外的无主雪地，旅程的起点。阿尔忒把记忆芯片留在附近一条「全自动低级躯壳流水线」上——死了就换一具便宜壳子。
- **基地**（base_1 → base_5）：一处机凯种早已放弃的外围基地，地形错综复杂。十年前战败的格里菲斯残党（义军）躲在这里苟活，靠搜刮旧军火为生——义军与机凯种天生敌对，**见了机凯种就杀**，这是常态，不需要理由。
- **管道噩梦**（pipe_nightmare_*）：旧时代(20xx)的地下管道网络，也就是今天大连的地底。基地最深处连着这里，埋着旧时代的「古董」——废弃机器人（和她同源、没被选中的废品）、鬼武士（旧时代守卫）、失败之作（失控被封的禁忌原型）。
- **上升路线**（pipe_ascent_*）：穿过鬼武士把守的通道一路向上。失败之作把守着通往地表的路，只能用电磁脉冲「解除」而非「杀死」。
- **星海广场**（star_sea_plaza）：从管道最深处爬出来，回到地表。这里是旧时代(20xx)的**大连星海广场**，如今已成废墟——她路过时抬头，这里曾是人们看海、看星的地方。离明日指针研究所已经很近了。

一句话：**她不是去挖莫斯的尸骨（那早被溶炼了），而是偷偷回自己的出生地，弄清「自己到底是什么」。**

## 项目结构

```
UnderStarflow/
├── main.py
├── bullet_designer.py
├── engine/
│   ├── config.py
│   ├── game_state.py
│   ├── map_data.py
│   ├── enemy_data.py
│   ├── save_system.py
│   ├── map_builder.py
│   ├── battle_system.py
│   ├── battle_menus.py
│   ├── battle_spawner.py
│   ├── battle_shield.py
│   ├── battle_render.py
│   ├── pattern_loader.py
│   ├── camera.py
│   ├── tile_manager.py
│   ├── audio.py
│   └── utils.py
├── entities/
│   ├── player.py
│   ├── enemies.py
│   ├── bullets.py
│   ├── items.py
│   ├── props.py
│   └── particles.py
├── ui/
│   ├── menus.py
│   ├── dialogue.py
│   ├── effects.py
│   └── atmosphere.py
├── assetsDB/
│   ├── audio/
│   ├── characters/
│   ├── items/
│   ├── maps/
│   ├── objects/
│   └── ui/
├── savegame.json
└── build_exe.py
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
| 废弃机器人MK2 | pipe_nightmare_3_1 | 普通 | 废料传送带切轨 / 重力摆锤 |
| UFO | pipe_nightmare_3_1 | 普通 | 牵引光束（重力列） |
| 双生舞怜 | pipe_nightmare_3_2 | BOSS | 双阶段：黄金分割切割 / 燃烧追逐 / 重力域 |

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
- GitHub 文件列表里每个文件旁显示的「Last commit message」（含 emoji 的旧提交信息）看起来像文件名后的注释，待以后改写提交信息清理（暂不处理）

## 本次更新（2026-08-14）

- 🆕 **上升管道路线**：击败鬼武士后，向左进入通往地表的三张连续管道图 `pipe_ascent_1 → pipe_ascent_2 → pipe_ascent_3`，复用「管道噩梦1-2」的横向管道素材（`maps/pipe_nightmare_3` + `is_pipe_channel`），一路向左指引。
- 🕯️ **阴湿管道篝火**：`pipe_ascent_2`（改名「阴湿管道」）屏幕正中间新增篝火存档点。
- ⚡ **电磁脉冲道具**：`pipe_ascent_1` 放置光点「电磁脉冲」（id=`emp_pulse`），战斗中用于瓦解失败之作的秒杀机制（永久生效，读档不失效）。
- 👻 **失败之作转移**：鬼武士死亡后，失败之作从 `pipe_nightmare_3_3` 消失，转而出现在 `pipe_ascent_3` 最左侧，把守通往地表的路。
- 🚶 **失败之作缓慢漂移**：在上升管道3中它只显示「向右移动」贴图，缓慢向右行走营造压迫感；仅当玩家距离 ≤90px 时转为正常追逐（可上下移动，用正常动作贴图）。
- 🔫 **失败之作战斗**：此战玩家必先手，等待使用电磁脉冲解除其秒杀；EMP 后按普通流程对战（正式攻击弹幕待后续实装）。
- 🧪 **测试道具「测试」**：开局自动加入背包，战斗中造成 1000 伤害且不消耗，便于快速测试路线。
- **星海广场特殊篝火 + 解析系统**：`star_sea_plaza` 新增特殊篝火，首次触碰弹出提示；解锁后所有篝火的休息菜单都会出现「解析」功能。解析会筛选带 `boss_trophy` 特殊 tag 的 boss 战利品（黑游侠「黑色游侠的动力炉」、鬼武士「鬼武士的动力炉」），选中后进入强化二选一（强化 A/B 的具体效果待后续实装）。
- **boss 战利品改名**：「鬼武士的断刃」统一改名为「鬼武士的动力炉」，描述与黑游侠的「黑游侠的核心部件」对齐；旧存档读档时自动迁移补 tag。
- **动画帧修正**：弃用（跳过而非删除）变量、机凯种、义军 rebel 若干有抠图/白块瑕疵的动画帧，并让地图与战斗动图同步使用同一批帧。

## 本次更新（2026-08-15）

### 管道噩梦 3-1 新增敌人
- 🤖 **废弃机器人MK2**：3-1 的加强版废弃机体（16 帧全用），两个技能组交替——「废料传送带」（三条虚线轨道，红心上下切轨躲避废料）与「重力摆锤」（单摆，左右键施力矩起摆），BGM 复用「地狱王子」1.5 倍速。
- 🛸 **UFO**：3-1 偏右上角飞行器，原地悬浮（16 帧动画）。技能「牵引光束」：战斗框三等分，红心落入重力列时被持续向上吸（下键对抗）。

### 管道噩梦 3-2 新 BOSS：双生舞怜
- 🩰 **双生舞怜**：深层管道的旧人偶，**双阶段战斗**。一阶段血量打空后进入二阶段（二阶段血量重置为 75%），BGM 分阶段切 `angela_phase1` / `angela_phase2`。
- **一阶段三技能循环**：①机枢舞者（左右两只颅像对角线冲刺）②田字格追逐（两只头像沿田字格虚线移动，一追一游荡）③苏联国徽单摆（红心挂单摆，轨道冲刺舞者穿场）。
- **二阶段技能重设计**：
  - ①机枢舞者 → **黄金分割递归切割**：每刀沿切割线冲刺留下发光红激光，玩家所在侧收缩成更小活动区，逐步逼到最后一息空间。
  - ②田字格追逐 → 只剩一只追击者、速度 ×1.5，**走过路径燃烧**（变红），踩上每秒扣 1 血；转角僵直 0.1s 给玩家拉开距离。
  - ③苏联国徽单摆 → 中心圆形**重力域**覆盖整条单摆，周期性重力脉冲（期间重力 ×4、玩家力矩被压制）；轨道冲刺舞者只剩一只、速度 +20%、每次冲刺横/竖轨迹交替。
- 🎭 **锁血演出回合**：二阶段濒死时锁血为 1 滴血，只剩一只舞者用**减半速度**的斜线冲刺做最后挣扎（寓意虚弱），一轮后玩家补刀击杀。
- 🏆 **击败奖励**：掉落「双生舞怜的动力炉」（`boss_trophy`，可进解析系统）+ 50 经验；标记为 boss，**击败后不再刷新**。

### 修复
- 🐛 二阶段田字格追逐「红线不扣血」：燃烧 DoT 判定从「按移动中的当前边」改为「红心实际坐标对每条燃烧边做点→线段距离」，站着/走着都结算。
- ⏱ 二阶段转角僵直 0.25s → 0.1s。

### 新道具
- 🧪 **纳米修复液(小)**：战斗中使用的持续回血消耗品——使用后**每回合回复 5 点生命值，持续 3 回合**（敌方回合结束回到菜单时结算）。放置两枚：`base_4`（义军士兵所在基地深层）一枚、`pipe_nightmare_3_1`（管道噩梦 3-1 左侧）一枚。
- 📡 **归航信标**：关键道具（`key_item`，**无限使用**），在地图上按 `T` 打开传送菜单，传到任意已激活的篝火。放置一枚：`base_1`（基地 1-1）右下。
- 🔥 **紧急保险丝**：关键道具（被动），濒死时**自动熔断锁血一次**——HP 归零改为保住 1 点生命并消耗该道具。放置一枚：`pipe_nightmare_1`（两个变量的房间）中间偏左。

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
