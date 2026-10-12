@echo off
chcp 65001 >nul
echo ========================================
echo   台股價格行為系統 - 一鍵啟動
echo ========================================
cd /d "C:\Users\201633\Downloads\node-v24.21.0-win-x64\node-v24.21.0-win-x64"

echo [1/3] 正在背景啟動本地伺服器 (http.server 8000)...
start /B "" "C:\Users\201633\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m http.server 8000 >nul 2>&1

echo [2/3] 正在背景啟動自動排程掃描器 (auto_scanner.py)...
start /B "" "C:\Users\201633\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" auto_scanner.py >nul 2>&1

echo [3/3] 正在開啟選股結果網頁...
start http://localhost:8000/public/index.html

echo.
echo 系統已全部在背景啟動完成！
timeout /t 3 >nul
