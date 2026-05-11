@echo off
chcp 65001 > nul

if exist "%~dp0scripts\download_server.py" (
    set REPO=%~dp0
    git -C "%REPO%" pull
    if not exist "%REPO%scripts\user_config.py" (
        copy "%REPO%scripts\user_config.example.py" "%REPO%scripts\user_config.py" > nul
    )
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

if not exist "%DEST%\scripts\user_config.py" (
    copy "%DEST%\scripts\user_config.example.py" "%DEST%\scripts\user_config.py" > nul
)

python "%DEST%\scripts\download_server.py"

:end
pause
