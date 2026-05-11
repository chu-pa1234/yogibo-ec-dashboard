@echo off
chcp 65001 > nul
echo ================================
echo  Yogibo EC ダウンロードサーバー
echo ================================
echo.
echo サーバーを起動しています...
echo.
python "%~dp0scripts\download_server.py"
pause
