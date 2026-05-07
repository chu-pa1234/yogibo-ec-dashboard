@echo off
chcp 65001 > nul
echo ================================
echo  Yogibo EC ダウンロードサーバー
echo ================================
echo.
echo サーバーを起動しています...
echo.
start "" "http://localhost:8765"
"C:\Users\d.nakamura\OneDrive - 株式会社 Yogibo\ドキュメント\claude\.venv\Scripts\python.exe" "%~dp0scripts\download_server.py"
pause
