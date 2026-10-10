@echo off
echo ====================================
echo Legal QA System - 启动脚本
echo ====================================
echo.

cd /d E:\陈杰\Legal_qa_system

echo [1/4] 检查依赖服务...
docker ps | findstr /C:"legal_qa_mysql" /C:"legal_qa_redis" /C:"milvus-standalone"
if errorlevel 1 (
    echo 错误: 依赖服务未运行！
    echo 请先启动 Docker 服务
    pause
    exit /b 1
)
echo ✅ 依赖服务运行正常
echo.

echo [2/4] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo 错误: Python 未安装或未加入 PATH
    pause
    exit /b 1
)
echo ✅ Python 环境正常
echo.

echo [3/4] 检查依赖包...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 依赖包未安装，正在安装...
    pip install -r config\requirements.txt
)
echo ✅ 依赖包已安装
echo.

echo [4/4] 启动服务...
echo.
echo ====================================
echo 服务地址: http://localhost:8003
echo 按 Ctrl+C 停止服务
echo ====================================
echo.

python app.py
