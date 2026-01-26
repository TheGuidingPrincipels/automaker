# tests/test_library_scanner.py
"""Tests for library scanner overview validation."""

import pytest
import anyio

from src.library.scanner import LibraryScanner


@pytest.mark.asyncio
async def test_library_scanner_extracts_overview(tmp_path):
    """Scanner extracts overview and validates length."""
    library_path = anyio.Path(tmp_path / "library")
    file_path = library_path / "tech" / "valid.md"
    await file_path.parent.mkdir(parents=True, exist_ok=True)

    overview = (
        "This overview explains the file purpose clearly and "
        "meets the required length constraint for validation."
    )
    await file_path.write_text(
        f"# Valid Title\n\n## Overview\n{overview}\n\n## Details\nMore info."
    )

    scanner = LibraryScanner(str(library_path))
    library_file = await scanner.get_file("tech/valid.md")

    assert library_file is not None
    assert library_file.overview == overview
    assert library_file.is_valid is True
    assert library_file.validation_errors == []


@pytest.mark.asyncio
async def test_library_scanner_rejects_short_overview(tmp_path):
    """Scanner flags overview length violations."""
    library_path = anyio.Path(tmp_path / "library")
    file_path = library_path / "tech" / "short.md"
    await file_path.parent.mkdir(parents=True, exist_ok=True)

    await file_path.write_text(
        "# Short Overview\n\n## Overview\nToo short.\n\n## Details\nMore info."
    )

    scanner = LibraryScanner(str(library_path))
    library_file = await scanner.get_file("tech/short.md")

    assert library_file is not None
    assert library_file.is_valid is False
    assert any("Overview must be 50-250 characters" in err for err in library_file.validation_errors)


@pytest.mark.asyncio
async def test_library_scanner_missing_overview(tmp_path):
    """Scanner flags missing overview section."""
    library_path = anyio.Path(tmp_path / "library")
    file_path = library_path / "tech" / "missing_overview.md"
    await file_path.parent.mkdir(parents=True, exist_ok=True)

    await file_path.write_text("# Title Only\n\n## Details\nNo overview here.")

    scanner = LibraryScanner(str(library_path))
    library_file = await scanner.get_file("tech/missing_overview.md")

    assert library_file is not None
    assert library_file.is_valid is False
    assert "Missing ## Overview section" in library_file.validation_errors
