
import pytest
from pathlib import Path
from src.execution.writer import ContentWriter, WriteResult
import anyio
import os

@pytest.mark.asyncio
async def test_path_traversal_prevention(tmp_path):
    """
    Test that ContentWriter prevents writing files outside the library directory.
    """
    # Setup library dir and a target outside it
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    
    sensitive_file = tmp_path / "sensitive.txt"
    sensitive_file.write_text("secret_data")
    
    writer = ContentWriter(library_path=str(library_dir))
    
    # Attempt to overwrite the sensitive file using traversal
    # construct path relative to library_dir that points to sensitive_file
    # e.g. ../sensitive.txt
    traversal_path = "../sensitive.txt"
    
    # This should raise ValueError with the fix. 
    # Without the fix, it might succeed (and overwrite) or fail with permission errors depending on OS/setup.
    # We assert that it raises ValueError or verifies safety.
    
    with pytest.raises(ValueError, match="Path traversal detected"):
        await writer.create_file(
            destination=traversal_path,
            title="Hacked",
            overview="Malicious overwrite",
            initial_content="PWNED"
        )
    
    # Verify the sensitive file was NOT changed
    assert sensitive_file.read_text() == "secret_data"

@pytest.mark.asyncio
async def test_absolute_path_traversal_prevention(tmp_path):
    """Test that providing an absolute path is also rejected if it's outside library."""
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    
    writer = ContentWriter(library_path=str(library_dir))
    
    # Create a path that is definitely outside
    outside_path = tmp_path / "outside.txt"
    
    # Even if we pass an absolute path, it should be treated as relative or rejected
    # In this implementation, we expect it to be rejected if it resolves outside.
    
    with pytest.raises(ValueError, match="Path traversal detected"):
        await writer.create_file(
            destination=str(outside_path), # This might be interpreted as relative if not careful, or absolute
            title="Hacked",
            overview="Malicious input",
        )
