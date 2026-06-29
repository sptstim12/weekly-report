@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ================================================
echo   定投周报 — 一键刷新
echo ================================================
echo.

python weekly_report.py --no-recommend

if %errorlevel% equ 0 (
    echo.
    echo 报告已生成，正在打开...
    start "" "%~dp0output\index.html"
) else (
    echo.
    echo [错误] 脚本运行失败，请检查上面的错误信息
)
pause
