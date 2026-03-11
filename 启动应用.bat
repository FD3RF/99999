@echo off
chcp 65001 >nul
title ETHUSDT 机构级量化巡航系统 V2.0
color 0A

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   ETHUSDT 机构级量化巡航系统 V2.0 - 启动中       ║
echo ╚══════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

REM 检查并清理端口
echo [1/3] 检查端口...
netstat -ano | findstr :8501 >nul 2>&1
if not errorlevel 1 (
    echo 发现端口占用，正在清理...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501 ^| findstr LISTENING') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)
echo ✅ 端口准备就绪

REM 检查Python
echo.
echo [2/3] 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查依赖
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt -q
)
echo ✅ 环境检查完成

REM 启动系统
echo.
echo [3/3] 启动 V2.0 系统...
echo.
echo ══════════════════════════════════════════════════
echo 🎯 V2.0 核心功能:
echo   • LSTM概率限制 85%% (防过拟合)
echo   • VWAP 机构成本 + CVD 订单流
echo   • EMA21/EMA200 + ATR 波动率
echo   • 主力吸筹检测 (准确度85%%)
echo   • 假突破识别 + 市场状态识别
echo   • 爆仓监控 + 语音播报
echo ══════════════════════════════════════════════════
echo.
echo 🌐 访问地址: http://localhost:8501
echo 🔄 刷新间隔: 5秒
echo.
echo ⚠️  如看到旧版本，请在浏览器中按 Ctrl+Shift+R
echo ══════════════════════════════════════════════════
echo.

REM 打开浏览器
start http://localhost:8501

REM 启动 Streamlit
python -m streamlit run app.py --server.headless=true --server.port=8501

pause
