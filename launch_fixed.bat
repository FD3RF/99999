@echo off
chcp 65001 >nul
cls
echo ========================================
echo   ETHUSDT 量化系统 - 启动修复版
echo ========================================
echo.

echo [1/3] 停止旧进程...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *streamlit*" 2>nul
timeout /t 2 /nobreak >nul

echo [2/3] 清除缓存...
if exist __pycache__ rd /s /q __pycache__
if exist .streamlit\cache rd /s /q .streamlit\cache 2>nul

echo [3/3] 启动修复版应用...
echo.
echo 正在启动... 请稍候
echo 浏览器将自动打开 http://localhost:8501
echo.
echo 按 Ctrl+C 可停止应用
echo ========================================
echo.

python -m streamlit run app_fixed.py --server.headless=true
