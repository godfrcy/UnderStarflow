import PyInstaller.__main__
import os

# 收集所有资源文件（assetsDB 目录）
root_dir = os.path.dirname(os.path.abspath(__file__))
assets_dir = os.path.join(root_dir, 'assetsDB')

# 资源文件夹列表
assets_folders = [
    'audio',
    'characters',
    'items',
    'maps',
    'objects',
    'ui',
]

add_data_args = []

# 添加 assetsDB 整体目录
if os.path.exists(assets_dir):
    add_data_args.append(f'--add-data={assets_dir}{os.pathsep}assetsDB')

# 添加根目录下的其他资源文件
root_files = ['icon.ico']
for f in root_files:
    path = os.path.join(root_dir, f)
    if os.path.exists(path):
        add_data_args.append(f'--add-data={path}{os.pathsep}.')

args = [
    'main.py',
    '--name=UnderStarflow',
    '--onefile',
    '--windowed',
    '--noconfirm',
    '--clean',
]

# 如果有图标，添加图标参数
icon_path = os.path.join(assets_dir, 'ui', 'icon.ico')
if os.path.exists(icon_path):
    args.append(f'--icon={icon_path}')

args.extend(add_data_args)

print("Running PyInstaller...")
print(f"Args: {args}")
PyInstaller.__main__.run(args)
