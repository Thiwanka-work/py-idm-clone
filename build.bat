@echo off
echo Installing requirements and PyInstaller...
pip install pyinstaller yt-dlp imageio-ffmpeg flask flask-cors requests customtkinter

echo Building Easy Downloader...
cd app
python -m pyinstaller --noconfirm --onedir --windowed --icon "icon.ico" --name "EasyDownloader" --add-data "icon.ico;." --hidden-import "yt_dlp" --hidden-import "imageio_ffmpeg" "main.py"

echo Build complete!
cd ..
pause
