# src/session/storage.py
"""
Session persistence using JSON files.

Provides save/load/list/delete operations for ExtractionSession objects.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import anyio

from ..models.session import ExtractionSession, SessionPhase
from ..models.content_mode import ContentMode


logger = logging.getLogger(__name__)


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

    def _uploads_root(self) -> Path:
        """Get the root path for session uploads."""
        return self.sessions_path / "uploads"

    def upload_dir(self, session_id: str) -> Path:
        """Get the directory for a session's uploaded files."""
        return self._uploads_root() / session_id

    def upload_path(self, session_id: str, filename: str) -> Path:
        """Get the full path for a session upload."""
        return self.upload_dir(session_id) / filename

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

    async def delete_uploads(self, session: ExtractionSession) -> None:
        """
        Delete persisted uploads for a session if they exist.
        """
        if not session.source:
            return

        upload_root = self._uploads_root().resolve()
        source_path = Path(session.source.file_path).resolve()
        if not source_path.is_relative_to(upload_root):
            return

        async_path = anyio.Path(source_path)
        if not await async_path.exists():
            logger.warning(
                "Upload file missing for session %s: %s",
                session.id,
                source_path,
            )
        else:
            await async_path.unlink()

        session_dir = anyio.Path(self.upload_dir(session.id))
        if await session_dir.exists():
            has_items = False
            async for _ in session_dir.iterdir():
                has_items = True
                break
            if not has_items:
                await session_dir.rmdir()

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
