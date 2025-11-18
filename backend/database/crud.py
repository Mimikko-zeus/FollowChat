"""SQLite CRUD helpers for FollowChat."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional, Sequence, Tuple
import sqlite3


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "followchat.db"


@dataclass(slots=True)
class Conversation:
    id: int
    title: str
    created_at: str


@dataclass(slots=True)
class Message:
    id: int
    conversation_id: int
    role: str
    content: str
    order_index: int
    summary: Optional[str]
    parent_id: Optional[int]
    assistant_reply: Optional[str]
    created_at: str


@dataclass(slots=True)
class Config:
    id: int
    api_key: Optional[str]
    base_url: Optional[str]
    model_name: str
    temperature: float
    updated_at: str


@contextmanager
def get_connection(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Create a SQLite connection with sensible defaults."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    """Create tables if they do not exist."""
    schema_statements = [
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT '新对话',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            parent_id INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES messages(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_conversation_order
            ON messages(conversation_id, order_index);
        """,
        """
        CREATE TABLE IF NOT EXISTS configs (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            api_key TEXT,
            base_url TEXT,
            model_name TEXT NOT NULL,
            temperature REAL DEFAULT 1.0,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ]

    with get_connection(db_path) as conn:
        for statement in schema_statements:
            conn.execute(statement)
        _ensure_message_summary_column(conn)
        _ensure_message_parent_id_column(conn)
        _ensure_message_assistant_reply_column(conn)
        _migrate_conversations_remove_parent_id(conn)


def _ensure_message_summary_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)")}
    if "summary" not in columns:
        conn.execute("ALTER TABLE messages ADD COLUMN summary TEXT")


def _ensure_message_parent_id_column(conn: sqlite3.Connection) -> None:
    """Ensure messages table has parent_id column."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)")}
    if "parent_id" not in columns:
        conn.execute("ALTER TABLE messages ADD COLUMN parent_id INTEGER")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_parent_id
            ON messages(parent_id)
        """)


def _ensure_message_assistant_reply_column(conn: sqlite3.Connection) -> None:
    """Ensure messages table has assistant_reply column."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)")}
    if "assistant_reply" not in columns:
        conn.execute("ALTER TABLE messages ADD COLUMN assistant_reply TEXT")


def _migrate_conversations_remove_parent_id(conn: sqlite3.Connection) -> None:
    """Remove parent_id column from conversations table if it exists."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(conversations)")}
    if "parent_id" in columns:
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        # First, disable foreign key checks temporarily
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL DEFAULT '新对话',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT INTO conversations_new (id, title, created_at)
                SELECT id, title, created_at FROM conversations
            """)
            conn.execute("DROP TABLE conversations")
            conn.execute("ALTER TABLE conversations_new RENAME TO conversations")
        finally:
            conn.execute("PRAGMA foreign_keys = ON")


def _row_to_conversation(row: sqlite3.Row) -> Conversation:
    return Conversation(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
    )


def _row_to_message(row: sqlite3.Row) -> Message:
    # sqlite3.Row doesn't support .get(), so we need to check if column exists
    # or use try-except. For nullable columns, we can use dict() conversion or direct access.
    row_dict = dict(row)
    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        content=row["content"],
        order_index=row["order_index"],
        summary=row_dict.get("summary"),
        parent_id=row_dict.get("parent_id"),
        assistant_reply=row_dict.get("assistant_reply"),
        created_at=row["created_at"],
    )


def _row_to_config(row: sqlite3.Row) -> Config:
    return Config(
        id=row["id"],
        api_key=row["api_key"],
        base_url=row["base_url"],
        model_name=row["model_name"],
        temperature=row["temperature"],
        updated_at=row["updated_at"],
    )


def create_conversation(title: str = "新对话") -> Conversation:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO conversations (title) VALUES (?)",
            (title,),
        )
        convo_id = cursor.lastrowid
    return get_conversation(convo_id)


def get_conversation(conversation_id: int) -> Conversation:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, created_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        return _row_to_conversation(row)


def get_conversation_ancestry(conversation_id: int) -> List[Conversation]:
    """Get conversation ancestry. Since conversations no longer have parent_id,
    this just returns the conversation itself."""
    conversation = get_conversation(conversation_id)
    return [conversation]


