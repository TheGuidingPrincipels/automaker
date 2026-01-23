# src/models/library.py

from pydantic import BaseModel, Field


class LibraryFile(BaseModel):
    """
    Represents a file in the library.
    """

    path: str                         # Relative to library root
    category: str                     # Parent category
    title: str
    sections: list[str] = Field(default_factory=list)
    last_modified: str
    block_count: int = 0              # Number of routed blocks


class LibraryCategory(BaseModel):
    """
    A category (folder) in the library.
    """

    name: str
    path: str                         # Relative to library root
    description: str
    files: list[LibraryFile] = Field(default_factory=list)
    subcategories: list["LibraryCategory"] = Field(default_factory=list)
