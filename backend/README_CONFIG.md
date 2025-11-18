# 配置文件说明

FollowChat 后端支持通过环境变量或 `.env` 文件配置 LLM API 参数。

## 配置方式

### 方式 1: 使用 .env 文件（推荐）

在项目根目录创建 `.env` 文件，内容如下：

```env
# LLM API Configuration
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-3.5-turbo
LLM_TEMPERATURE=1.0
```

### 方式 2: 使用环境变量

直接在系统环境变量中设置：

- `LLM_API_KEY`: LLM API 密钥
- `LLM_BASE_URL`: LLM API 基础 URL（默认: https://api.openai.com/v1）
- `LLM_MODEL_NAME`: 模型名称（默认: gpt-3.5-turbo）
- `LLM_TEMPERATURE`: 温度参数（默认: 1.0）

## 配置参数说明

### LLM_API_KEY
- **必需**: 是（如果使用 API）
- **说明**: 你的 LLM 服务 API 密钥
- **示例**: 
  - OpenAI: `sk-...`
  - Anthropic: `sk-ant-...`
  - 其他兼容服务: 根据服务商提供

### LLM_BASE_URL
- **必需**: 否
- **默认值**: `https://api.openai.com/v1`
- **说明**: LLM API 的基础 URL
- **示例**:
  - OpenAI: `https://api.openai.com/v1`
  - Anthropic: `https://api.anthropic.com/v1`
  - 本地服务: `http://localhost:11434/v1`
  - 其他兼容 API: 根据服务商提供

### LLM_MODEL_NAME
- **必需**: 否
- **默认值**: `gpt-3.5-turbo`
- **说明**: 要使用的模型名称
- **示例**:
  - OpenAI: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`
  - Anthropic: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`
  - 本地模型: `llama2`, `mistral`, 等

### LLM_TEMPERATURE
- **必需**: 否
- **默认值**: `1.0`
- **说明**: 控制模型输出的随机性（0.0 到 2.0）
  - 较低值（0.0-0.5）: 更确定、更一致的回答
  - 中等值（0.5-1.0）: 平衡创造性和一致性
  - 较高值（1.0-2.0）: 更创造性、更多样化的回答

## 初始化行为

应用启动时，如果数据库中没有配置，会自动使用 `.env` 文件或环境变量中的值初始化配置。

如果数据库已有配置，则优先使用数据库中的配置（可通过 API 的 `/config` 端点修改）。

## 安装依赖

如果使用 `.env` 文件，需要安装 `python-dotenv`:

```bash
pip install python-dotenv
```

## 安全提示

⚠️ **重要**: `.env` 文件包含敏感信息，请确保：
1. 不要将 `.env` 文件提交到版本控制系统
2. 在 `.gitignore` 中添加 `.env`
3. 使用 `.env.example` 作为模板（不包含真实密钥）

