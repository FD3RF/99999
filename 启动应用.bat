@echo off
chcp 65001 >nul
title ETHUSDT 量化交易系统
color 0A

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║       ETHUSDT 量化交易系统 - 启动中              ║
echo ╚══════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/3] 检查端口...
netstat -ano | findstr :8501 >nul
if not errorlevel 1 (
    echo 发现端口占用，正在停止旧进程...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501 ^| findstr LISTENING') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)
echo ✅ 端口准备就绪

echo.
echo [2/3] 启动应用...
echo.
echo 📊 数据源: CoinEx 企业级
echo 🤖 AI 模型: DeepSeek-R1 1.5B (快速)
echo 🔄 刷新间隔: 10秒
echo.
echo 访问地址: http://localhost:8501
echo.
echo ══════════════════════════════════════════════════
echo.

echo [3/3] 打开浏览器...
start http://localhost:8501

python -m streamlit run app_coinex.py --server.headless=true --server.port=8501

pause
