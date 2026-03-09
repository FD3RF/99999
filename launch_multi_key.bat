@echo off
chcp 65001 >nul
cls
echo ========================================
echo   ETHUSDT 企业级系统 - 多 Key 负载均衡
echo ========================================
echo.

echo [配置信息]
echo  API-1: ck_ffiiw9tghpmo (优先级1)
echo  API-2: edb9c210... (优先级2)
echo  模式: 轮询负载均衡 + 故障转移
echo.

echo [启动步骤]
echo  1. 检查 Ollama...
tasklist | findstr /I "ollama" >nul
if errorlevel 1 (
    echo     启动 Ollama...
    start /B ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo     Ollama 已运行
)

echo  2. 启动应用...
echo.
echo  访问地址: http://localhost:8501
echo  特性: 双 API Key 负载均衡
echo  AI模型: DeepSeek-R1:1.5B
echo.
echo  按 Ctrl+C 停止
echo ========================================
echo.

streamlit run app_multi_key.py --server.headless=true
