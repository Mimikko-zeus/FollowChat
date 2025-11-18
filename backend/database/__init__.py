"""
Database package for FollowChat.

This package exposes utility helpers to interact with the local SQLite
database that stores conversations, messages, and user configuration.
"""

from .crud import (
    Conversation,
    Message,
    Config,
    init_db,
    create_conversation,
    get_conversation,
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
    get_conversation_ancestry,
)

__all__ = [
    "Conversation",
    "Message",
    "Config",
    "init_db",
    "create_conversation",
    "get_conversation",
    "list_conversations",
    "update_conversation",
    "delete_conversation",
    "create_message",
    "get_messages_for_conversation",
    "get_message_path_to_root",
    "update_message",
    "delete_message",
    "upsert_config",
    "get_config",
    "get_conversation_ancestry",
]

