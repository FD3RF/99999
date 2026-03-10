@echo off
chcp 65001 >nul
title 自动部署到 Streamlit Cloud
color 0A

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║     ETHUSDT 量化系统 - 全自动云部署                   ║
echo ║     平台: Streamlit Community Cloud (完全免费)        ║
echo ╚══════════════════════════════════════════════════════╝
echo.
echo 📋 部署流程说明：
echo.
echo ✅ 步骤 1: 配置 GitHub 仓库
echo ✅ 步骤 2: 推送代码到 GitHub
echo ✅ 步骤 3: 连接 Streamlit Cloud
echo ✅ 步骤 4: 自动部署应用
echo ✅ 步骤 5: 配置 API Key
echo.
echo ⏱️  预计时间: 3-5 分钟
echo.

pause

cd /d "%~dp0"

:: 步骤 1: 配置 GitHub
echo.
echo ┌──────────────────────────────────────────────────────┐
echo │ [步骤 1/5] 配置 GitHub 仓库                          │
echo └──────────────────────────────────────────────────────┘
echo.

git remote -v | findstr origin >nul
if errorlevel 1 (
    echo ⚠️  未检测到远程仓库配置
    echo.
    echo 请按以下步骤操作（需要 1 分钟）：
    echo.
    echo 1️⃣  打开浏览器访问: https://github.com/new
    echo.
    echo 2️⃣  填写仓库信息：
    echo     ├─ Repository name: ethusdt-quantitative-system
    echo     ├─ Description: ETHUSDT 量化交易系统
    echo     ├─ 选择 Public (必须公开，Private 需付费)
    echo     └─ 不要勾选任何初始化选项
    echo.
    echo 3️⃣  点击 "Create repository"
    echo.
    
    start https://github.com/new
    
    echo.
    set /p GITHUB_USER="✅ 创建完成后，请输入你的 GitHub 用户名: "
    
    echo.
    echo 正在配置远程仓库...
    git remote add origin https://github.com/%GITHUB_USER%/ethusdt-quantitative-system.git
    echo ✅ 远程仓库配置完成
    
) else (
    echo ✅ 远程仓库已配置
    for /f "tokens=2 delims=/" %%a in ('git remote -v ^| findstr origin ^| findstr fetch') do set REPO_URL=%%a
    for /f "tokens=1 delims=." %%b in ("%REPO_URL%") do set GITHUB_USER=%%b
)

:: 步骤 2: 推送代码
echo.
echo ┌──────────────────────────────────────────────────────┐
echo │ [步骤 2/5] 推送代码到 GitHub                         │
echo └──────────────────────────────────────────────────────┘
echo.

echo 正在推送代码...
git branch -M master
git push -u origin master --force

if errorlevel 1 (
    echo.
    echo ❌ 推送失败！
    echo.
    echo 可能的原因：
    echo 1. GitHub 仓库不存在 - 请确保已在 GitHub 创建仓库
    echo 2. 需要登录 - 运行 git config 配置用户信息
    echo 3. 网络问题 - 检查网络连接
    echo.
    pause
    exit /b 1
)

echo ✅ 代码推送成功

:: 步骤 3: 连接 Streamlit Cloud
echo.
echo ┌──────────────────────────────────────────────────────┐
echo │ [步骤 3/5] 连接 Streamlit Cloud                      │
echo └──────────────────────────────────────────────────────┘
echo.

echo 正在打开 Streamlit Cloud...
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

:: 步骤 4: 部署应用
echo.
echo ┌──────────────────────────────────────────────────────┐
echo │ [步骤 4/5] 部署应用                                  │
echo └──────────────────────────────────────────────────────┘
echo.

echo 请在 Streamlit Cloud 中填写：
echo.
echo ├─ Repository: 选择 ethusdt-quantitative-system
echo ├─ Branch: master
echo └─ Main file path: app_coinex.py
echo.
echo 然后点击 "Deploy!" 按钮
echo.
echo ⏳ 等待 2-3 分钟完成部署...
echo.

:: 步骤 5: 配置 API Key
echo.
echo ┌──────────────────────────────────────────────────────┐
echo │ [步骤 5/5] 配置 API Key                              │
echo └──────────────────────────────────────────────────────┘
echo.

echo 部署成功后，需要配置 API Key：
echo.
echo 1️⃣  在 Streamlit Cloud 应用页面
echo.
echo 2️⃣  点击右上角 "Settings" → "Secrets"
echo.
echo 3️⃣  点击 "Edit secrets"
echo.
echo 4️⃣  粘贴以下内容：
echo.
echo ┌────────────────────────────────────────────────────┐
echo │ COINEX_ACCESS_ID = "ck_ffiiw9tghpmo"              │
echo │ COINEX_SECRET_KEY = "your_secret_key_here"        │
echo │                                                    │
echo │ # 可选：启用 AI 功能                               │
echo │ DEEPSEEK_API_KEY = "your_deepseek_api_key"        │
echo └────────────────────────────────────────────────────┘
echo.
echo 5️⃣  点击 "Save"
echo.
echo 6️⃣  应用将自动重启
echo.

echo ╔══════════════════════════════════════════════════════╗
echo ║              ✅ 部署流程完成！                        ║
echo ╚══════════════════════════════════════════════════════╝
echo.

if defined GITHUB_USER (
    echo 🌐 你的应用地址：
    echo https://ethusdt-quantitative-system-%GITHUB_USER%.streamlit.app
    echo.
)

echo 📋 重要提示：
echo.
echo ✅ 应用已部署到云端，可全球访问
echo ✅ 自动分配 HTTPS 域名
echo ✅ 推送代码到 GitHub 会自动更新
echo ✅ 完全免费，无需信用卡
echo.

echo 💡 下次更新代码后，只需运行：
echo    git add .
echo    git commit -m "更新说明"
echo    git push
echo.

echo 🎉 现在可以在浏览器中访问你的应用了！
echo.

pause
