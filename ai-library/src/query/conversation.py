"""Conversation manager for multi-turn query sessions.

Handles persistence of conversation history to disk.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional
import anyio


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sources: list[str] = field(default_factory=list)


@dataclass
class Conversation:
    """A conversation with multiple turns."""

    id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    turns: list[ConversationTurn] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turns": [asdict(turn) for turn in self.turns],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """Create from dictionary."""
        turns = [
            ConversationTurn(
                role=t["role"],
                content=t["content"],
                timestamp=t.get("timestamp", ""),
                sources=t.get("sources", []),
            )
            for t in data.get("turns", [])
        ]
        return cls(
            id=data["id"],
            title=data.get("title"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            turns=turns,
        )


class ConversationManager:
    """Manages conversation persistence and retrieval."""

    MAX_CONTEXT_TURNS = 5  # Maximum turns to include in context
    MAX_TITLE_LENGTH = 50  # Maximum length for auto-generated titles

    def __init__(self, storage_dir: str = "./sessions/conversations"):
        """Initialize the conversation manager.

        Args:
            storage_dir: Directory for conversation JSON files

        Raises:
            ValueError: If storage_dir is empty or None
        """
        if not storage_dir:
            raise ValueError("storage_dir cannot be empty or None")
        self.storage_dir = anyio.Path(storage_dir)
        self._locks: dict[str, anyio.Lock] = {}
        self._locks_lock = anyio.Lock()
        self._index_lock = anyio.Lock()
        self._index_path = self.storage_dir / "index.json"

    async def _ensure_storage_dir(self) -> None:
        """Ensure the storage directory exists."""
        await self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def _get_conversation_lock(self, conversation_id: str) -> anyio.Lock:
        """Get or create a lock for a specific conversation."""
        async with self._locks_lock:
            if conversation_id not in self._locks:
                self._locks[conversation_id] = anyio.Lock()
            return self._locks[conversation_id]

    def _get_path(self, conversation_id: str) -> anyio.Path:
        """Get the file path for a conversation."""
        return self.storage_dir / f"{conversation_id}.json"

    async def _load_index(self) -> list[dict]:
        """Load the conversation index."""
        if not await self._index_path.exists():
            return []
        try:
            content = await self._index_path.read_text()
            return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    async def _save_index(self, index: list[dict]) -> None:
        """Save the conversation index."""
        await self._index_path.write_text(json.dumps(index, indent=2))

    async def _update_index_entry(self, conversation: Conversation) -> None:
        """Update or add a conversation entry in the index."""
        async with self._index_lock:
            index = await self._load_index()
            
            # Remove existing entry if present
            index = [i for i in index if i["id"] != conversation.id]
            
            # Add new entry
            entry = {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
            }
            index.append(entry)
            
            # Sort by updated_at descending
            index.sort(key=lambda x: x["updated_at"], reverse=True)
            
            await self._save_index(index)

    async def _remove_from_index(self, conversation_id: str) -> None:
        """Remove a conversation from the index."""
        async with self._index_lock:
            index = await self._load_index()
            index = [i for i in index if i["id"] != conversation_id]
            await self._save_index(index)

    async def create(self, title: Optional[str] = None) -> Conversation:
        """Create a new conversation.

        Args:
            title: Optional title for the conversation

        Returns:
            The new Conversation object
        """
        await self._ensure_storage_dir()
        now = datetime.now(timezone.utc).isoformat()
        conversation = Conversation(
            id=str(uuid.uuid4()),
            title=title,
            created_at=now,
            updated_at=now,
            turns=[],
        )
        await self._save(conversation)
        await self._update_index_entry(conversation)
        return conversation

    async def get(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation ID

        Returns:
            The Conversation if found, None otherwise
        """
        path = self._get_path(conversation_id)
        if not await path.exists():
            return None

        try:
            data = json.loads(await path.read_text())
            return Conversation.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    async def add_turn(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        """Add a turn to a conversation.

        Args:
            conversation_id: The conversation ID
            role: "user" or "assistant"
            content: The turn content
            sources: Optional list of source files (for assistant turns)

        Returns:
            The updated Conversation if found, None otherwise
        """
        lock = await self._get_conversation_lock(conversation_id)
        async with lock:
            conversation = await self.get(conversation_id)
            if not conversation:
                return None

            turn = ConversationTurn(
                role=role,
                content=content,
                sources=sources or [],
            )
            conversation.turns.append(turn)
            conversation.updated_at = datetime.now(timezone.utc).isoformat()

            # Auto-generate title from first user message
            if not conversation.title and role == "user":
                max_len = self.MAX_TITLE_LENGTH
                conversation.title = content[:max_len] + ("..." if len(content) > max_len else "")

            await self._save(conversation)
            
            # Update index
            await self._update_index_entry(conversation)
            
            return conversation

    async def list_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """List recent conversations.

        Args:
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of Conversation objects (populated with minimal data from index)
            Note: The objects will have empty turns lists to save IO.
        """
        await self._ensure_storage_dir()

        # If index doesn't exist, try to rebuild it
        if not await self._index_path.exists():
            await self.rebuild_index()

        try:
            index = await self._load_index()
        except Exception:
            # Fallback if index load fails
            return []

        # Pagination
        sliced = index[offset : offset + limit]

        # Convert to lightweight Conversation objects
        # We don't load turns here to keep it O(1) per page
        return [
            Conversation(
                id=item["id"],
                title=item.get("title"),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                turns=[],  # Empty turns for listing
            )
            for item in sliced
        ]

    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if deleted, False if not found
        """
        lock = await self._get_conversation_lock(conversation_id)
        async with lock:
            path = self._get_path(conversation_id)
            
            # Remove from index regardless of file existence (cleanup)
            await self._remove_from_index(conversation_id)
            
            if await path.exists():
                await path.unlink()
                return True
            return False

    async def rebuild_index(self) -> None:
        """Rebuild the index from existing files."""
        async with self._index_lock:
            index = []
            async for path in self.storage_dir.iterdir():
                if path.suffix != ".json" or path.name == "index.json" or path.name.endswith(".tmp"):
                    continue
                try:
                    data = json.loads(await path.read_text())
                    conv = Conversation.from_dict(data)
                    index.append({
                        "id": conv.id,
                        "title": conv.title,
                        "created_at": conv.created_at,
                        "updated_at": conv.updated_at,
                    })
                except (json.JSONDecodeError, KeyError):
                    continue
            
            index.sort(key=lambda x: x["updated_at"], reverse=True)
            await self._save_index(index)

    def get_context_turns(self, conversation: Conversation) -> list[ConversationTurn]:
        """Get recent turns for context window.

        Args:
            conversation: The conversation

        Returns:
            List of recent turns (up to MAX_CONTEXT_TURNS)
        """
        return conversation.turns[-self.MAX_CONTEXT_TURNS :]

    def format_context(self, conversation: Conversation) -> str:
        """Format conversation history for LLM context.

        Args:
            conversation: The conversation

        Returns:
            Formatted conversation history string
        """
        turns = self.get_context_turns(conversation)
        if not turns:
            return ""

        formatted = ["Previous conversation:"]
        for turn in turns:
            role_label = "User" if turn.role == "user" else "Assistant"
            formatted.append(f"\n{role_label}: {turn.content}")

        return "\n".join(formatted)

    async def _save(self, conversation: Conversation) -> None:
        """Save a conversation to disk atomically."""
        path = self._get_path(conversation.id)
        tmp_path = path.with_suffix(".tmp")

        # Write to temp file first
        await self._ensure_storage_dir()
        await tmp_path.write_text(json.dumps(conversation.to_dict(), indent=2))

        # Atomic rename
        await tmp_path.replace(path)
