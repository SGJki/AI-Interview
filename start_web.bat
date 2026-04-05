@echo off
echo ========================================
echo AI Interview Web 前端启动
echo ========================================
echo.

cd /d "%~dp0"

echo 使用 Python 内置服务器启动静态文件服务...
echo 访问 http://127.0.0.1:3000 查看前端页面
echo.
echo 注意: 请先启动 API 服务 (start_api.bat)
echo 按 Ctrl+C 停止服务
echo.

python -m http.server 3000 --directory src\web
