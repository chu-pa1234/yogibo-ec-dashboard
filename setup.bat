@echo off
chcp 65001 > nul

if exist "%~dp0scripts\download_server.py" (
    set REPO=%~dp0
    git -C "%REPO%" pull
    python "%REPO%scripts\download_server.py"
    goto :end
)

set DEST=%USERPROFILE%\Downloads\yogibo-ec-dashboard

if exist "%DEST%\.git" (
    git -C "%DEST%" pull
) else (
    git clone https://github.com/chu-pa1234/yogibo-ec-dashboard.git "%DEST%"
)

if %ERRORLEVEL% neq 0 (
    echo git error
    pause
    exit /b 1
)

python "%DEST%\scripts\download_server.py"

:end
pause
