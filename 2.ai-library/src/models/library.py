# src/models/library.py

from pydantic import BaseModel, Field
from typing import Optional


class LibraryFile(BaseModel):
    """
    Represents a file in the library.
    """

    path: str                         # Relative to library root
    category: str                     # Parent category
    title: str
    overview: Optional[str] = None
    sections: list[str] = Field(default_factory=list)
    last_modified: str
    block_count: int = 0              # Number of routed blocks
    is_valid: bool = True
    validation_errors: list[str] = Field(default_factory=list)


class LibraryCategory(BaseModel):
    """
    A category (folder) in the library.
    """

    name: str
    path: str                         # Relative to library root
    description: str
    files: list[LibraryFile] = Field(default_factory=list)
    subcategories: list["LibraryCategory"] = Field(default_factory=list)
