import PyInstaller.__main__
import os
import shutil

# Clean up previous builds
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

print("Starting build process...")

PyInstaller.__main__.run([
    'main.py',
    '--name=UnderStarflow',
    '--onedir',
    '--windowed',
    '--noconfirm',
    '--clean',
    '--icon=assetsDB/icon.ico',
    '--add-data=assetsDB;assetsDB',
    # Hidden imports if needed (e.g. pygame is usually auto-detected)
])

print("Build complete. Check 'dist/UnderStarflow' folder.")
