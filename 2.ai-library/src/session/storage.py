# src/session/storage.py
"""
Session persistence using JSON files.

Provides save/load/list/delete operations for ExtractionSession objects.
"""

import json
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import anyio

from ..models.session import ExtractionSession, SessionPhase
from ..models.content_mode import ContentMode


class SessionStorage:
    """Persist and retrieve extraction sessions as JSON files."""

    def __init__(self, sessions_path: str = "./sessions"):
        self.sessions_path = Path(sessions_path)

    async def ensure_directory(self) -> None:
        """Ensure the sessions directory exists."""
        path = anyio.Path(self.sessions_path)
        if not await path.exists():
            await path.mkdir(parents=True)

    def _session_file(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.sessions_path / f"{session_id}.json"

    async def save(self, session: ExtractionSession) -> None:
        """
        Save a session to disk.

        Args:
            session: The session to save
        """
        await self.ensure_directory()

        # Update timestamp
        session.updated_at = datetime.now()

        # Serialize to JSON
        data = session.model_dump(mode="json")

        # Write atomically (write to temp, then rename)
        file_path = anyio.Path(self._session_file(session.id))
        temp_path = anyio.Path(f"{file_path}.tmp")

        await temp_path.write_text(json.dumps(data, indent=2, default=str))
        await temp_path.rename(file_path)

    async def load(self, session_id: str) -> Optional[ExtractionSession]:
        """
        Load a session from disk.

        Args:
            session_id: The ID of the session to load

        Returns:
            The loaded session, or None if not found
        """
        file_path = anyio.Path(self._session_file(session_id))

        if not await file_path.exists():
            return None

        text = await file_path.read_text()
        data = json.loads(text)

        return ExtractionSession(**data)

    async def list_sessions(self) -> List[str]:
        """
        List all session IDs.

        Returns:
            List of session IDs
        """
        await self.ensure_directory()

        sessions = []
        path = anyio.Path(self.sessions_path)

        async for item in path.iterdir():
            if item.suffix == ".json" and not str(item).endswith(".tmp"):
                sessions.append(item.stem)

        return sorted(sessions)

    async def delete(self, session_id: str) -> bool:
        """
        Delete a session from disk.

        Args:
            session_id: The ID of the session to delete

        Returns:
            True if deleted, False if not found
        """
        file_path = anyio.Path(self._session_file(session_id))

        if await file_path.exists():
            await file_path.unlink()
            return True

        return False

    async def exists(self, session_id: str) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: The ID of the session to check

        Returns:
            True if exists
        """
        file_path = anyio.Path(self._session_file(session_id))
        return await file_path.exists()
