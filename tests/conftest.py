import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import redis
from unittest.mock import AsyncMock, MagicMock
import asyncio
from app.main import app
from app.core.database import get_database, get_redis

# Create mock database and redis clients
@pytest.fixture
def mock_mongo_db():
    """Return a mock AsyncIOMotorDatabase."""
    return AsyncMock(spec=AsyncIOMotorDatabase)


@pytest.fixture
def mock_redis():
    """Return a mock Redis client."""
    return MagicMock(spec=redis.Redis)


# Override get_database and get_redis dependencies
@pytest.fixture
def override_get_database(mock_mongo_db):
    """Replace get_database with a function that returns the mock database."""
    async def _get_database():
        return mock_mongo_db
    
    app.dependency_overrides[get_database] = _get_database
    yield
    app.dependency_overrides.pop(get_database)


@pytest.fixture
def override_get_redis(mock_redis):
    """Replace get_redis with a function that returns the mock Redis client."""
    def _get_redis():
        return mock_redis
    
    app.dependency_overrides[get_redis] = _get_redis
    yield
    app.dependency_overrides.pop(get_redis)


# Test client
@pytest.fixture
async def test_client(override_get_database, override_get_redis):
    """Return an AsyncClient for testing the API."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client 