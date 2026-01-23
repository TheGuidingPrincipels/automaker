# src/library/scanner.py
"""
Library structure scanning.

Scans the library folder for markdown files and extracts metadata.
"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import anyio

from ..models.library import LibraryFile, LibraryCategory


class LibraryScanner:
    """Scan library structure for files and metadata."""

    def __init__(self, library_path: str = "./library"):
        self.library_path = Path(library_path)

    async def scan(self) -> Dict[str, Any]:
        """
        Scan the entire library structure.

        Returns:
            Dictionary with library structure including:
            - categories: List of categories with files
            - total_files: Count of markdown files
            - total_sections: Count of sections across all files
        """
        lib_path = anyio.Path(self.library_path)

        if not await lib_path.exists():
            return {
                "categories": [],
                "total_files": 0,
                "total_sections": 0,
            }

        categories = []
        total_files = 0
        total_sections = 0

        # Scan root-level categories (directories)
        async for item in lib_path.iterdir():
            if await item.is_dir() and not item.name.startswith((".", "_")):
                cat_result = await self._scan_category(item)
                categories.append(cat_result["category"])
                total_files += cat_result["file_count"]
                total_sections += cat_result["section_count"]

        return {
            "categories": categories,
            "total_files": total_files,
            "total_sections": total_sections,
        }

    async def _scan_category(
        self, category_path: anyio.Path, parent_path: str = ""
    ) -> Dict[str, Any]:
        """Scan a single category directory."""
        name = category_path.name
        rel_path = f"{parent_path}/{name}" if parent_path else name

        files = []
        subcategories = []
        file_count = 0
        section_count = 0

        async for item in category_path.iterdir():
            if await item.is_file() and item.suffix == ".md":
                lib_file = await self._scan_file(item, rel_path)
                files.append(lib_file)
                file_count += 1
                section_count += len(lib_file.sections)

            elif await item.is_dir() and not item.name.startswith((".", "_")):
                sub_result = await self._scan_category(item, rel_path)
                subcategories.append(sub_result["category"])
                file_count += sub_result["file_count"]
                section_count += sub_result["section_count"]

        category = LibraryCategory(
            name=name,
            path=rel_path,
            description="",  # Would need to read from _index.yaml
            files=files,
            subcategories=subcategories,
        )

        return {
            "category": category,
            "file_count": file_count,
            "section_count": section_count,
        }

    async def _scan_file(
        self, file_path: anyio.Path, category_path: str
    ) -> LibraryFile:
        """Scan a single markdown file."""
        content = await file_path.read_text()
        stat = await file_path.stat()

        # Extract title (first H1 or filename)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path.stem

        # Extract sections (H2 headers)
        sections = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)

        # Count blocks (rough estimate based on paragraphs)
        blocks = len(re.split(r'\n\n+', content.strip()))

        rel_path = f"{category_path}/{file_path.name}"

        return LibraryFile(
            path=rel_path,
            category=category_path,
            title=title,
            sections=sections,
            last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            block_count=blocks,
        )

    async def get_file(self, file_path: str) -> Optional[LibraryFile]:
        """
        Get metadata for a specific file.

        Args:
            file_path: Relative path to the file

        Returns:
            LibraryFile or None if not found
        """
        full_path = anyio.Path(self.library_path / file_path)

        if not await full_path.exists():
            return None

        # Extract category from path
        parts = file_path.rsplit("/", 1)
        category_path = parts[0] if len(parts) > 1 else ""

        return await self._scan_file(full_path, category_path)

    async def list_files(self, category: Optional[str] = None) -> List[LibraryFile]:
        """
        List all files, optionally filtered by category.

        Args:
            category: Category path to filter by (optional)

        Returns:
            List of LibraryFile objects
        """
        result = await self.scan()
        files = []

        def collect_files(categories: List[LibraryCategory]):
            for cat in categories:
                if category is None or cat.path.startswith(category):
                    files.extend(cat.files)
                collect_files(cat.subcategories)

        collect_files(result["categories"])
        return files

    async def search_sections(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for sections matching a query.

        Args:
            query: Search query (case-insensitive substring match)

        Returns:
            List of matching sections with file info
        """
        files = await self.list_files()
        results = []
        query_lower = query.lower()

        for file in files:
            for section in file.sections:
                if query_lower in section.lower():
                    results.append({
                        "file_path": file.path,
                        "file_title": file.title,
                        "section": section,
                        "category": file.category,
                    })

        return results
