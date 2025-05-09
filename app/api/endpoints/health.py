from fastapi import APIRouter, Depends, HTTPException
from ...core.database import get_database, get_redis
from motor.motor_asyncio import AsyncIOMotorClient
import redis
from typing import Dict, Any
import time
import platform
import os
from ...core.config import settings


router = APIRouter()


@router.get("")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint to verify API and dependencies are working.
    Returns status of database connections and basic system info.
    """
    start_time = time.time()
    health_data = {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": time.time(),
        "environment": settings.ENV,
        "dependencies": {
            "mongodb": {"status": "unknown"},
            "redis": {"status": "unknown"}
        },
        "system": {
            "python_version": platform.python_version(),
            "platform": platform.platform()
        }
    }
    
    # Check MongoDB connection
    try:
        db = get_database()
        # Perform a simple operation to verify connection
        await db.command("ping")
        health_data["dependencies"]["mongodb"]["status"] = "ok"
    except Exception as e:
        health_data["dependencies"]["mongodb"]["status"] = "error"
        health_data["dependencies"]["mongodb"]["error"] = str(e)
        health_data["status"] = "degraded"  # MongoDB is critical, mark as degraded
    
    # Check Redis connection
    redis_client = get_redis()
    if redis_client:
        try:
            redis_client.ping()
            health_data["dependencies"]["redis"]["status"] = "ok"
        except Exception as e:
            health_data["dependencies"]["redis"]["status"] = "error"
            health_data["dependencies"]["redis"]["error"] = str(e)
            # Redis is not critical, app can work without it (just slower)
    else:
        health_data["dependencies"]["redis"]["status"] = "disabled"
    
    # Calculate response time
    health_data["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return health_data 