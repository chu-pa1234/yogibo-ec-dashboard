@echo off
chcp 65001 > nul
echo ================================
echo  Yogibo EC ダウンロードサーバー
echo ================================
echo.
echo 最新版に更新中...
git -C "%~dp0" pull
echo.
echo サーバーを起動しています...
python "%~dp0scripts\download_server.py"
pause
