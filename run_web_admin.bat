@echo off
REM 管理者権限チェックと昇格
REM Check and elevate to administrator privileges

net session >nul 2>&1
if %errorLevel% == 0 (
    REM 既に管理者権限で実行中
    goto :run_program
) else (
    REM 管理者権限で再起動
    echo 管理者権限で再起動しています...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:run_program
REM ここから実際のプログラム実行
cd /d "%~dp0"

echo ========================================
echo Webゲームコントローラーサーバー起動
echo (管理者権限)
echo ========================================
echo.

REM 仮想環境を有効化
echo [1/2] 仮想環境を有効化中...
call .venv\Scripts\activate.bat

REM Pythonプログラムを実行
echo [2/2] プログラムを起動中...
echo.
python web_gamepad_server.py

REM プログラム終了後、キー入力待ち
echo.
echo ========================================
echo プログラムが終了しました
echo ========================================
pause
