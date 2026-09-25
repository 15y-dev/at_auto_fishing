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
rem set_resolution.py と同じフォルダに置く。
cd /d "%~dp0"

for /f "skip=1 tokens=3" %%s in ('query user %USERNAME%') do (
    %windir%\System32\tscon.exe %%s /dest:console
)

rem コンソール(ダミープラグ)に切り替わるのを待つ
timeout /t 3 /nobreak >nul

rem python が PATH に無い場合はフルパスに書き換える
py "%~dp0set_resolution.py"