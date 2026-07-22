import PyInstaller.__main__
import os

# 收集所有资源文件
added_files = [
    ('assets', 'assets'),
    ('jikaizhong_grid', 'jikaizhong_grid'),
    ('variable_grid', 'variable_grid'),
    ('瓦片地图01_grid', '瓦片地图01_grid'),
    ('雪地grid', '雪地grid'),
    ('fire_grid', 'fire_grid'),
    ('newsoldier_grid', 'newsoldier_grid'),
    ('d2f465025b3f4f51b50c4811786d39ca_grid', 'd2f465025b3f4f51b50c4811786d39ca_grid'),
]

# 添加根目录下的特定文件
root_files = [
    'attack_success.wav',
    'city ruins.mp3',
    'jikaizhong.mp3',
    'monster_song.mp3',
    'sound.MP3',
    'the tree.mp3',
    'mechanical_heart.jpeg',
    'startgame.jpg',
    'tile01.jpg',
    'anthe_back.png',
    'anthe_forward.png',
    'anthe_forward_2.png',
    'anthe_forward_walk.png',
    'anthe_front.png',
    'anthe_front_walk.png',
    'anthe_sheet.png',
    'jikaizhong.png',
    'variable.gif',
    'icon.ico'
]

for f in root_files:
    if os.path.exists(f):
        added_files.append((f, '.'))

# 构建 add-data 参数
add_data_args = []
for src, dst in added_files:
    # Windows separator is ;
    add_data_args.append(f'--add-data={src}{os.pathsep}{dst}')

args = [
    'main.py',
    '--name=UnderStarflow',
    '--onefile',
    '--windowed',
    '--noconfirm',
    '--clean',
] 

if os.path.exists('icon.ico'):
    args.append('--icon=icon.ico')

args.extend(add_data_args)

print("Running PyInstaller...")
PyInstaller.__main__.run(args)
