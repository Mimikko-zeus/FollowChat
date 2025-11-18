@echo off
chcp 65001 >nul
echo ========================================
echo FollowChat 一键部署脚本 (Windows)
echo ========================================
echo.

REM 检查 Python
echo [1/6] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
python --version
echo.

REM 检查 Node.js
echo [2/6] 检查 Node.js 环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 16+
    pause
    exit /b 1
)
node --version
echo.

REM 检查并创建虚拟环境
echo [3/6] 设置 Python 虚拟环境...
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)
echo 激活虚拟环境...
call venv\Scripts\activate.bat
echo.

REM 安装后端依赖
echo [4/6] 安装后端依赖...
pip install -q --upgrade pip
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)
echo 后端依赖安装完成
echo.

REM 初始化数据库
echo [5/6] 初始化数据库...
python -c "from backend.database import init_db; init_db(); print('数据库初始化完成')"
if errorlevel 1 (
    echo [错误] 数据库初始化失败
    pause
    exit /b 1
)
echo.

REM 检查环境变量文件
if not exist ".env" (
    echo [提示] 未找到 .env 文件
    if exist ".env.example" (
        echo 正在从 .env.example 创建 .env 文件...
        copy .env.example .env >nul
        echo 请编辑 .env 文件并填写 LLM_API_KEY 等配置
    ) else (
        echo 请创建 .env 文件并配置 LLM_API_KEY
    )
    echo.
)

REM 安装前端依赖
echo [6/6] 安装前端依赖...
cd frontend\followchat
if not exist "node_modules" (
    echo 安装 npm 依赖包（这可能需要几分钟）...
    call npm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败
        cd ..\..
        pause
        exit /b 1
    )
) else (
    echo 前端依赖已存在，跳过安装
)
cd ..\..
echo.

echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 下一步：
echo 1. 编辑 .env 文件，配置 LLM_API_KEY
echo 2. 启动后端服务：
echo    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
echo 3. 启动前端服务（新开一个终端）：
echo    cd frontend\followchat
echo    npm run dev
echo.
echo 或者使用 start-dev.bat 同时启动前后端
echo.
pause

