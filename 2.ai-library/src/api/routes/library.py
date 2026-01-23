# src/api/routes/library.py
"""Library browsing routes."""

from typing import Optional
from pathlib import Path
import anyio

from fastapi import APIRouter, HTTPException, status

from ..dependencies import (
    ConfigDep,
    LibraryScannerDep,
    SemanticSearchDep,
)
from ..schemas import (
    LibraryStructureResponse,
    LibraryCategoryResponse,
    LibraryFileResponse,
    LibrarySearchResponse,
    LibrarySearchResult,
    IndexResponse,
    ErrorResponse,
)


router = APIRouter()


# =============================================================================
# Library Structure
# =============================================================================


@router.get("", response_model=LibraryStructureResponse)
async def get_library_structure(scanner: LibraryScannerDep):
    """Get the complete library structure."""
    result = await scanner.scan()

    return LibraryStructureResponse(
        categories=[
            LibraryCategoryResponse.from_category(cat) for cat in result["categories"]
        ],
        total_files=result["total_files"],
        total_sections=result["total_sections"],
    )


@router.get("/categories", response_model=list[LibraryCategoryResponse])
async def get_categories(scanner: LibraryScannerDep):
    """Get top-level categories."""
    result = await scanner.scan()
    return [LibraryCategoryResponse.from_category(cat) for cat in result["categories"]]


@router.get("/files/{file_path:path}", response_model=LibraryFileResponse)
async def get_file(
    file_path: str,
    scanner: LibraryScannerDep,
):
    """Get metadata for a specific file."""
    file = await scanner.get_file(file_path)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
        )

    return LibraryFileResponse.from_file(file)


@router.get("/files/{file_path:path}/content")
async def get_file_content(
    file_path: str,
    scanner: LibraryScannerDep,
    config: ConfigDep,
):
    """Get the content of a library file."""
    # Security check: Prevent path traversal
    try:
        library_root = Path(config.library.path).resolve()
        # Resolve the target path relative to the library root
        target_path = (library_root / file_path).resolve()

        # Ensure the target path is still within the library root
        # This prevents ".." attacks escaping the directory
        if not str(target_path).startswith(str(library_root)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: File outside library root",
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file path: {str(e)}",
        )

    full_path = anyio.Path(target_path)

    if not await full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
        )

    content = await full_path.read_text()
    return {"content": content, "path": file_path}


# =============================================================================
# Library Search
# =============================================================================


@router.get("/search", response_model=LibrarySearchResponse)
async def search_library(
    query: str,
    scanner: LibraryScannerDep,
):
    """Search library sections by text."""
    results = await scanner.search_sections(query)

    return LibrarySearchResponse(
        results=[
            LibrarySearchResult(
                file_path=r["file_path"],
                file_title=r["file_title"],
                section=r["section"],
                category=r["category"],
            )
            for r in results
        ],
        query=query,
        total=len(results),
    )


# =============================================================================
# Indexing
# =============================================================================


@router.post("/index", response_model=IndexResponse)
async def index_library(
    search: SemanticSearchDep,
    force: bool = False,
):
    """Trigger library indexing for semantic search."""
    try:
        result = await search.ensure_indexed(force=force)
        return IndexResponse(
            status=result.get("status", "unknown"),
            files_indexed=result.get("files_indexed", 0),
            details=result.get("details"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {str(e)}",
        )


@router.get("/index/stats")
async def get_index_stats(search: SemanticSearchDep):
    """Get indexing statistics."""
    try:
        stats = await search.get_stats()
        return stats
    except Exception as e:
        return {
            "status": "unavailable",
            "error": str(e),
        }
