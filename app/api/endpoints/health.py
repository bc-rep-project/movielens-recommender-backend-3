from fastapi import APIRouter, Depends, HTTPException
from ...core.database import get_database, get_redis
from motor.motor_asyncio import AsyncIOMotorClient
import redis
from ...core.config import settings
import time
import sys
import platform
import os
from loguru import logger
from typing import Dict, Any

router = APIRouter()

async def check_mongo_connection() -> Dict[str, Any]:
    """Check MongoDB connection status"""
    try:
        db = get_database()
        # Try a simple command to verify connection
        start_time = time.time()
        await db.command("ping")
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        return {
            "status": "ok",
            "response_time_ms": round(response_time, 2)
        }
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def check_redis_connection() -> Dict[str, Any]:
    """Check Redis connection status"""
    try:
        redis_client = get_redis()
        if not redis_client:
            return {"status": "disabled"}
        
        # Try a simple command to verify connection
        start_time = time.time()
        redis_client.ping()
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        return {
            "status": "ok",
            "response_time_ms": round(response_time, 2)
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("")
async def health_check():
    """
    Health check endpoint to verify API and dependencies status
    """
    start_time = time.time()
    
    # Check MongoDB
    mongo_status = await check_mongo_connection()
    
    # Check Redis
    redis_status = check_redis_connection()
    
    # Get system information
    system_info = {
        "python_version": platform.python_version(),
        "platform": f"{platform.system()} {platform.release()}",
        "environment": os.environ.get("ENV", "development"),
        "cloud_run": os.environ.get("CLOUD_RUN", "false")
    }
    
    # Calculate total response time
    response_time = (time.time() - start_time) * 1000  # Convert to ms
    
    return {
        "status": "ok" if mongo_status["status"] == "ok" else "degraded",
        "version": settings.API_VERSION,
        "timestamp": time.time(),
        "environment": system_info["environment"],
        "dependencies": {
            "mongodb": mongo_status,
            "redis": redis_status
        },
        "system": system_info,
        "response_time_ms": round(response_time, 2)
    } 