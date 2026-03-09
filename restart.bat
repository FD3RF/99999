@echo off
echo 正在停止旧的 Streamlit 进程...
taskkill /F /IM streamlit.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq *streamlit*" 2>nul
timeout /t 2 /nobreak >nul

echo 正在启动新的 Streamlit 应用...
start "ETHUSDT量化系统" cmd /k "cd /d c:/Users/Administrator/新建文件夹/888 && python -m streamlit run app.py"

echo 应用已启动！
timeout /t 3 /nobreak >nul
