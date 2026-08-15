#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sprite_split.py — 把一张 NxM 的 spritesheet 均分切成命名帧 PNG。

设计动机：AI 生成的角色行走动画常常是一张 spritesheet（如 4x4 = 16 帧），
而游戏引擎（OverworldEnemy / battle_system）按 `{前缀}_{row}_{col}.png` 逐帧加载。
这个脚本把 spritesheet 切回逐帧 PNG，覆盖输出目录下同名帧，方便替换/复用。

用法：
    python sprite_split.py <spritesheet.png> <输出目录> <前缀> [行数] [列数] [--colorkey R,G,B]

示例（rebel_soldier 4x4 行走动画，替换掉同目录下 16 帧）：
    python sprite_split.py "assetsDB/characters/enemies/rebel_soldier/8d2f4b1b94e647c1a7058ce9995ad3fd.png" \
        "assetsDB/characters/enemies/rebel_soldier" rebel_soldier 4 4

    # 若 spritesheet 是带纯色底（如白底）还没抠图，用 --colorkey 去掉：
    python sprite_split.py sheet.png out_dir 前缀 4 4 --colorkey 255,255,255

命名：{前缀}_{row}_{col}.png，row/col 从 1 开始（与引擎 is_grid 加载顺序一致）。
"""

import os
import sys
import argparse
import pygame


def split_sheet(sheet_path, out_dir, prefix, rows=4, cols=4, colorkey=None):
    pygame.init()
    pygame.display.set_mode((1, 1))  # 供 convert_alpha 使用

    sheet = pygame.image.load(sheet_path).convert_alpha()
    sw, sh = sheet.get_size()

    if sw % cols != 0 or sh % rows != 0:
        print(f"[警告] spritesheet 尺寸 {sw}x{sh} 无法被 {cols}x{rows} 整除，右侧/下侧余数会被忽略。")

    cw = sw // cols
    ch = sh // rows
    os.makedirs(out_dir, exist_ok=True)

    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            x = (c - 1) * cw
            y = (r - 1) * ch
            frame = sheet.subsurface((x, y, cw, ch)).copy()

            if colorkey:
                frame.set_colorkey(tuple(colorkey))
                frame = frame.convert_alpha()  # 把 colorkey 颜色转成真正的透明

            out_path = os.path.join(out_dir, f"{prefix}_{r}_{c}.png")
            pygame.image.save(frame, out_path)

    print(f"完成：{sheet_path} ({sw}x{sh}) → {rows}x{cols}={rows * cols} 帧，"
          f"输出到 {out_dir}/（前缀 {prefix}，每帧 {cw}x{ch}）")


def main():
    ap = argparse.ArgumentParser(description="spritesheet 均分切帧")
    ap.add_argument("sheet", help="spritesheet 路径")
    ap.add_argument("out_dir", help="输出目录")
    ap.add_argument("prefix", help="输出文件名前缀")
    ap.add_argument("rows", nargs="?", type=int, default=4)
    ap.add_argument("cols", nargs="?", type=int, default=4)
    ap.add_argument("--colorkey", help="去掉纯色底，如 255,255,255", default=None)
    args = ap.parse_args()

    colorkey = None
    if args.colorkey:
        colorkey = [int(v) for v in args.colorkey.split(",")]
        if len(colorkey) != 3:
            sys.exit("[错误] --colorkey 需要 R,G,B 三个值")

    split_sheet(args.sheet, args.out_dir, args.prefix, args.rows, args.cols, colorkey)


if __name__ == "__main__":
    main()
