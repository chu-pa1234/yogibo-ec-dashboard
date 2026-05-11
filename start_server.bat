@echo off
set REPO=%~dp0
git -C "%REPO%" pull
"C:\Users\d.nakamura\OneDrive - Š”®‰ïĞ Yogibo\ƒhƒLƒ…ƒƒ“ƒg\claude\.venv\Scripts\python.exe" "%REPO%scripts\download_server.py"
pause
