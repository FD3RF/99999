@echo off
chcp 65001 >nul
cls
echo ========================================
echo   ETHUSDT 企业级量化系统 - CoinEx版
echo ========================================
echo.

echo [启动步骤]
echo 1. 检查 Ollama 服务...
tasklist | findstr /I "ollama" >nul
if errorlevel 1 (
    echo    - 启动 Ollama 服务...
    start /B ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo    - Ollama 已运行
)

echo 2. 启动 Streamlit 应用...
echo.
echo 访问地址: http://localhost:8501
echo 数据源: CoinEx (企业级优化)
echo AI模型: DeepSeek-R1:1.5B (快速响应)
echo.
echo 按 Ctrl+C 停止应用
echo ========================================
echo.

streamlit run app_coinex.py --server.headless=true
