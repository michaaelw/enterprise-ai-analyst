"""Unit tests for chat history persistence (DuckDB + history routes)."""
from __future__ import annotations

from uuid import uuid4

import pytest

from src.integrations.data_warehouse.duckdb_store import DuckDBStore


@pytest.fixture
async def store() -> DuckDBStore:  # type: ignore[misc]
    s = DuckDBStore(":memory:")
    await s.connect()
    yield s  # type: ignore[misc]
    await s.close()


class TestChatTables:
    async def test_chat_tables_created(self, store: DuckDBStore) -> None:
        rows = await store.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        )
        table_names = {row["table_name"] for row in rows}
        assert "chat_sessions" in table_names
        assert "chat_messages" in table_names


class TestCreateSession:
    async def test_create_session(self, store: DuckDBStore) -> None:
        sid = str(uuid4())
        await store.create_session(sid, "Hello world")
        rows = await store.execute(
            "SELECT * FROM chat_sessions WHERE id = ?", {"id": sid}
        )
        assert len(rows) == 1
        assert rows[0]["title"] == "Hello world"
        assert rows[0]["message_count"] == 0


class TestSaveMessage:
    async def test_save_message_and_update_count(self, store: DuckDBStore) -> None:
        sid = str(uuid4())
        await store.create_session(sid, "Test session")

        msg_id = str(uuid4())
        await store.save_message({
            "id": msg_id,
            "session_id": sid,
            "role": "user",
            "content": "Hello",
        })

        msgs = await store.execute(
            "SELECT * FROM chat_messages WHERE session_id = ?", {"sid": sid}
        )
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello"

        sessions = await store.execute(
            "SELECT * FROM chat_sessions WHERE id = ?", {"id": sid}
        )
        assert sessions[0]["message_count"] == 1

    async def test_save_multiple_messages(self, store: DuckDBStore) -> None:
        sid = str(uuid4())
        await store.create_session(sid, "Multi-msg")

        for i in range(3):
            await store.save_message({
                "id": str(uuid4()),
                "session_id": sid,
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
            })

        sessions = await store.execute(
            "SELECT * FROM chat_sessions WHERE id = ?", {"id": sid}
        )
        assert sessions[0]["message_count"] == 3


class TestListSessions:
    async def test_list_sessions_ordered_by_updated(self, store: DuckDBStore) -> None:
        sid1 = str(uuid4())
        sid2 = str(uuid4())
        await store.create_session(sid1, "First")
        await store.create_session(sid2, "Second")

        # Add a message to first session to update its timestamp
        await store.save_message({
            "id": str(uuid4()),
            "session_id": sid1,
            "role": "user",
            "content": "Update first",
        })

        rows = await store.list_sessions(limit=10)
        assert len(rows) >= 2
        # First session should now be most recent (updated_at was bumped)
        assert rows[0]["id"] == sid1

    async def test_list_sessions_respects_limit(self, store: DuckDBStore) -> None:
        for i in range(5):
            await store.create_session(str(uuid4()), f"Session {i}")
        rows = await store.list_sessions(limit=3)
        assert len(rows) == 3


class TestGetSessionMessages:
    async def test_get_session_messages(self, store: DuckDBStore) -> None:
        sid = str(uuid4())
        await store.create_session(sid, "Test")

        await store.save_message({
            "id": str(uuid4()),
            "session_id": sid,
            "role": "user",
            "content": "Q1",
        })
        await store.save_message({
            "id": str(uuid4()),
            "session_id": sid,
            "role": "assistant",
            "content": "A1",
        })

        data = await store.get_session_messages(sid)
        assert data["session"] is not None
        assert data["session"]["title"] == "Test"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    async def test_get_nonexistent_session(self, store: DuckDBStore) -> None:
        data = await store.get_session_messages("nonexistent")
        assert data["session"] is None
        assert data["messages"] == []


class TestHistoryRoutes:
    """Test the history route handlers with a mocked app state."""

    async def test_save_message_auto_creates_session(self, store: DuckDBStore) -> None:
        """Simulates what the POST /history/messages endpoint does."""
        sid = str(uuid4())

        # Session doesn't exist yet
        existing = await store.get_session_messages(sid)
        assert existing["session"] is None

        # Auto-create (same logic as the route handler)
        title = "What are the key policies?"[:100]
        await store.create_session(sid, title)
        await store.save_message({
            "id": str(uuid4()),
            "session_id": sid,
            "role": "user",
            "content": "What are the key policies?",
        })

        data = await store.get_session_messages(sid)
        assert data["session"] is not None
        assert data["session"]["title"] == "What are the key policies?"
        assert len(data["messages"]) == 1
