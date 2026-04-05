@echo off
echo ========================================
echo AI Interview API 服务启动
echo ========================================
echo.

cd /d "%~dp0"

echo 激活虚拟环境...
call .venv\Scripts\activate.bat

echo.
echo 启动 API 服务 (端口 8000)...
echo 访问 http://127.0.0.1:8000/docs 查看 API 文档
echo.

uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
