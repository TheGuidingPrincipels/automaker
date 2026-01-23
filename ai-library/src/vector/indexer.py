# src/vector/indexer.py

from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import yaml
import uuid
from datetime import datetime
import anyio

from .store import QdrantVectorStore
from ..payloads.schema import ContentPayload


class LibraryIndexer:
    """
    Keep vector index in sync with markdown files in the library.
    Supports incremental indexing based on file checksums.
    """

    def __init__(
        self,
        library_path: str,
        vector_store: QdrantVectorStore,
    ):
        self.library_path = Path(library_path)
        self.store = vector_store
        self.index_state_file = self.library_path / ".vector_state.yaml"

    async def index_file(self, file_path: Path) -> int:
        """
        Index a single markdown file. Returns chunk count.
        """
        content = await anyio.Path(file_path).read_text(encoding="utf-8")
        rel_path = str(file_path.relative_to(self.library_path))

        # Extract chunks (paragraphs, sections, etc.)
        chunks = self._extract_chunks_for_indexing(content, rel_path)

        if not chunks:
            return 0

        # Remove old chunks for this file
        await self.store.delete_by_file(rel_path)

        # Add new chunks
        items = [
            (chunk["id"], chunk["content"], chunk["payload"])
            for chunk in chunks
        ]
        await self.store.add_contents_batch(items)

        # Update state
        await self._update_file_state(rel_path, content)

        return len(chunks)

    async def index_all(self, force: bool = False) -> Dict[str, int]:
        """
        Index all markdown files in library.

        Args:
            force: If True, reindex all files regardless of checksums

        Returns:
            Dict mapping file paths to chunk counts
        """
        results = {}
        state = await self._load_state()

        # Run directory traversal in a thread to avoid blocking event loop
        md_files = await anyio.to_thread.run_sync(
            lambda: list(self.library_path.rglob("*.md"))
        )

        for md_file in md_files:
            if md_file.name.startswith("_"):
                continue  # Skip index files

            rel_path = str(md_file.relative_to(self.library_path))

            # Check if file needs indexing
            if not force:
                current_checksum = await self._calculate_checksum(md_file)
                stored_checksum = state.get(rel_path, {}).get("checksum")

                if current_checksum == stored_checksum:
                    continue  # File hasn't changed

            chunk_count = await self.index_file(md_file)
            results[rel_path] = chunk_count

        return results

    async def remove_deleted_files(self) -> List[str]:
        """
        Remove vectors for files that no longer exist.
        Returns list of removed file paths.
        """
        state = await self._load_state()
        removed = []

        for rel_path in list(state.keys()):
            full_path = self.library_path / rel_path
            if not await anyio.Path(full_path).exists():
                await self.store.delete_by_file(rel_path)
                del state[rel_path]
                removed.append(rel_path)

        await self._save_state(state)
        return removed

    async def find_similar(
        self,
        content: str,
        n_results: int = 5,
        exclude_file: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find similar content in the library.

        Args:
            content: Content to find similar matches for
            n_results: Number of results to return
            exclude_file: Optional file to exclude from results

        Returns:
            List of similar chunks with metadata
        """
        results = await self.store.search(content, n_results=n_results + 5)

        # Filter out excluded file if specified
        if exclude_file:
            results = [
                r for r in results
                if r["payload"].file_path != exclude_file
            ]

        return results[:n_results]

    def _extract_chunks_for_indexing(
        self,
        content: str,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract content chunks for vector indexing.

        Chunks are created at section/paragraph boundaries to maintain
        semantic coherence. Target chunk size: 512-2048 tokens.
        """
        chunks = []
        chunk_index = 0
        current_section = ""

        lines = content.split("\n")
        current_chunk = []

        for i, line in enumerate(lines):
            # Detect section headers
            if line.startswith("#"):
                # Save previous chunk if exists
                if current_chunk:
                    chunk_text = "\n".join(current_chunk).strip()
                    if len(chunk_text) > 50:  # Minimum chunk size
                        chunk_id = str(uuid.uuid4())
                        content_hash = hashlib.md5(chunk_text.encode()).hexdigest()

                        payload = ContentPayload.create_basic(
                            content_id=chunk_id,
                            file_path=file_path,
                            section=current_section,
                            chunk_index=chunk_index,
                            content_hash=content_hash,
                            source_file=file_path,
                        )

                        chunks.append({
                            "id": chunk_id,
                            "content": chunk_text,
                            "payload": payload,
                        })
                        chunk_index += 1

                # Start new section
                current_section = line.lstrip("#").strip()
                current_chunk = [line]

            # Detect paragraph breaks (double newline)
            elif line.strip() == "" and current_chunk:
                chunk_text = "\n".join(current_chunk).strip()
                if len(chunk_text) > 50:
                    chunk_id = str(uuid.uuid4())
                    content_hash = hashlib.md5(chunk_text.encode()).hexdigest()

                    payload = ContentPayload.create_basic(
                        content_id=chunk_id,
                        file_path=file_path,
                        section=current_section,
                        chunk_index=chunk_index,
                        content_hash=content_hash,
                        source_file=file_path,
                    )

                    chunks.append({
                        "id": chunk_id,
                        "content": chunk_text,
                        "payload": payload,
                    })
                    chunk_index += 1
                    current_chunk = []
            else:
                current_chunk.append(line)

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if len(chunk_text) > 50:
                chunk_id = str(uuid.uuid4())
                content_hash = hashlib.md5(chunk_text.encode()).hexdigest()

                payload = ContentPayload.create_basic(
                    content_id=chunk_id,
                    file_path=file_path,
                    section=current_section,
                    chunk_index=chunk_index,
                    content_hash=content_hash,
                    source_file=file_path,
                )

                chunks.append({
                    "id": chunk_id,
                    "content": chunk_text,
                    "payload": payload,
                })

        # Update chunk_total for all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk["payload"].chunk_total = total

        return chunks

    def extract_chunks(
        self,
        content: str,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """Extract content chunks from markdown text for vector indexing.

        Splits markdown content into semantic chunks at section and paragraph
        boundaries. Each chunk includes metadata for retrieval and hydration.

        Args:
            content: The raw markdown content to parse
            file_path: Relative path to the source file (used in payload metadata)

        Returns:
            List of chunk dictionaries, each containing:
                - id: Unique UUID for the chunk
                - content: The extracted text content
                - payload: ContentPayload with file_path, section, chunk_index,
                          content_hash, and chunk_total metadata
        """
        return self._extract_chunks_for_indexing(content, file_path)

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file content."""
        content = await anyio.Path(file_path).read_bytes()
        return hashlib.md5(content).hexdigest()

    async def _load_state(self) -> Dict[str, Dict]:
        """Load indexing state from file."""
        state_file = anyio.Path(self.index_state_file)
        if not await state_file.exists():
            return {}

        text = await state_file.read_text(encoding="utf-8")
        return yaml.safe_load(text) or {}

    async def _save_state(self, state: Dict[str, Dict]) -> None:
        """Save indexing state to file."""
        state_file = anyio.Path(self.index_state_file)
        text = yaml.safe_dump(state)
        await state_file.write_text(text, encoding="utf-8")

    async def _update_file_state(self, rel_path: str, content: str) -> None:
        """Update state for a single file."""
        state = await self._load_state()
        state[rel_path] = {
            "checksum": hashlib.md5(content.encode()).hexdigest(),
            "indexed_at": datetime.now().isoformat(),
        }
        await self._save_state(state)
