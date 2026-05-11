@echo off
chcp 65001 > nul
echo ================================
echo  Yogibo EC ダッシュボード セットアップ
echo ================================
echo.

:: リポジトリ内から起動された場合は直接サーバー起動
if exist "%~dp0scripts\download_server.py" (
    echo サーバーを起動します...
    python "%~dp0scripts\download_server.py"
    goto :end
)

:: 初回セットアップ: ダウンロードフォルダにクローン
set DEST=%USERPROFILE%\Downloads\yogibo-ec-dashboard

echo 初回セットアップを開始します...
echo クローン先: %DEST%
echo.

if exist "%DEST%\.git" (
    echo リポジトリが見つかりました。最新版に更新します...
    git -C "%DEST%" pull
) else (
    echo リポジトリをクローンしています...
    git clone https://github.com/chu-pa1234/yogibo-ec-dashboard.git "%DEST%"
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo エラーが発生しました。git がインストール済みか確認してください。
    pause
    exit /b 1
)

echo.
echo 完了！サーバーを起動します...
python "%DEST%\scripts\download_server.py"

:end
pause
