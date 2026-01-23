# tests/test_conversation.py
"""Tests for the ConversationManager module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch
import tempfile
import shutil
from anyio import Path as AnyioPath

from src.query.conversation import (
    ConversationManager,
    Conversation,
    ConversationTurn,
)


class TestConversationTurn:
    """Tests for ConversationTurn dataclass."""

    def test_turn_creation(self):
        """Test creating a conversation turn."""
        turn = ConversationTurn(
            role="user",
            content="What is the answer?",
        )

        assert turn.role == "user"
        assert turn.content == "What is the answer?"
        assert turn.timestamp  # Auto-generated
        assert turn.sources == []

    def test_turn_with_sources(self):
        """Test turn with sources."""
        turn = ConversationTurn(
            role="assistant",
            content="The answer is 42",
            sources=["guide.md", "reference.md"],
        )

        assert turn.sources == ["guide.md", "reference.md"]


class TestConversation:
    """Tests for Conversation dataclass."""

    def test_conversation_to_dict(self):
        """Test converting conversation to dict."""
        conv = Conversation(
            id="test-id",
            title="Test Conversation",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            turns=[
                ConversationTurn(
                    role="user",
                    content="Hello",
                    timestamp="2024-01-01T00:00:00",
                ),
            ],
        )

        data = conv.to_dict()

        assert data["id"] == "test-id"
        assert data["title"] == "Test Conversation"
        assert len(data["turns"]) == 1
        assert data["turns"][0]["role"] == "user"

    def test_conversation_from_dict(self):
        """Test creating conversation from dict."""
        data = {
            "id": "test-id",
            "title": "Test",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "turns": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": "2024-01-01T00:00:00",
                    "sources": [],
                },
            ],
        }

        conv = Conversation.from_dict(data)

        assert conv.id == "test-id"
        assert conv.title == "Test"
        assert len(conv.turns) == 1
        assert conv.turns[0].content == "Hello"


class TestConversationManager:
    """Tests for ConversationManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a ConversationManager with temp storage."""
        return ConversationManager(storage_dir=temp_dir)

    @pytest.mark.asyncio
    async def test_create_conversation(self, manager):
        """Test creating a new conversation."""
        conv = await manager.create(title="New Conversation")

        assert conv.id is not None
        assert conv.title == "New Conversation"
        assert conv.turns == []
        assert conv.created_at is not None
        assert conv.updated_at is not None

    def test_get_path_returns_anyio_path(self, manager):
        """Ensure async Path is used for I/O."""
        path = manager._get_path("test-id")
        assert isinstance(path, AnyioPath)

    @pytest.mark.asyncio
    async def test_create_conversation_without_title(self, manager):
        """Test creating conversation without title."""
        conv = await manager.create()

        assert conv.id is not None
        assert conv.title is None

    @pytest.mark.asyncio
    async def test_get_conversation(self, manager):
        """Test getting a conversation by ID."""
        created = await manager.create(title="Test")

        retrieved = await manager.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, manager):
        """Test getting a conversation that doesn't exist."""
        result = await manager.get("nonexistent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_add_turn(self, manager):
        """Test adding a turn to a conversation."""
        conv = await manager.create()

        updated = await manager.add_turn(
            conv.id,
            role="user",
            content="What is Python?",
        )

        assert updated is not None
        assert len(updated.turns) == 1
        assert updated.turns[0].role == "user"
        assert updated.turns[0].content == "What is Python?"

    @pytest.mark.asyncio
    async def test_add_turn_with_sources(self, manager):
        """Test adding turn with sources."""
        conv = await manager.create()

        updated = await manager.add_turn(
            conv.id,
            role="assistant",
            content="Python is a programming language",
            sources=["python/intro.md"],
        )

        assert updated.turns[0].sources == ["python/intro.md"]

    @pytest.mark.asyncio
    async def test_add_turn_auto_title(self, manager):
        """Test that first user message becomes title."""
        conv = await manager.create()
        assert conv.title is None

        updated = await manager.add_turn(
            conv.id,
            role="user",
            content="What is the meaning of life?",
        )

        assert updated.title == "What is the meaning of life?"

    @pytest.mark.asyncio
    async def test_add_turn_title_truncation(self, manager):
        """Test that long titles are truncated."""
        conv = await manager.create()

        long_content = "A" * 100

        updated = await manager.add_turn(
            conv.id,
            role="user",
            content=long_content,
        )

        assert len(updated.title) <= 53  # 50 chars + "..."
        assert updated.title.endswith("...")

    @pytest.mark.asyncio
    async def test_add_turn_to_nonexistent(self, manager):
        """Test adding turn to nonexistent conversation."""
        result = await manager.add_turn(
            "nonexistent-id",
            role="user",
            content="Hello",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_list_conversations(self, manager):
        """Test listing conversations."""
        await manager.create(title="First")
        await manager.create(title="Second")
        await manager.create(title="Third")

        convs = await manager.list_conversations()

        assert len(convs) == 3

    @pytest.mark.asyncio
    async def test_list_conversations_limit(self, manager):
        """Test listing with limit."""
        for i in range(5):
            await manager.create(title=f"Conv {i}")

        convs = await manager.list_conversations(limit=3)

        assert len(convs) == 3

    @pytest.mark.asyncio
    async def test_list_conversations_offset(self, manager):
        """Test listing with offset."""
        for i in range(5):
            await manager.create(title=f"Conv {i}")

        convs = await manager.list_conversations(limit=2, offset=2)

        assert len(convs) == 2

    @pytest.mark.asyncio
    async def test_list_conversations_ordered_by_updated(self, manager):
        """Test that conversations are ordered by updated_at descending."""
        conv1 = await manager.create(title="First")
        conv2 = await manager.create(title="Second")

        # Update the first one
        await manager.add_turn(conv1.id, "user", "Update")

        convs = await manager.list_conversations()

        # First should now be at the top (most recently updated)
        assert convs[0].id == conv1.id

    @pytest.mark.asyncio
    async def test_delete_conversation(self, manager):
        """Test deleting a conversation."""
        conv = await manager.create(title="To Delete")

        deleted = await manager.delete(conv.id)

        assert deleted is True

        # Should not exist anymore
        result = await manager.get(conv.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, manager):
        """Test deleting nonexistent conversation."""
        deleted = await manager.delete("nonexistent-id")

        assert deleted is False

    def test_get_context_turns(self, manager):
        """Test getting context turns with limit."""
        conv = Conversation(
            id="test",
            title="Test",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            turns=[
                ConversationTurn(role="user", content=f"Message {i}")
                for i in range(10)
            ],
        )

        context = manager.get_context_turns(conv)

        # Should only return MAX_CONTEXT_TURNS
        assert len(context) == ConversationManager.MAX_CONTEXT_TURNS
        # Should be the most recent turns
        assert context[-1].content == "Message 9"

    def test_format_context(self, manager):
        """Test formatting conversation context."""
        conv = Conversation(
            id="test",
            title="Test",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            turns=[
                ConversationTurn(role="user", content="What is X?"),
                ConversationTurn(role="assistant", content="X is Y."),
            ],
        )

        formatted = manager.format_context(conv)

        assert "Previous conversation:" in formatted
        assert "User: What is X?" in formatted
        assert "Assistant: X is Y." in formatted

    def test_format_context_empty(self, manager):
        """Test formatting empty conversation."""
        conv = Conversation(
            id="test",
            title="Test",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            turns=[],
        )

        formatted = manager.format_context(conv)

        assert formatted == ""

    @pytest.mark.asyncio
    async def test_persistence(self, manager, temp_dir):
        """Test that conversations persist to disk."""
        conv = await manager.create(title="Persistent")
        await manager.add_turn(conv.id, "user", "Test message")

        # Check file exists
        file_path = Path(temp_dir) / f"{conv.id}.json"
        assert file_path.exists()

        # Load and verify
        with open(file_path) as f:
            data = json.load(f)

        assert data["id"] == conv.id
        assert data["title"] == "Persistent"
        assert len(data["turns"]) == 1

    @pytest.mark.asyncio
    async def test_atomic_save(self, manager, temp_dir):
        """Test that saves are atomic (use temp file)."""
        conv = await manager.create(title="Atomic Test")

        # Check that no .tmp files remain
        tmp_files = list(Path(temp_dir).glob("*.tmp"))
        assert len(tmp_files) == 0
