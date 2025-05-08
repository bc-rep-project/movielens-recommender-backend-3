import pytest
from httpx import AsyncClient
import json

@pytest.mark.asyncio
async def test_health_endpoint(test_client: AsyncClient, mock_mongo_db, mock_redis):
    # Setup: Configure mocks to respond appropriately
    mock_mongo_db.command.return_value = {"ok": 1.0}
    mock_redis.ping.return_value = True
    
    # Execute
    response = await test_client.get("/api/health")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["dependencies"]["mongodb"]["status"] == "ok"
    assert data["dependencies"]["redis"]["status"] == "ok"
    assert "response_time_ms" in data 