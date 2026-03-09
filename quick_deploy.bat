@echo off
chcp 65001 >nul
echo ========================================
echo ETHUSDT 量化系统 - 云服务器部署助手
echo ========================================
echo.

echo 此脚本将帮助你部署应用到云服务器
echo.
echo 前置要求：
echo 1. 已购买腾讯云 Lighthouse 服务器
echo 2. 已记录服务器公网 IP
echo 3. 已记录服务器登录密码
echo.

pause

echo.
echo [步骤 1/5] 获取服务器信息
echo.
set /p SERVER_IP="请输入服务器公网 IP: "
set /p SERVER_USER="请输入登录用户名 (默认 root): "
if "%SERVER_USER%"=="" set SERVER_USER=root

echo.
echo [步骤 2/5] 测试服务器连接
echo.
echo 正在测试连接到 %SERVER_IP%...
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo 连接成功" 2>nul
if errorlevel 1 (
    echo.
    echo ❌ 无法连接到服务器
    echo 请检查：
    echo 1. 服务器 IP 是否正确
    echo 2. 服务器是否已启动
    echo 3. 安全组是否开放 22 端口
    pause
    exit /b 1
)

echo ✅ 服务器连接正常

echo.
echo [步骤 3/5] 上传项目文件
echo.
echo 正在上传文件到服务器...
scp -r "%~dp0*" %SERVER_USER%@%SERVER_IP%:/tmp/ethusdt-trading/
if errorlevel 1 (
    echo ❌ 文件上传失败
    pause
    exit /b 1
)
echo ✅ 文件上传完成

echo.
echo [步骤 4/5] 配置 API Key
echo.
set /p API_ID="请输入 CoinEx Access ID: "
set /p API_KEY="请输入 CoinEx Secret Key: "

echo 正在配置...
ssh %SERVER_USER%@%SERVER_IP% "cat > /tmp/ethusdt-trading/.env << EOF
COINEX_ACCESS_ID=%API_ID%
COINEX_SECRET_KEY=%API_KEY%
TZ=Asia/Shanghai
EOF"
echo ✅ API Key 配置完成

echo.
echo [步骤 5/5] 执行部署脚本
echo.
echo 正在部署应用...
ssh %SERVER_USER%@%SERVER_IP% "cd /tmp/ethusdt-trading && chmod +x deploy_to_cloud.sh && ./deploy_to_cloud.sh"

echo.
echo ========================================
echo ✅ 部署完成！
echo ========================================
echo.
echo 访问地址: http://%SERVER_IP%:8501
echo.
echo 注意：请确保服务器安全组已开放 8501 端口
echo.
pause
