# src/execution/writer.py
"""
File writing operations with integrity verification.

Supports:
- Creating new files
- Appending to existing files
- Inserting at specific locations
- Backup before modification
- Read-back verification
"""

import hashlib
import shutil
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
from datetime import datetime
import anyio

from ..models.content import ContentBlock, BlockType
from ..models.content_mode import ContentMode
from ..extraction.canonicalize import canonicalize_prose_v1
from ..extraction.integrity import IntegrityError
from .markers import BlockMarker, MarkerParser


@dataclass
class WriteResult:
    """Result of a write operation."""

    success: bool
    verified: bool
    file_path: str
    block_id: str
    action: str
    error: Optional[str] = None
    backup_path: Optional[str] = None


class ContentWriter:
    """Write content blocks to library files with verification."""

    def __init__(
        self,
        library_path: str = "./library",
        backup_enabled: bool = True,
    ):
        self.library_path = Path(library_path)
        self.backup_enabled = backup_enabled
        self.backup_dir = self.library_path / "_backups"

    async def _ensure_directory(self, file_path: Path) -> None:
        """Ensure the parent directory exists."""
        parent = anyio.Path(file_path.parent)
        if not await parent.exists():
            await parent.mkdir(parents=True)

    async def _create_backup(self, file_path: Path) -> Optional[str]:
        """Create a backup of a file before modifying it."""
        if not self.backup_enabled:
            return None

        async_path = anyio.Path(file_path)
        if not await async_path.exists():
            return None

        # Create backup directory
        backup_dir = anyio.Path(self.backup_dir)
        await backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name

        # Copy file to backup
        content = await async_path.read_text()
        await anyio.Path(backup_path).write_text(content)

        return str(backup_path)

    async def _read_file(self, file_path: Path) -> str:
        """Read file content, return empty string if not exists."""
        async_path = anyio.Path(file_path)
        if await async_path.exists():
            return await async_path.read_text()
        return ""

    def _validate_path(self, file_path: Path) -> Path:
        """
        Validate that the path is within the library directory.
        
        Args:
            file_path: The path to validate
            
        Returns:
            The resolved absolute path
            
        Raises:
            ValueError: If path is outside library
        """
        # Resolve to absolute paths
        resolved = file_path.resolve()
        # self.library_path is a Path object from __init__
        # We need its resolved absolute version
        start = self.library_path.resolve()
        
        # Check if resolved path starts with library path
        if not resolved.is_relative_to(start):
            raise ValueError(f"Path traversal detected: {file_path} is outside library {start}")
        
        return resolved

    async def _write_file(self, file_path: Path, content: str) -> None:
        """Write content to file atomically."""
        # Validate path before doing anything
        self._validate_path(file_path)
        
        await self._ensure_directory(file_path)

        async_path = anyio.Path(file_path)
        temp_path = anyio.Path(f"{file_path}.tmp")

        await temp_path.write_text(content)
        await temp_path.rename(async_path)

    def _verify_checksum(
        self,
        block: ContentBlock,
        written_content: str,
        mode: ContentMode,
    ) -> bool:
        """Verify written content matches expected checksums."""
        written_exact = hashlib.sha256(
            written_content.encode("utf-8")
        ).hexdigest()[:16]

        if block.block_type == BlockType.CODE_BLOCK:
            # Code blocks are byte-strict
            return block.checksum_exact == written_exact
        else:
            # Prose uses canonical checksum
            if mode == ContentMode.STRICT:
                written_canonical = hashlib.sha256(
                    canonicalize_prose_v1(written_content).encode("utf-8")
                ).hexdigest()[:16]
                return block.checksum_canonical == written_canonical
            else:
                # REFINEMENT mode: record but don't enforce
                return True

    async def write_block(
        self,
        block: ContentBlock,
        destination: str,
        session_id: str,
        position: str = "append",
        mode: ContentMode = ContentMode.STRICT,
        section: Optional[str] = None,
    ) -> WriteResult:
        """
        Write a block to a destination file with integrity verification.

        Args:
            block: The ContentBlock to write
            destination: Relative path to destination file
            session_id: Current session ID
            position: "append", "create", "insert_before", "insert_after"
            mode: ContentMode (STRICT or REFINEMENT)
            section: Section name for insert operations

        Returns:
            WriteResult with success/verification status
        """
        file_path = self.library_path / destination
        self._validate_path(file_path)

        # Create backup
        backup_path = await self._create_backup(file_path)

        # Prepare content with markers
        marker = BlockMarker.create(
            block_id=block.id,
            source_file=block.source_file,
            session_id=session_id,
            checksum=block.checksum_exact,
        )
        wrapped_content = marker.wrap_content(block.content)

        try:
            if position == "create":
                # Create new file
                await self._write_file(file_path, wrapped_content)

            elif position == "append":
                # Append to file
                existing = await self._read_file(file_path)
                if existing:
                    new_content = f"{existing.rstrip()}\n\n{wrapped_content}"
                else:
                    new_content = wrapped_content
                await self._write_file(file_path, new_content)

            elif position in ("insert_before", "insert_after"):
                if not section:
                    raise ValueError(f"Section required for {position}")

                existing = await self._read_file(file_path)
                new_content = self._insert_at_section(
                    existing, wrapped_content, section, position
                )
                await self._write_file(file_path, new_content)

            else:
                raise ValueError(f"Unknown position: {position}")

            # Read back and verify
            full_content = await self._read_file(file_path)
            written_content = MarkerParser.extract_block_content(
                full_content, block.id
            )

            if written_content is None:
                raise IntegrityError(
                    f"Block {block.id} not found after write"
                )

            verified = self._verify_checksum(block, written_content, mode)

            if not verified and mode == ContentMode.STRICT:
                raise IntegrityError(
                    f"Checksum verification failed for block {block.id}\n"
                    f"Expected: {block.checksum_exact}\n"
                    f"Written content may have been modified."
                )

            # Mark block as verified
            block.integrity_verified = verified
            block.is_executed = True

            return WriteResult(
                success=True,
                verified=verified,
                file_path=str(file_path),
                block_id=block.id,
                action=position,
                backup_path=backup_path,
            )

        except Exception as e:
            return WriteResult(
                success=False,
                verified=False,
                file_path=str(file_path),
                block_id=block.id,
                action=position,
                error=str(e),
                backup_path=backup_path,
            )

    def _insert_at_section(
        self,
        content: str,
        new_content: str,
        section: str,
        position: str,
    ) -> str:
        """Insert content before or after a section."""
        import re

        # Handle empty or whitespace-only section names
        if not section.strip():
            return f"{content.rstrip()}\n\n{new_content}"

        # Find the section header
        pattern = rf'^(##\s+{re.escape(section)}.*)$'
        match = re.search(pattern, content, re.MULTILINE)

        if not match:
            # Section not found, append to end
            return f"{content.rstrip()}\n\n{new_content}"

        if position == "insert_before":
            # Insert before the section header
            return (
                content[:match.start()].rstrip() +
                f"\n\n{new_content}\n\n" +
                content[match.start():]
            )
        else:
            # Insert after the section header line
            return (
                content[:match.end()] +
                f"\n\n{new_content}" +
                content[match.end():]
            )

    async def create_file(
        self,
        destination: str,
        title: str,
        overview: str,
        initial_content: str = "",
    ) -> WriteResult:
        """
        Create a new library file with a title.

        Args:
            destination: Relative path for the new file
            title: File title (H1 header)
            overview: Overview text for the file
            initial_content: Optional initial content

        Returns:
            WriteResult
        """
        file_path = self.library_path / destination
        self._validate_path(file_path)

        async_path = anyio.Path(file_path)
        if await async_path.exists():
            return WriteResult(
                success=False,
                verified=False,
                file_path=str(file_path),
                block_id="",
                action="create_file",
                error=f"File already exists: {destination}",
            )

        content = f"# {title}\n\n## Overview\n{overview}"
        if initial_content:
            content = f"{content}\n\n{initial_content}"
        content = content.strip()

        try:
            await self._write_file(file_path, content)

            return WriteResult(
                success=True,
                verified=True,
                file_path=str(file_path),
                block_id="",
                action="create_file",
            )
        except Exception as e:
            return WriteResult(
                success=False,
                verified=False,
                file_path=str(file_path),
                block_id="",
                action="create_file",
                error=str(e),
            )

    async def create_section(
        self,
        destination: str,
        section_title: str,
    ) -> WriteResult:
        """
        Create a new section in an existing file.

        Args:
            destination: Relative path to the file
            section_title: Section title (H2 header)

        Returns:
            WriteResult
        """
        file_path = self.library_path / destination
        self._validate_path(file_path)

        existing = await self._read_file(file_path)
        if not existing:
            return WriteResult(
                success=False,
                verified=False,
                file_path=str(file_path),
                block_id="",
                action="create_section",
                error=f"File not found: {destination}",
            )

        import re
        if re.search(rf"^##\s+{re.escape(section_title)}\s*$", existing, re.MULTILINE):
            return WriteResult(
                success=True,
                verified=True,
                file_path=str(file_path),
                block_id="",
                action="create_section",
            )

        new_content = f"{existing.rstrip()}\n\n## {section_title}\n"

        try:
            await self._write_file(file_path, new_content)

            return WriteResult(
                success=True,
                verified=True,
                file_path=str(file_path),
                block_id="",
                action="create_section",
            )
        except Exception as e:
            return WriteResult(
                success=False,
                verified=False,
                file_path=str(file_path),
                block_id="",
                action="create_section",
                error=str(e),
            )
