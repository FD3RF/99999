@echo off
cd /d c:\Users\Administrator\新建文件夹\888
start /b python -m streamlit run app_coinex.py --server.headless=true --server.port=8501 >nul 2>&1
