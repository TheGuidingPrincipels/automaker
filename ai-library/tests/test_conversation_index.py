
import json
import pytest
from src.query.conversation import ConversationManager, Conversation
import anyio

@pytest.fixture
async def temp_storage(tmp_path):
    """Create a temp storage directory."""
    path = tmp_path / "conversations"
    await anyio.Path(path).mkdir()
    return str(path)

@pytest.mark.asyncio
async def test_conversation_index_creation(temp_storage):
    """Test that creating a conversation adds it to the index."""
    manager = ConversationManager(temp_storage)
    conv = await manager.create(title="Test Chat")
    
    index_path = anyio.Path(temp_storage) / "index.json"
    assert await index_path.exists()
    
    content = json.loads(await index_path.read_text())
    assert len(content) == 1
    assert content[0]["id"] == conv.id
    assert content[0]["title"] == "Test Chat"

@pytest.mark.asyncio
async def test_conversation_list_uses_index(temp_storage):
    """Test that listing conversations reads from index, not files."""
    manager = ConversationManager(temp_storage)
    
    # Create 3 conversations
    for i in range(3):
        await manager.create(title=f"Chat {i}")
        
    # Check index
    index_path = anyio.Path(temp_storage) / "index.json"
    content = json.loads(await index_path.read_text())
    assert len(content) == 3
    
    # List conversations
    listed = await manager.list_conversations()
    assert len(listed) == 3
    assert listed[0].title  # Ensure titles are populated

@pytest.mark.asyncio
async def test_delete_removes_from_index(temp_storage):
    """Test that deleting a conversation removes it from index."""
    manager = ConversationManager(temp_storage)
    conv = await manager.create(title="To Delete")
    
    # Confirm in index
    index_path = anyio.Path(temp_storage) / "index.json"
    content = json.loads(await index_path.read_text())
    assert any(c["id"] == conv.id for c in content)
    
    # Delete
    await manager.delete(conv.id)
    
    # Confirm removed from index
    content = json.loads(await index_path.read_text())
    assert not any(c["id"] == conv.id for c in content)

@pytest.mark.asyncio
async def test_rebuild_index(temp_storage):
    """Test rebuilding index from files."""
    manager = ConversationManager(temp_storage)
    
    # Manually create a file directly, bypassing manager
    import uuid
    from datetime import datetime
    
    conv_id = str(uuid.uuid4())
    conv_data = {
        "id": conv_id,
        "title": "Manual Chat",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "turns": []
    }
    
    path = anyio.Path(temp_storage) / f"{conv_id}.json"
    await path.write_text(json.dumps(conv_data))
    
    # Verify not in index yet (since we bypassed manager)
    # (Actually manager might not have created index.json if we didn't use it yet)
    # So let's initialize manager's index first correctly
    await manager.create("Normal Chat") 
    
    # Now check manual chat is missing
    index_path = anyio.Path(temp_storage) / "index.json"
    content = json.loads(await index_path.read_text())
    assert len(content) == 1
    
    # Rebuild
    await manager.rebuild_index()
    
    # Check both present
    content = json.loads(await index_path.read_text())
    assert len(content) == 2
    assert any(c["id"] == conv_id for c in content)
