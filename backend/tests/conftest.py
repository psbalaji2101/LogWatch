"""pytest fixtures"""

import pytest
import asyncio
from httpx import AsyncClient

from app.main import app
from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client():
    """Create async HTTP client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_log_lines():
    """Sample log lines for testing"""
    return [
        '{"timestamp": "2025-10-20T14:30:00Z", "level": "ERROR", "message": "Test error"}',
        '192.168.1.1 - - [20/Oct/2025:14:30:00 +0000] "GET /api HTTP/1.1" 200 1234',
        '[2025-10-20 14:30:00] INFO: Application started',
        '2025-10-20T14:30:00Z,user_login,user123,success'
    ]
