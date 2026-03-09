@echo off
chcp 65001 >nul
title ETHUSDT 量化系统 - 免费云部署
color 0A

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   ETHUSDT 量化系统 - 一键免费云部署              ║
echo ║   平台: Streamlit Community Cloud (完全免费)     ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo 📋 部署方案说明：
echo.
echo ✅ 完全免费 - 无需信用卡，无时间限制
echo ✅ 自动部署 - 连接 GitHub 自动更新
echo ✅ HTTPS 域名 - 自动分配 SSL 证书
echo ✅ Python 环境 - 完整支持 Streamlit
echo ✅ 全球加速 - CDN 加速访问
echo.
echo ⏱️  预计部署时间：5-10 分钟
echo.

pause

:: 步骤 1
echo.
echo ┌──────────────────────────────────────────────────┐
echo │ [步骤 1/6] 检查项目文件                          │
echo └──────────────────────────────────────────────────┘
cd /d "%~dp0"

if exist "app_coinex.py" (
    echo ✅ 主程序文件存在
) else (
    echo ❌ 错误：找不到 app_coinex.py
    pause
    exit /b 1
)

if exist "requirements.txt" (
    echo ✅ 依赖文件存在
) else (
    echo ❌ 错误：找不到 requirements.txt
    pause
    exit /b 1
)

echo ✅ 项目文件检查通过

:: 步骤 2
echo.
echo ┌──────────────────────────────────────────────────┐
echo │ [步骤 2/6] 准备 Git 仓库                         │
echo └──────────────────────────────────────────────────┘

git status >nul 2>&1
if errorlevel 1 (
    echo 正在初始化 Git 仓库...
    git init
    git config user.email "trader@example.com"
    git config user.name "Trader"
    git add .
    git commit -m "Initial commit: ETHUSDT quantitative trading system"
    echo ✅ Git 仓库初始化完成
) else (
    echo ✅ Git 仓库已存在
    git add . 2>nul
    git diff --cached --quiet
    if errorlevel 1 (
        echo 发现新文件，正在提交...
        git commit -m "Update project files"
        echo ✅ 文件已提交
    )
)

:: 步骤 3
echo.
echo ┌──────────────────────────────────────────────────┐
echo │ [步骤 3/6] 配置 GitHub 仓库                      │
echo └──────────────────────────────────────────────────┘

git remote -v | findstr origin >nul
if errorlevel 1 (
    echo.
    echo ⚠️  需要配置 GitHub 仓库
    echo.
    echo 请按以下步骤操作：
    echo.
    echo 1. 打开浏览器访问：https://github.com/new
    echo 2. 登录你的 GitHub 账号
    echo 3. 填写仓库信息：
    echo    - Repository name: ethusdt-quantitative-system
    echo    - Description: ETHUSDT 量化交易系统
    echo    - 选择 Public（必须公开，Private 需付费）
    echo    - 不要勾选 "Add a README file"
    echo    - 不要选择 .gitignore 和 license
    echo 4. 点击 "Create repository"
    echo.
    pause
    
    echo.
    set /p GITHUB_USER="请输入你的 GitHub 用户名: "
    
    echo.
    echo 正在配置远程仓库...
    git remote add origin https://github.com/%GITHUB_USER%/ethusdt-quantitative-system.git
    echo ✅ 远程仓库配置完成
) else (
    echo ✅ 远程仓库已配置
)

:: 步骤 4
echo.
echo ┌──────────────────────────────────────────────────┐
echo │ [步骤 4/6] 推送代码到 GitHub                     │
echo └──────────────────────────────────────────────────┘

echo.
echo 正在推送代码...
git branch -M master
git push -u origin master

if errorlevel 1 (
    echo.
    echo ❌ 推送失败
    echo.
    echo 可能的原因和解决方案：
    echo.
    echo 1. 需要登录 GitHub
    echo    解决：运行以下命令
    echo    git config --global user.name "你的用户名"
    echo    git config --global user.email "你的邮箱"
    echo.
    echo 2. GitHub 仓库不存在
    echo    解决：确保已在 GitHub 创建仓库
    echo.
    echo 3. 网络连接问题
    echo    解决：检查网络连接或使用代理
    echo.
    pause
    exit /b 1
)

echo ✅ 代码推送成功

:: 步骤 5
echo.
echo ┌──────────────────────────────────────────────────┐
echo │ [步骤 5/6] 部署到 Streamlit Cloud                │
echo └──────────────────────────────────────────────────┘

echo.
echo 正在打开 Streamlit Cloud 部署页面...
echo.
timeout /t 2 /nobreak >nul
start https://share.streamlit.io/

echo.
echo 请按以下步骤操作：
echo.
echo 1️⃣  在打开的页面中，点击 "Sign in with GitHub"
echo.
echo 2️⃣  授权 Streamlit 访问你的 GitHub
echo.
echo 3️⃣  登录后，点击 "New app" 按钮
echo.
echo 4️⃣  填写应用信息：
echo     ├─ Repository: 选择 ethusdt-quantitative-system
echo     ├─ Branch: master
echo     └─ Main file path: app_coinex.py
echo.
echo 5️⃣  点击 "Deploy!" 按钮
echo.
echo 6️⃣  等待 2-3 分钟，应用将自动部署
echo.

:: 步骤 6
echo.
echo ┌──────────────────────────────────────────────────┐
echo │ [步骤 6/6] 配置 API Key                          │
echo └──────────────────────────────────────────────────┘

echo.
echo 部署成功后，需要配置 API Key：
echo.
echo 1️⃣  在 Streamlit Cloud 应用页面
echo.
echo 2️⃣  点击右上角 "Settings" ^> "Secrets"
echo.
echo 3️⃣  点击 "Edit secrets"
echo.
echo 4️⃣  粘贴以下内容：
echo.
echo ┌────────────────────────────────────────┐
echo │ COINEX_ACCESS_ID = "ck_ffiiw9tghpmo"  │
echo │ COINEX_SECRET_KEY = "your_key_here"   │
echo │                                        │
echo │ # 如果使用 AI，添加：                  │
echo │ DEEPSEEK_API_KEY = "your_deepseek_key"│
echo └────────────────────────────────────────┘
echo.
echo 5️⃣  点击 "Save"
echo.
echo 6️⃣  应用将自动重启并加载配置
echo.

echo ╔══════════════════════════════════════════════════╗
echo ║           ✅ 部署完成！                          ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo 🌐 访问地址：
echo https://ethusdt-quantitative-system-你的用户名.streamlit.app
echo.
echo 📚 相关文档：
echo ├─ STREAMLIT_CLOUD_DEPLOY.md - 详细部署指南
echo ├─ README.md - 项目文档
echo └─ DEPLOYMENT_SUMMARY.md - 部署总结
echo.
echo 💰 费用：完全免费！
echo ├─ Streamlit Cloud: ¥0
echo ├─ GitHub: ¥0
echo ├─ 域名: 免费子域名
echo └─ SSL 证书: 免费
echo.
echo 🎉 现在可以访问你的应用了！
echo.

:: 保存访问地址
git remote -v | findstr origin > temp.txt
for /f "tokens=2 delims=/" %%a in (temp.txt) do set REPO_URL=%%a
del temp.txt

echo 按任意键打开应用（部署完成后）...
pause >nul

:: 尝试打开应用（需要替换用户名）
for /f "tokens=2 delims=/" %%a in ('git remote -v ^| findstr origin') do (
    for /f "tokens=1 delims=." %%b in ("%%a") do (
        start https://ethusdt-quantitative-system-%%b.streamlit.app
    )
)
