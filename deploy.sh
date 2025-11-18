#!/bin/bash

set -e

echo "========================================"
echo "FollowChat 一键部署脚本 (Linux/Mac)"
echo "========================================"
echo

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Python
echo "[1/6] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Python3，请先安装 Python 3.8+${NC}"
    exit 1
fi
python3 --version
echo

# 检查 Node.js
echo "[2/6] 检查 Node.js 环境..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Node.js，请先安装 Node.js 16+${NC}"
    exit 1
fi
node --version
echo

# 检查并创建虚拟环境
echo "[3/6] 设置 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi
echo "激活虚拟环境..."
source venv/bin/activate
echo

# 安装后端依赖
echo "[4/6] 安装后端依赖..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 后端依赖安装失败${NC}"
    exit 1
fi
echo -e "${GREEN}后端依赖安装完成${NC}"
echo

# 初始化数据库
echo "[5/6] 初始化数据库..."
python3 -c "from backend.database import init_db; init_db(); print('数据库初始化完成')"
if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 数据库初始化失败${NC}"
    exit 1
fi
echo

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[提示] 未找到 .env 文件${NC}"
    if [ -f ".env.example" ]; then
        echo "正在从 .env.example 创建 .env 文件..."
        cp .env.example .env
        echo -e "${YELLOW}请编辑 .env 文件并填写 LLM_API_KEY 等配置${NC}"
    else
        echo -e "${YELLOW}请创建 .env 文件并配置 LLM_API_KEY${NC}"
    fi
    echo
fi

# 安装前端依赖
echo "[6/6] 安装前端依赖..."
cd frontend/followchat
if [ ! -d "node_modules" ]; then
    echo "安装 npm 依赖包（这可能需要几分钟）..."
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 前端依赖安装失败${NC}"
        cd ../..
        exit 1
    fi
else
    echo -e "${GREEN}前端依赖已存在，跳过安装${NC}"
fi
cd ../..
echo

echo "========================================"
echo -e "${GREEN}部署完成！${NC}"
echo "========================================"
echo
echo "下一步："
echo "1. 编辑 .env 文件，配置 LLM_API_KEY"
echo "2. 启动后端服务："
echo "   source venv/bin/activate"
echo "   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
echo "3. 启动前端服务（新开一个终端）："
echo "   cd frontend/followchat"
echo "   npm run dev"
echo
echo "或者使用 ./start-dev.sh 同时启动前后端"
echo

