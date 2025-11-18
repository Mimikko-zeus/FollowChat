#!/bin/bash

set -e

echo "========================================"
echo "FollowChat 开发环境启动脚本"
echo "========================================"
echo

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}[错误] 未找到虚拟环境，请先运行 ./deploy.sh${NC}"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[警告] 未找到 .env 文件，请先配置环境变量${NC}"
    echo
fi

# 激活虚拟环境
source venv/bin/activate

# 清理函数
cleanup() {
    echo
    echo -e "${YELLOW}正在关闭服务...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 启动后端
echo -e "${GREEN}启动后端服务...${NC}"
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo -e "${GREEN}启动前端服务...${NC}"
cd frontend/followchat
npm run dev &
FRONTEND_PID=$!
cd ../..

echo
echo "========================================"
echo -e "${GREEN}服务已启动！${NC}"
echo "========================================"
echo "后端: http://localhost:8000"
echo "前端: http://localhost:5173"
echo "API 文档: http://localhost:8000/docs"
echo
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo

# 等待
wait

