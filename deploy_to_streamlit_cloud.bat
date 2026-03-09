@echo off
chcp 65001 >nul
echo ========================================
echo Streamlit Community Cloud 一键部署
echo ========================================
echo.

echo 此脚本将帮助你部署到 Streamlit Cloud（完全免费）
echo.
echo 前置要求：
echo 1. 已有 GitHub 账号
echo 2. 已创建 GitHub 仓库（Public）
echo 3. 已安装 Git
echo.

pause

echo.
echo [步骤 1/5] 检查 Git 仓库
echo.
cd /d "%~dp0"
git status >nul 2>&1
if errorlevel 1 (
    echo 初始化 Git 仓库...
    git init
    git add .
    git commit -m "Initial commit"
)

echo ✅ Git 仓库就绪

echo.
echo [步骤 2/5] 配置 GitHub 远程仓库
echo.
git remote -v | findstr origin >nul
if errorlevel 1 (
    echo 需要配置 GitHub 仓库
    echo.
    echo 请先在 GitHub 创建仓库：
    echo 1. 访问 https://github.com/new
    echo 2. 仓库名：ethusdt-quantitative-system
    echo 3. 设为 Public（必须公开）
    echo 4. 不要勾选 "Initialize with README"
    echo.
    set /p GITHUB_USER="请输入你的 GitHub 用户名: "
    git remote add origin https://github.com/%GITHUB_USER%/ethusdt-quantitative-system.git
    echo ✅ 远程仓库已配置
) else (
    echo ✅ 远程仓库已存在
)

echo.
echo [步骤 3/5] 推送代码到 GitHub
echo.
echo 正在推送...
git push -u origin master
if errorlevel 1 (
    echo.
    echo ❌ 推送失败
    echo 可能原因：
    echo 1. GitHub 仓库不存在
    echo 2. 需要登录 GitHub（运行 git config --global user.name 和 user.email）
    echo 3. 网络连接问题
    pause
    exit /b 1
)
echo ✅ 代码推送成功

echo.
echo [步骤 4/5] 配置 API Key
echo.
echo 请在 Streamlit Cloud 中配置 Secrets：
echo 1. 访问 https://share.streamlit.io/
echo 2. 登录并选择你的应用
echo 3. Settings ^> Secrets
echo 4. 添加：
echo    COINEX_ACCESS_ID = "ck_ffiiw9tghpmo"
echo    COINEX_SECRET_KEY = "your_secret_key"
echo.

echo.
echo [步骤 5/5] 部署到 Streamlit Cloud
echo.
echo 请按以下步骤操作：
echo.
echo 1. 打开浏览器访问：https://share.streamlit.io/
echo 2. 点击 "Sign in with GitHub"
echo 3. 授权 Streamlit 访问 GitHub
echo 4. 点击 "New app"
echo 5. 填写信息：
echo    - Repository: 你的用户名/ethusdt-quantitative-system
echo    - Branch: master
echo    - Main file path: app_coinex.py
echo 6. 点击 "Deploy!"
echo.
echo 等待 2-3 分钟部署完成
echo.

echo ========================================
echo ✅ 本地配置完成！
echo ========================================
echo.
echo 访问地址将是：
echo https://ethusdt-quantitative-system-你的用户名.streamlit.app
echo.
echo 注意事项：
echo - 首次部署需要等待 2-3 分钟
echo - 记得在 Streamlit Cloud 中配置 API Key
echo - AI 功能需要使用在线 API（如 DeepSeek）
echo.
echo 详细说明请查看：STREAMLIT_CLOUD_DEPLOY.md
echo.
pause
