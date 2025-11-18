# FollowChat API 文档

本文档基于 `backend/app/main.py` 中定义的 FastAPI 应用，列出了可用的 REST 接口及其请求/响应格式。所有接口默认返回 `application/json`，并允许跨域访问。

## 健康检查

- **GET** `/health`
  - 用于探测服务状态。
  - **200 响应**：`{"status": "ok"}`

## 对话（Conversation）

### 列出对话
- **GET** `/conversations`
  - 查询参数：`parent_id`（可选，int）若提供则仅返回该父级下的子对话。
  - **200 响应**：`ConversationOut[]`

### 创建对话
- **POST** `/conversations`
  - **请求体** `ConversationCreate`
    ```json
    {
      "title": "新对话标题",
      "parent_id": 1
    }
    ```
    `title` 默认值为“新对话”，最长 255 字符；`parent_id` 可为空。
  - **201 响应**：`ConversationOut`

### 获取单个对话
- **GET** `/conversations/{conversation_id}`
  - 找不到记录时返回 404。
  - **200 响应**：`ConversationOut`

### 获取对话谱系
- **GET** `/conversations/{conversation_id}/ancestry`
  - 返回从根节点到指定对话的列表。
  - 404：对话不存在。
  - **200 响应**：`ConversationOut[]`

### 更新对话
- **PATCH** `/conversations/{conversation_id}`
  - **请求体** `ConversationUpdate`
    ```json
    {
      "title": "重命名",
      "parent_id": 2
    }
    ```
    至少提供一个字段；否则返回 400。
  - 404：对话不存在。
  - **200 响应**：`ConversationOut`

### 删除对话
- **DELETE** `/conversations/{conversation_id}`
  - 无响应体，始终返回 204。

## 消息（Message）

### 获取消息列表
- **GET** `/conversations/{conversation_id}/messages`
  - 查询参数：`include_ancestors`（bool，默认 false），若为 true 则包含祖先对话的消息。
  - **200 响应**：`MessageOut[]`

### 创建消息
- **POST** `/conversations/{conversation_id}/messages`
  - **请求体** `MessageCreate`
    ```json
    {
      "role": "user | assistant | system",
      "content": "消息内容"
    }
    ```
    `role` 必须匹配三种角色之一，`summary` 字段由系统计算，调用方无需提供。
  - 400：payload 校验或创建失败。
  - **201 响应**：`MessageOut`

### 更新消息
- **PATCH** `/messages/{message_id}`
  - **请求体** `MessageUpdate`
    ```json
    {
      "role": "assistant",
      "content": "修改后的内容",
      "order_index": 3,
      "summary": "（可选）简介"
    }
    ```
    需至少提供一个字段；否则 400。
  - 404：消息不存在。
  - **200 响应**：`MessageOut`

### 删除消息
- **DELETE** `/messages/{message_id}`
  - 无响应体，返回 204。

## 配置（Config）

### 获取配置
- **GET** `/config`
  - 若尚未初始化配置则返回 404。
  - **200 响应**：`ConfigOut`

### 新建/更新配置
- **PUT** `/config`
  - **请求体** `ConfigUpdate`
    ```json
    {
      "api_key": "sk-xxx",
      "base_url": "https://example.com/v1",
      "model_name": "gpt-4o",
      "temperature": 0.7
    }
    ```
    `model_name` 必填，其余可选。
  - **200 响应**：`ConfigOut`

## 数据模型

- `ConversationOut`: `{id, title, parent_id, created_at}`
- `MessageOut`: `{id, conversation_id, role, content, order_index, summary, created_at}`
- `ConfigOut`: `{id, api_key, base_url, model_name, temperature, updated_at}`

## LLM 自动回复

- **POST** `/conversations/{conversation_id}/llm-reply`
  - **请求体** `LLMReplyRequest`
    ```json
    {
      "content": "用户输入"
    }
    ```
  - 处理流程：
    1. 将用户输入写入消息表。
    2. 读取会话历史并调用 `OpenAICompatibleLLM` 获取助手回复。
    3. 使用第二次 LLM 调用生成该输入的简介，并写回用户消息的 `summary` 字段。
    4. 返回用户消息与助手消息。
  - **200 响应**
    ```json
    {
      "user_message": { ...MessageOut },
      "assistant_message": { ...MessageOut }
    }
    ```
  - 400：未配置 LLM 参数。
  - 404：会话不存在。
  - 502：上游 LLM 请求失败。

## 本地开发

启动开发服务器：

```bash
uvicorn backend.app.main:app --reload --port 8000
```

默认开放 `http://localhost:8000`，可结合 Swagger UI (`/docs`) 或 ReDoc (`/redoc`) 进行调试。

