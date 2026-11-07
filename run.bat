@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/2] 运行数据流水线...
python src\pipeline.py
if errorlevel 1 goto :err

echo [2/2] 打开看板...
start "" "dashboard\index.html"
echo 完成。
timeout /t 2 >nul
exit /b 0

:err
echo.
echo 运行失败。如果提示缺少 pandas，请先执行：
echo     pip install -r requirements.txt
echo.
pause
exit /b 1
