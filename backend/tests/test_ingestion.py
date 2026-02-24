"""Test ingestion components"""

import pytest
import tempfile
from pathlib import Path

from app.ingestion.checkpoint import CheckpointManager
from app.ingestion.worker import IngestionWorker


def test_checkpoint_manager():
    """Test checkpoint manager"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        db_path = f.name
    
    manager = CheckpointManager(db_path)
    
    # Set checkpoint
    manager.set_checkpoint("/test/file.log", 1234, 1234567890.0)
    
    # Get checkpoint
    offset = manager.get_checkpoint("/test/file.log")
    assert offset == 1234
    
    # Clear checkpoint
    manager.clear_checkpoint("/test/file.log")
    offset = manager.get_checkpoint("/test/file.log")
    assert offset is None


@pytest.mark.asyncio
async def test_ingestion_worker(sample_log_lines):
    """Test ingestion worker"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        for line in sample_log_lines:
            f.write(line + '\n')
        temp_path = f.name
    
    worker = IngestionWorker()
    
    # Mock checkpoint manager to avoid file creation
    worker.checkpoint_manager.set_checkpoint = lambda *args: None
    
    # Test parsing
    for line in sample_log_lines:
        parsed = worker._parse_line(line)
        assert 'timestamp' in parsed
        assert 'fields' in parsed
        assert 'tokens' in parsed
    
    # Cleanup
    Path(temp_path).unlink()
