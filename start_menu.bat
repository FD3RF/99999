@echo off
chcp 65001 >nul
echo ========================================
echo   ETHUSDT 量化系统启动器
echo ========================================
echo.
echo 请选择启动方式：
echo.
echo [1] 直接启动（无代理）
echo [2] 配置代理启动（输入代理地址）
echo [3] 使用默认代理（127.0.0.1:7890）
echo [4] 测试网络连接
echo [5] 退出
echo.
set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" goto direct
if "%choice%"=="2" goto custom_proxy
if "%choice%"=="3" goto default_proxy
if "%choice%"=="4" goto test
if "%choice%"=="5" exit

:direct
echo.
echo 正在直接启动...
python -m streamlit run app_v3.py
exit

:custom_proxy
echo.
set /p proxy_addr="请输入代理地址（如 http://127.0.0.1:7890）: "
echo.
echo 正在配置代理: %proxy_addr%
set HTTP_PROXY=%proxy_addr%
set HTTPS_PROXY=%proxy_addr%
python -m streamlit run app_v3.py
exit

:default_proxy
echo.
echo 正在使用默认代理: http://127.0.0.1:7890
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
python -m streamlit run app_v3.py
exit

:test
echo.
echo 正在测试网络连接...
python test_apis_simple.py
echo.
pause
exit
