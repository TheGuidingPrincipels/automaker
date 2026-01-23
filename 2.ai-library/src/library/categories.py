# src/library/categories.py
"""
Category management for the knowledge library.

Categories are defined in library/_index.yaml and represented as folders.
"""

import yaml
from typing import List, Optional, Dict, Any
from pathlib import Path
import anyio

from ..models.library import LibraryCategory


class CategoryManager:
    """Manage library categories."""

    def __init__(self, library_path: str = "./library"):
        self.library_path = Path(library_path)
        self.index_file = self.library_path / "_index.yaml"

    async def load_categories(self) -> List[LibraryCategory]:
        """
        Load categories from the index file.

        Returns:
            List of LibraryCategory objects
        """
        index_path = anyio.Path(self.index_file)

        if not await index_path.exists():
            return []

        text = await index_path.read_text()
        data = yaml.safe_load(text) or {}

        categories = []
        for cat_data in data.get("categories", []):
            categories.append(self._parse_category(cat_data))

        return categories

    def _parse_category(self, data: Dict[str, Any], parent_path: str = "") -> LibraryCategory:
        """Parse a category from YAML data."""
        name = data.get("name", "unnamed")
        path = data.get("path", name)

        if parent_path:
            full_path = f"{parent_path}/{path}"
        else:
            full_path = path

        subcategories = []
        for sub_data in data.get("subcategories", []):
            subcategories.append(self._parse_category(sub_data, full_path))

        return LibraryCategory(
            name=name,
            path=full_path,
            description=data.get("description", ""),
            files=[],  # Populated by scanner
            subcategories=subcategories,
        )

    async def save_categories(self, categories: List[LibraryCategory]) -> None:
        """
        Save categories to the index file.

        Args:
            categories: List of categories to save
        """
        data = {
            "categories": [self._category_to_dict(cat) for cat in categories]
        }

        index_path = anyio.Path(self.index_file)
        await index_path.parent.mkdir(parents=True, exist_ok=True)
        await index_path.write_text(yaml.dump(data, default_flow_style=False))

    def _category_to_dict(self, category: LibraryCategory) -> Dict[str, Any]:
        """Convert a category to YAML-serializable dict."""
        result = {
            "name": category.name,
            "path": category.path.split("/")[-1],  # Just the folder name
            "description": category.description,
        }

        if category.subcategories:
            result["subcategories"] = [
                self._category_to_dict(sub) for sub in category.subcategories
            ]

        return result

    async def create_category(
        self,
        name: str,
        description: str = "",
        parent_path: Optional[str] = None,
    ) -> LibraryCategory:
        """
        Create a new category.

        Args:
            name: Category name
            description: Category description
            parent_path: Parent category path (None for root)

        Returns:
            The created category
        """
        categories = await self.load_categories()

        # Determine path
        path = name.lower().replace(" ", "-")
        if parent_path:
            path = f"{parent_path}/{path}"

        new_category = LibraryCategory(
            name=name,
            path=path,
            description=description,
            files=[],
            subcategories=[],
        )

        # Add to appropriate location
        if parent_path:
            self._add_to_parent(categories, parent_path, new_category)
        else:
            categories.append(new_category)

        await self.save_categories(categories)

        # Create directory
        dir_path = anyio.Path(self.library_path / path)
        await dir_path.mkdir(parents=True, exist_ok=True)

        return new_category

    def _add_to_parent(
        self,
        categories: List[LibraryCategory],
        parent_path: str,
        new_category: LibraryCategory,
    ) -> bool:
        """Add a category to its parent."""
        for cat in categories:
            if cat.path == parent_path:
                cat.subcategories.append(new_category)
                return True
            if self._add_to_parent(cat.subcategories, parent_path, new_category):
                return True
        return False

    async def get_category(self, path: str) -> Optional[LibraryCategory]:
        """
        Get a category by path.

        Args:
            path: Category path

        Returns:
            The category or None if not found
        """
        categories = await self.load_categories()
        return self._find_category(categories, path)

    def _find_category(
        self, categories: List[LibraryCategory], path: str
    ) -> Optional[LibraryCategory]:
        """Find a category by path."""
        for cat in categories:
            if cat.path == path:
                return cat
            found = self._find_category(cat.subcategories, path)
            if found:
                return found
        return None

    async def list_all_paths(self) -> List[str]:
        """
        Get all category paths.

        Returns:
            List of category paths
        """
        categories = await self.load_categories()
        paths = []
        self._collect_paths(categories, paths)
        return paths

    def _collect_paths(
        self, categories: List[LibraryCategory], paths: List[str]
    ) -> None:
        """Recursively collect category paths."""
        for cat in categories:
            paths.append(cat.path)
            self._collect_paths(cat.subcategories, paths)
