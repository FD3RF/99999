Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\Administrator\新建文件夹\888"
WshShell.Run "cmd /c python -m streamlit run app_coinex.py --server.headless=true --server.port=8501", 0, False
WScript.Sleep 3000
WshShell.Run "http://localhost:8501", 1, False
