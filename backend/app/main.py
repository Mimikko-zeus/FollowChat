"""FastAPI application exposing FollowChat database CRUD APIs."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Generator, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import re

from backend.database import (
    Conversation,
    Message,
    Config,
    init_db,
    create_conversation,
    get_conversation,
    get_conversation_ancestry,
    list_conversations,
    update_conversation,
    delete_conversation,
    create_message,
    get_messages_for_conversation,
    get_message_path_to_root,
    update_message,
    delete_message,
    upsert_config,
    get_config,
)
from backend.llm.client import LLMClientError, OpenAICompatibleLLM
from backend.config import Config as AppConfig


class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", max_length=255)


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)


class MessageCreate(BaseModel):
    content: str


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    order_index: Optional[int] = Field(default=None, ge=0)
    summary: Optional[str] = None


class ConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: str
    temperature: float = 1.0


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: str

    @classmethod
    def from_model(cls, conversation: Conversation) -> "ConversationOut":
        return cls(**asdict(conversation))


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    content: str
    order_index: int
    summary: Optional[str]
    parent_id: Optional[int]
    assistant_reply: Optional[str]
    created_at: str

    @classmethod
    def from_model(cls, message: Message) -> "MessageOut":
        data = asdict(message)
        # Remove role field from output
        data.pop("role", None)
        return cls(**data)


class ConfigOut(BaseModel):
    id: int
    api_key: Optional[str]
    base_url: Optional[str]
    model_name: str
    temperature: float
    updated_at: str

    @classmethod
    def from_model(cls, config: Config) -> "ConfigOut":
        return cls(**asdict(config))


class LLMReplyRequest(BaseModel):
    content: str = Field(min_length=1)
    parent_id: Optional[int] = None


class LLMReplyResponse(BaseModel):
    user_message: MessageOut


ASSISTANT_SYSTEM_PROMPT = (
    "你是 FollowChat 助手，需要根据当前会话历史回答用户最新的问题。"
    "保持专业且简洁，如信息不足请主动说明。"
)

MODEL_IDENTITY_RESPONSE = (
    "我是FollowChat 助手，为你提供分支对话管理。"
)


def is_model_related_question(content: str) -> bool:
    """检测用户问题是否与模型身份相关"""
    content_lower = content.lower().strip()
    # 检测关键词
    model_keywords = [
        "你是什么", "你是谁", "你是什么模型", "你是什么ai", "你是什么助手",
        "什么模型", "哪个模型", "用的什么", "基于什么", "什么技术",
        "what are you", "who are you", "what model", "which model",
        "你叫什么", "你的名字", "你的身份"
    ]
    # 检测判断性问题
    judgment_patterns = [
        r"你是.*吗\?*$", r"你是.*吗？", r"你是.*？", r"你是.*\?",
        r"是不是.*", r"是否.*", r"能否.*", r"会不会.*"
    ]
    
    # 检查关键词
    for keyword in model_keywords:
        if keyword in content_lower:
            return True
    
    # 检查判断性模式
    for pattern in judgment_patterns:
        if re.search(pattern, content_lower):
            return True
    
    return False

SUMMARY_SYSTEM_PROMPT = (
    "请用5-10个字概括用户刚刚输入的内容，仅返回概括文本。"
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    # Initialize config from environment variables if not already in database
    db_config = get_config()
    if db_config is None:
        # Use values from config file/environment variables
        upsert_config(
            api_key=AppConfig.get_api_key(),
            base_url=AppConfig.get_base_url(),
            model_name=AppConfig.get_model_name(),
            temperature=AppConfig.get_temperature(),
        )
    yield


app = FastAPI(title="FollowChat API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/conversations", response_model=List[ConversationOut])
def api_list_conversations(parent_id: Optional[int] = None) -> List[ConversationOut]:
    conversations = list_conversations(parent_id=parent_id)
    return [ConversationOut.from_model(c) for c in conversations]


@app.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
def api_create_conversation(payload: ConversationCreate) -> ConversationOut:
    conversation = create_conversation(title=payload.title)
    return ConversationOut.from_model(conversation)


@app.get("/conversations/{conversation_id}", response_model=ConversationOut)
def api_get_conversation(conversation_id: int) -> ConversationOut:
    try:
        conversation = get_conversation(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ConversationOut.from_model(conversation)


@app.get(
    "/conversations/{conversation_id}/ancestry", response_model=List[ConversationOut]
)
def api_get_conversation_ancestry(conversation_id: int) -> List[ConversationOut]:
    try:
        conversations = get_conversation_ancestry(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return [ConversationOut.from_model(convo) for convo in conversations]


@app.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def api_update_conversation(
    conversation_id: int, payload: ConversationUpdate
) -> ConversationOut:
    if payload.title is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided",
        )
    try:
        conversation = update_conversation(conversation_id, title=payload.title)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ConversationOut.from_model(conversation)


@app.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def api_delete_conversation(conversation_id: int) -> None:
    delete_conversation(conversation_id)


@app.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageOut],
)
def api_get_messages(
    conversation_id: int,
    include_ancestors: bool = False,
) -> List[MessageOut]:
    try:
        # Verify conversation exists
        get_conversation(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    
    try:
        messages = get_messages_for_conversation(conversation_id)
        return [MessageOut.from_model(m) for m in messages]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching messages: {str(exc)}"
        )


@app.get(
    "/messages/{message_id}/path-to-root",
    response_model=List[MessageOut],
)
def api_get_message_path_to_root(message_id: int) -> List[MessageOut]:
    """Get the path from a message to the root message."""
    try:
        messages = get_message_path_to_root(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return [MessageOut.from_model(m) for m in messages]


@app.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
def api_create_message(conversation_id: int, payload: MessageCreate) -> MessageOut:
    try:
        message = create_message(
            conversation_id=conversation_id,
            content=payload.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return MessageOut.from_model(message)


@app.patch("/messages/{message_id}", response_model=MessageOut)
def api_update_message(message_id: int, payload: MessageUpdate) -> MessageOut:
    if (
        payload.content is None
        and payload.order_index is None
        and payload.summary is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided",
        )
    try:
        message = update_message(
            message_id,
            content=payload.content,
            order_index=payload.order_index,
            summary=payload.summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return MessageOut.from_model(message)


@app.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_message(message_id: int) -> None:
    delete_message(message_id)


def _stream_llm_reply(
    conversation_id: int,
    payload: LLMReplyRequest,
    conversation: Conversation,
    config: Config,
    llm_client: OpenAICompatibleLLM,
    user_message: Message,
) -> Generator[str, None, None]:
    """流式生成 LLM 回复的内部函数"""
    # 首先发送消息 ID，让前端知道要更新哪个消息
    yield json.dumps({
        "type": "message_id",
        "message_id": user_message.id
    }, ensure_ascii=False) + "\n"
    
    # 检测是否是模型相关问题
    if is_model_related_question(payload.content):
        # 直接返回特定回答
        response_text = MODEL_IDENTITY_RESPONSE
        # 流式输出每个字符
        for char in response_text:
            yield json.dumps({"type": "delta", "content": char}, ensure_ascii=False) + "\n"
        yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
        # 保存完整回复
        user_message = update_message(user_message.id, assistant_reply=response_text)
        return
    
    # 获取消息历史
    history = get_message_path_to_root(user_message.id)
    llm_messages = [{"role": "system", "content": ASSISTANT_SYSTEM_PROMPT}]
    for msg in history:
        if msg.role == "user":
            llm_messages.append({"role": "user", "content": msg.content})
            if msg.assistant_reply:
                llm_messages.append({"role": "assistant", "content": msg.assistant_reply})
        elif msg.role == "assistant":
            llm_messages.append({"role": "assistant", "content": msg.content})
    
    # 流式调用 LLM
    assistant_content = ""
    try:
        for delta in llm_client.stream(llm_messages, temperature=config.temperature):
            assistant_content += delta
            yield json.dumps({"type": "delta", "content": delta}, ensure_ascii=False) + "\n"
    except LLMClientError as exc:
        error_msg = f"LLM 请求失败: {exc}"
        yield json.dumps({"type": "error", "content": error_msg}, ensure_ascii=False) + "\n"
        return
    
    # 发送完成信号
    yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
    
    # 保存完整回复
    assistant_content = assistant_content.strip()
    user_message = update_message(user_message.id, assistant_reply=assistant_content)
    
    # 生成摘要（异步，不阻塞流式输出）
    summary_prompt = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": payload.content},
    ]
    
    try:
        summary_completion = llm_client.complete(summary_prompt, temperature=0.2)
        summary_text = summary_completion.choice.content.strip()
    except LLMClientError:
        summary_text = None
    
    if summary_text:
        trimmed_summary = summary_text[:255]
        user_message = update_message(user_message.id, summary=trimmed_summary)
        summary_text = trimmed_summary
    
    # 更新对话标题（如果需要）
    should_update_title = conversation.title in {"新对话", "", None}
    if should_update_title and user_message.order_index == 0:
        title_candidate = summary_text or payload.content.strip()
        if title_candidate:
            update_conversation(conversation_id, title=title_candidate[:255])


@app.post("/conversations/{conversation_id}/llm-reply")
def api_conversation_llm_reply(
    conversation_id: int, payload: LLMReplyRequest
) -> StreamingResponse:
    # Ensure conversation exists
    try:
        conversation = get_conversation(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    config = get_config()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LLM 配置尚未初始化",
        )

    llm_client = OpenAICompatibleLLM(
        api_key=config.api_key,
        model_name=config.model_name,
        api_base=config.base_url,
        timeout=30.0,
    )

    # Use parent_id from payload, or fallback to last message if not provided
    parent_message_id = payload.parent_id
    if parent_message_id is None:
        existing_messages = get_messages_for_conversation(conversation_id)
        parent_message_id = existing_messages[-1].id if existing_messages else None

    user_message = create_message(
        conversation_id=conversation_id,
        content=payload.content,
        parent_id=parent_message_id,
    )

    # 返回流式响应
    return StreamingResponse(
        _stream_llm_reply(
            conversation_id=conversation_id,
            payload=payload,
            conversation=conversation,
            config=config,
            llm_client=llm_client,
            user_message=user_message,
        ),
        media_type="application/x-ndjson",
    )


@app.get("/config", response_model=ConfigOut)
def api_get_config() -> ConfigOut:
    config = get_config()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Config not initialized"
        )
    return ConfigOut.from_model(config)


@app.put("/config", response_model=ConfigOut)
def api_upsert_config(payload: ConfigUpdate) -> ConfigOut:
    config = upsert_config(
        api_key=payload.api_key,
        base_url=payload.base_url,
        model_name=payload.model_name,
        temperature=payload.temperature,
    )
    return ConfigOut.from_model(config)


@app.get("/")
def root() -> dict:
    return {"message": "FollowChat API running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)


