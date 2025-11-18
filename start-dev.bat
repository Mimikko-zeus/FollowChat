@echo off
chcp 65001 >nul
echo ========================================
echo FollowChat 开发环境启动脚本
echo ========================================
echo.

REM 检查虚拟环境
if not exist "venv" (
    echo [错误] 未找到虚拟环境，请先运行 deploy.bat
    pause
    exit /b 1
)

REM 检查 .env 文件
if not exist ".env" (
    echo [警告] 未找到 .env 文件，请先配置环境变量
    echo.
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 启动后端（后台）
echo 启动后端服务...
start "FollowChat Backend" cmd /k "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端
echo 启动前端服务...
cd frontend\followchat
start "FollowChat Frontend" cmd /k "npm run dev"
cd ..\..

echo.
echo ========================================
echo 服务已启动！
echo ========================================
echo 后端: http://localhost:8000
echo 前端: http://localhost:5173
echo API 文档: http://localhost:8000/docs
echo.
echo 按任意键关闭所有服务...
pause >nul

REM 关闭服务
taskkill /FI "WINDOWTITLE eq FollowChat Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq FollowChat Frontend*" /T /F >nul 2>&1

