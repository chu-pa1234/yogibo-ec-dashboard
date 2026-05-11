@echo off
chcp 65001 > nul

set REPO=%~dp0
git -C "%REPO%" pull
echo.
python "%REPO%scripts\download_server.py"
pause
