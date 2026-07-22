# 更新日志

## [0.2.0] - 2026-07-23

### 项目整理
- 🧹 删除 12 个无用 zip 压缩包
- 🗑️ 删除遗留 `maps/` 目录（已迁移到 `assetsDB/maps/`）
- 🗑️ 删除一次性脚本 `organize_assets.py`、`verify_ghost.py`
- 📁 30+ 个散落在 `assetsDB/` 根目录的文件归类到 `characters/`、`objects/`、`ui/` 子目录
- 🏷️ 所有中文目录重命名为英文（`失败之作` → `failure_boss`、`废弃机器人` → `abandoned_robot` 等）
- 🎵 音频文件标准化命名（去空格、去中文、统一小写）
- 🔧 更新所有代码中的资源路径引用

## [0.1.0] - 2026-07-23

### 新增
- 初始化项目，提交初始版本代码
- 添加 `README.md` 项目说明文档
- 添加 `CHANGELOG.md` 更新日志

### 基础设施
- 配置 Git 远程仓库：https://github.com/godfrcy/UnderStarflow
- 配置 SSH Key 完成 GitHub 认证
- 首次推送，项目正式开源

## [0.0.1] - 初始版本

- 🎮 Pygame 2D 俯视角弹幕躲避 RPG
- 瓦片地图系统（雪地/基地/管道噩梦）
- 实时弹幕战斗系统（普通/激光/方块/等离子刃/激光网络）
- 魂系篝火存档机制
- 完整 UI 系统（标题/暂停/篝火/传送/背包菜单）
- 对话系统与多种特效
- PyInstaller 打包支持
