@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 抖音直播弹幕点歌机
python main.py %*
pause
