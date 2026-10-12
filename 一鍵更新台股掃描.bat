@echo off
chcp 65001 >nul
echo ========================================
echo   台股價格行為系統 - 一鍵更新與掃描
echo ========================================
cd /d "C:\Users\201633\Downloads\node-v24.21.0-win-x64\node-v24.21.0-win-x64"

echo [1/2] 正在執行選股掃描 (scanner.py)...
"C:\Users\201633\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scanner.py

echo.
echo [2/2] 正在開啟掃描結果網頁 (public/index.html)...
start "" "public\index.html"

echo.
echo 掃描與開啟網頁完成！
pause
