# FollowChat

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 16+](https://img.shields.io/badge/node-16+-green.svg)](https://nodejs.org/)

一个支持对话树形结构的智能聊天应用，可以创建分支对话、回溯历史消息，提供更灵活的对话管理体验。

## 功能特性

- 🌳 **对话树形结构**：支持创建多个对话分支，探索不同的对话路径
- 💬 **流式响应**：实时显示 AI 回复，提供流畅的交互体验
- 📝 **Markdown 支持**：支持 Markdown 格式的消息渲染
- 🔄 **对话回溯**：可以查看和回溯到历史消息节点
- 🎨 **可视化树形图**：直观展示对话的树形结构
- ⚙️ **灵活配置**：支持多种 LLM API（OpenAI 兼容）
- 💾 **本地存储**：使用 SQLite 数据库存储对话数据

## 技术栈

### 后端
- **FastAPI** - 高性能 Python Web 框架
- **SQLite** - 轻量级数据库
- **httpx** - 异步 HTTP 客户端
- **Uvicorn** - ASGI 服务器

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript
- **Vite** - 快速的前端构建工具
- **Pinia** - Vue 状态管理
- **v-network-graph** - 网络图可视化组件
- **Marked** - Markdown 解析器

## 快速开始

### 前置要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 一键部署

#### Windows

```bash
deploy.bat
```

#### Linux / macOS

```bash
chmod +x deploy.sh
./deploy.sh
```

部署脚本会自动：
1. 检查并安装 Python 和 Node.js 依赖
2. 创建虚拟环境（如果需要）
3. 初始化数据库
4. 构建前端项目
5. 启动后端和前端服务

### 手动安装

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/FollowChat.git
cd FollowChat
```

> 注意：请将 `your-username` 替换为您的 GitHub 用户名或组织名

#### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# LLM API 配置
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-3.5-turbo
LLM_TEMPERATURE=1.0
```

#### 3. 安装后端依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 4. 初始化数据库

```bash
python -c "from backend.database import init_db; init_db()"
```

#### 5. 安装前端依赖

```bash
cd frontend/followchat
npm install
```

#### 6. 构建前端

```bash
npm run build
```

#### 7. 启动服务

**启动后端**（在项目根目录）：

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

**启动前端开发服务器**（在 `frontend/followchat` 目录）：

```bash
npm run dev
```

或者使用生产构建：

```bash
# 将构建后的文件复制到后端静态文件目录
# 或者使用 nginx 等服务器托管
```

## 使用说明

1. **创建对话**：点击"新对话"按钮创建新的对话
2. **发送消息**：在输入框中输入消息并发送
3. **创建分支**：点击消息旁边的"分支"按钮创建新的对话分支
4. **切换分支**：在对话树中点击不同的节点切换到对应的对话路径
5. **查看树形图**：切换到树形视图查看完整的对话结构
6. **删除对话**：在侧边栏中删除不需要的对话

## 配置说明

### LLM API 配置

支持所有 OpenAI 兼容的 API，包括：

- OpenAI API
- Azure OpenAI
- 其他兼容 OpenAI API 格式的服务

配置方式：

1. **环境变量**：在 `.env` 文件中设置
2. **API 配置**：通过 `/api/config` 端点动态配置（优先级更高）

### 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_API_KEY` | LLM API 密钥 | 无（必需） |
| `LLM_BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `LLM_MODEL_NAME` | 模型名称 | `gpt-3.5-turbo` |
| `LLM_TEMPERATURE` | 温度参数 | `1.0` |

## API 文档

启动后端服务后，访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

详细的 API 文档请参考 `backend/app/API.md`。

## 项目结构

```
FollowChat/
├── backend/                 # 后端代码
│   ├── app/                # FastAPI 应用
│   │   ├── main.py         # 主应用文件
│   │   └── API.md          # API 文档
│   ├── database/           # 数据库相关
│   │   ├── crud.py         # CRUD 操作
│   │   └── followchat.db   # SQLite 数据库（自动生成）
│   ├── llm/                # LLM 客户端
│   │   └── client.py       # LLM API 客户端
│   ├── config.py           # 配置管理
│   └── README_CONFIG.md    # 配置说明文档
├── frontend/               # 前端代码
│   └── followchat/         # Vue 3 项目
│       ├── src/
│       │   ├── App.vue     # 主组件
│       │   ├── components/ # 组件
│       │   └── types/      # TypeScript 类型定义
│       └── package.json
├── .env.example            # 环境变量模板
├── requirements.txt        # Python 依赖
├── deploy.bat             # Windows 部署脚本
├── deploy.sh              # Linux/Mac 部署脚本
└── README.md              # 本文件
```

## 开发说明

### 后端开发

```bash
# 启动开发服务器（自动重载）
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发

```bash
cd frontend/followchat
npm run dev
```

前端开发服务器默认运行在 `http://localhost:5173`，会自动代理 API 请求到后端。

## 常见问题

### 1. 数据库初始化失败

确保有写入权限，数据库文件会创建在 `backend/database/` 目录下。

### 2. 前端无法连接后端

检查：
- 后端服务是否正常运行（http://localhost:8000）
- CORS 配置是否正确
- 前端 API 基础 URL 配置

### 3. LLM API 调用失败

检查：
- API 密钥是否正确
- API 基础 URL 是否正确
- 网络连接是否正常
- API 配额是否充足

## 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 贡献

我们欢迎所有形式的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与项目。

### 贡献方式

- 🐛 报告 Bug
- 💡 提出功能建议
- 📝 改进文档
- 🔧 提交代码修复或新功能
- ⭐ 给项目点个 Star

### 贡献者

感谢所有为项目做出贡献的开发者！

## 开源协议

本项目采用 MIT 许可证开源，您可以自由使用、修改和分发。详情请参阅 [LICENSE](LICENSE) 文件。

## 更新日志

### v0.1.0
- 初始版本
- 支持对话树形结构
- 支持流式响应
- 支持 Markdown 渲染
- 支持对话树可视化

