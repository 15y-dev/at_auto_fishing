@echo off
REM 文字コードを UTF-8 に切り替える(このファイルは UTF-8 で保存されているため)
chcp 65001 >nul

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
rem set_resolution.py と同じフォルダに置く。
cd /d "%~dp0"

rem 現在のセッションIDを取得する(日本語/英語版Windows問わず確実に取得)
set "SESSION_ID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-Process -Id $PID).SessionId"`) do set "SESSION_ID=%%i"

if not defined SESSION_ID (
    echo セッションIDの取得に失敗しました。
    pause
    exit /b 1
)

echo 現在のセッションID: %SESSION_ID% をコンソールに切り替えます...
%windir%\System32\tscon.exe %SESSION_ID% /dest:console

rem コンソール(ダミープラグ)に切り替わるのを待つ
timeout /t 3 /nobreak >nul

rem python が PATH に無い場合はフルパスに書き換える
py "%~dp0set_resolution.py"