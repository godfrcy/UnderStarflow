
import pygame
import os

try:
    pygame.init()
    path = r"d:\UnderStarflow\assetsDB\义军女1\c4502f3ac15a46aea1d3e088e3375afd_2_1.png"
    if os.path.exists(path):
        img = pygame.image.load(path)
        print(f"Size: {img.get_width()}x{img.get_height()}")
    else:
        print("File not found")
except Exception as e:
    print(f"Error: {e}")
