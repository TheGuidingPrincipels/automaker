# src/library/manifest.py
"""
Library manifest generation.

Produces a snapshot of the library structure used to constrain routing decisions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json
import anyio

from ..models.library import LibraryFile, LibraryCategory
from .scanner import LibraryScanner
from .categories import CategoryManager


class LibraryManifest:
    """Generate and manage library manifest snapshots."""

    def __init__(self, library_path: str = "./library"):
        self.library_path = Path(library_path)
        self.scanner = LibraryScanner(str(library_path))
        self.categories = CategoryManager(str(library_path))

    async def generate(self) -> Dict[str, Any]:
        """
        Generate a complete library manifest.

        Returns:
            Dictionary with library structure suitable for routing decisions
        """
        scan_result = await self.scanner.scan()
        category_list = await self.categories.load_categories()

        manifest = {
            "generated_at": datetime.now().isoformat(),
            "library_path": str(self.library_path),
            "summary": {
                "total_categories": self._count_categories(scan_result["categories"]),
                "total_files": scan_result["total_files"],
                "total_sections": scan_result["total_sections"],
            },
            "categories": [
                self._category_to_manifest(cat) for cat in scan_result["categories"]
            ],
            "flat_file_list": await self._get_flat_file_list(),
            "section_index": await self._build_section_index(),
        }

        return manifest

    def _count_categories(self, categories: List[LibraryCategory]) -> int:
        """Count total categories including subcategories."""
        count = len(categories)
        for cat in categories:
            count += self._count_categories(cat.subcategories)
        return count

    def _category_to_manifest(self, category: LibraryCategory) -> Dict[str, Any]:
        """Convert category to manifest format."""
        return {
            "name": category.name,
            "path": category.path,
            "description": category.description,
            "file_count": len(category.files),
            "files": [
                {
                    "path": f.path,
                    "title": f.title,
                    "sections": f.sections,
                    "block_count": f.block_count,
                }
                for f in category.files
            ],
            "subcategories": [
                self._category_to_manifest(sub) for sub in category.subcategories
            ],
        }

    async def _get_flat_file_list(self) -> List[Dict[str, str]]:
        """Get a flat list of all files for quick lookup."""
        files = await self.scanner.list_files()
        return [
            {
                "path": f.path,
                "title": f.title,
                "category": f.category,
            }
            for f in files
        ]

    async def _build_section_index(self) -> Dict[str, List[Dict[str, str]]]:
        """Build an index of sections grouped by file."""
        files = await self.scanner.list_files()
        index = {}

        for f in files:
            if f.sections:
                index[f.path] = [
                    {"title": section, "file": f.path}
                    for section in f.sections
                ]

        return index

    async def save(self, output_path: Optional[str] = None) -> str:
        """
        Save manifest to a JSON file.

        Args:
            output_path: Optional output path (defaults to library/_manifest.json)

        Returns:
            Path to the saved manifest file
        """
        manifest = await self.generate()

        if output_path is None:
            output_path = str(self.library_path / "_manifest.json")

        out_path = anyio.Path(output_path)
        await out_path.write_text(json.dumps(manifest, indent=2))

        return output_path

    async def load(self, manifest_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load a previously saved manifest.

        Args:
            manifest_path: Path to manifest file (defaults to library/_manifest.json)

        Returns:
            Manifest dictionary or None if not found
        """
        if manifest_path is None:
            manifest_path = str(self.library_path / "_manifest.json")

        path = anyio.Path(manifest_path)
        if not await path.exists():
            return None

        text = await path.read_text()
        return json.loads(text)

    async def get_routing_context(self) -> Dict[str, Any]:
        """
        Get a compact manifest suitable for routing decisions.

        This is optimized for use in AI prompts with:
        - Category names and descriptions
        - File titles and their sections
        - No content, just structure

        Returns:
            Compact routing context dictionary
        """
        manifest = await self.generate()

        def simplify_category(cat: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "name": cat["name"],
                "path": cat["path"],
                "files": [
                    {"path": f["path"], "title": f["title"], "sections": f["sections"]}
                    for f in cat["files"]
                ],
                "subcategories": [
                    simplify_category(sub) for sub in cat["subcategories"]
                ],
            }

        return {
            "summary": manifest["summary"],
            "categories": [
                simplify_category(cat) for cat in manifest["categories"]
            ],
        }
