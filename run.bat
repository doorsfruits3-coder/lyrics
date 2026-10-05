@echo off
chcp 65001 >nul
title Discord Lyric Status Sync - Web Dashboard
echo ========================================================
echo   🎵 KHOI DONG DISCORD LYRIC STATUS SYNC TOOL (WEB UI) 🎵
echo ========================================================
echo.
echo Dang kiem tra moi truong Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python! Vui long cai dat Python 3.9 tro len va tick 'Add to PATH'.
    pause
    exit /b
)

echo Dang khoi dong may chu Web Dashboard...
python app.py
pause
