@echo off
rem 管理者として実行すること。set_resolution.py と同じフォルダに置く。

for /f "skip=1 tokens=3" %%s in ('query user %USERNAME%') do (
    %windir%\System32\tscon.exe %%s /dest:console
)

rem コンソール(ダミープラグ)に切り替わるのを待つ
timeout /t 3 /nobreak >nul

rem python が PATH に無い場合はフルパスに書き換える
py "%~dp0set_resolution.py"
