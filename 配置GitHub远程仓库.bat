@echo off
chcp 65001 >nul
title 配置 GitHub 远程仓库
color 0A

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║       配置 GitHub 远程仓库                        ║
echo ╚══════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 检查是否已配置
git remote -v | findstr origin >nul
if not errorlevel 1 (
    echo ✅ 远程仓库已配置
    echo.
    git remote -v
    echo.
    pause
    exit /b 0
)

echo ⚠️  检测到尚未配置远程仓库
echo.
echo 请按以下步骤操作：
echo.
echo 1️⃣  创建 GitHub 仓库
echo     访问: https://github.com/new
echo     仓库名: ethusdt-quantitative-system
echo     选择: Public (必须)
echo     ⚠️  不要勾选任何初始化选项
echo.

pause

echo.
echo 2️⃣  配置远程仓库
echo.
set /p GITHUB_USER="请输入你的 GitHub 用户名: "

echo.
echo 正在配置...
git remote add origin https://github.com/%GITHUB_USER%/ethusdt-quantitative-system.git

if errorlevel 1 (
    echo ❌ 配置失败
    pause
    exit /b 1
)

echo ✅ 远程仓库配置成功
echo.
echo 3️⃣  推送代码到 GitHub
echo.

set /p CONFIRM="是否现在推送代码? (Y/N): "
if /i "%CONFIRM%"=="Y" (
    echo.
    echo 正在推送...
    git branch -M master
    git push -u origin master
    
    if errorlevel 1 (
        echo ❌ 推送失败
        echo 请检查：
        echo 1. GitHub 仓库是否已创建
        echo 2. 是否已登录 GitHub
        echo pause
        exit /b 1
    )
    
    echo ✅ 代码推送成功
    echo.
    echo 🌐 GitHub 地址:
    echo https://github.com/%GITHUB_USER%/ethusdt-quantitative-system
    echo.
)

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║           ✅ 配置完成！                          ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo 下一步：
echo 1. 访问 https://share.streamlit.io/
echo 2. 使用 GitHub 登录
echo 3. 点击 "New app" 创建应用
echo 4. 选择 ethusdt-quantitative-system 仓库
echo 5. Main file path: app_coinex.py
echo 6. 点击 "Deploy!"
echo.
echo 访问地址将是：
echo https://ethusdt-quantitative-system-%GITHUB_USER%.streamlit.app
echo.

pause