def list_conversations(parent_id: Optional[int] = None) -> List[Conversation]:
    """List conversations. parent_id parameter is ignored since conversations no longer have parent_id."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, created_at
            FROM conversations
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [_row_to_conversation(row) for row in rows]


def update_conversation(conversation_id: int, title: Optional[str] = None) -> Conversation:
    if title is None:
        raise ValueError("At least one field must be provided to update_conversation")

    with get_connection() as conn:
        conn.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id),
        )
    return get_conversation(conversation_id)


def delete_conversation(conversation_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def _next_order_index(conn: sqlite3.Connection, conversation_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(order_index), -1) AS max_order FROM messages WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchone()
    return int(row["max_order"]) + 1


def create_message(
    conversation_id: int,
    content: str,
    order_index: Optional[int] = None,
    summary: Optional[str] = None,
    parent_id: Optional[int] = None,
    assistant_reply: Optional[str] = None,
) -> Message:
    # All messages are user messages now
    role = "user"

    with get_connection() as conn:
        if order_index is None:
            order_index = _next_order_index(conn, conversation_id)
        cursor = conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, order_index, summary, parent_id, assistant_reply)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, order_index, summary, parent_id, assistant_reply),
        )
        message_id = cursor.lastrowid

    return get_message(message_id)


def get_message(message_id: int) -> Message:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, conversation_id, role, content, order_index, summary, parent_id, assistant_reply, created_at
            FROM messages WHERE id = ?
            """,
            (message_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Message {message_id} not found")
        return _row_to_message(row)


def get_messages_for_conversation(conversation_id: int, include_ancestors: bool = False) -> List[Message]:
    """Get messages for a conversation. include_ancestors is ignored since conversations no longer have parent_id."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, conversation_id, role, content, order_index, summary, parent_id, assistant_reply, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY order_index
            """,
            (conversation_id,),
        ).fetchall()
    return [_row_to_message(row) for row in rows]


def get_message_path_to_root(message_id: int) -> List[Message]:
    """Get the path from a message to the root message (parent_id is NULL).
    Returns messages in order from root to the given message."""
    path: List[Message] = []
    current_id: Optional[int] = message_id
    
    # First, collect all messages from the given message up to root
    while current_id is not None:
        try:
            message = get_message(current_id)
            path.append(message)
            current_id = message.parent_id
        except ValueError:
            break
    
    # Reverse to get path from root to the given message
    return list(reversed(path))


def update_message(
    message_id: int,
    *,
    content: Optional[str] = None,
    order_index: Optional[int] = None,
    summary: Optional[str] = None,
    parent_id: Optional[int] = None,
    assistant_reply: Optional[str] = None,
) -> Message:
    if content is None and order_index is None and summary is None and parent_id is None and assistant_reply is None:
        raise ValueError("At least one field must be provided to update_message")
    set_clauses: List[str] = []
    params: List[Any] = []
    if content is not None:
        set_clauses.append("content = ?")
        params.append(content)
    if order_index is not None:
        set_clauses.append("order_index = ?")
        params.append(order_index)
    if summary is not None:
        set_clauses.append("summary = ?")
        params.append(summary)
    if parent_id is not None:
        set_clauses.append("parent_id = ?")
        params.append(parent_id)
    if assistant_reply is not None:
        set_clauses.append("assistant_reply = ?")
        params.append(assistant_reply)
    params.append(message_id)
    query = f"UPDATE messages SET {', '.join(set_clauses)} WHERE id = ?"

    with get_connection() as conn:
        conn.execute(query, params)
    return get_message(message_id)


def delete_message(message_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))


def upsert_config(
    api_key: Optional[str],
    base_url: Optional[str],
    model_name: str,
    temperature: float = 1.0,
) -> Config:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO configs (id, api_key, base_url, model_name, temperature, updated_at)
            VALUES (1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                api_key = excluded.api_key,
                base_url = excluded.base_url,
                model_name = excluded.model_name,
                temperature = excluded.temperature,
                updated_at = CURRENT_TIMESTAMP
            """,
            (api_key, base_url, model_name, temperature),
        )
    return get_config()


def get_config() -> Optional[Config]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, api_key, base_url, model_name, temperature, updated_at FROM configs WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        return _row_to_config(row)


if not DB_PATH.exists():
    init_db()


def _demo() -> None:
    """Quick manual test when running this module directly."""
    init_db()
    root = create_conversation("Demo Root")
    child = create_conversation("Demo Child", parent_id=root.id)
    create_message(root.id, "user", "Hello from demo root")
    create_message(child.id, "assistant", "Hi from demo child")
    messages = get_messages_for_conversation(child.id, include_ancestors=True)
    config = upsert_config(
        api_key="demo-key",
        base_url="https://example.com/v1",
        model_name="gpt-demo",
        temperature=0.5,
    )
    print("root:", root)
    print("child:", child)
    print("messages:", messages)
    print("config:", config)


if __name__ == "__main__":
    _demo()
