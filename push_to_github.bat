@echo off
set PATH=%PATH%;C:\Program Files\Git\bin
cd /d "%~dp0"
git remote add origin https://github.com/FD3RF/99999.git
git push -u origin master
pause
