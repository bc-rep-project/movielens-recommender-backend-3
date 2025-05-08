import redis
import json
from typing import Any, Optional, Dict, List, Union
from ..core.database import get_redis
from loguru import logger

class CacheRepository:
    """Repository for Redis cache operations"""
    
    def __init__(self):
        pass
    
    def get_redis(self) -> Optional[redis.Redis]:
        """Get Redis client"""
        return get_redis()
    
    def get(self, key: str) -> Optional[str]:
        """Get a value from the cache"""
        try:
            redis_client = self.get_redis()
            if not redis_client:
                return None
            
            value = redis_client.get(key)
            return value.decode('utf-8') if value else None
        except Exception as e:
            logger.error(f"Error in CacheRepository.get: {e}")
            return None
    
    def get_json(self, key: str) -> Optional[Union[Dict, List]]:
        """Get a JSON value from the cache and parse it"""
        try:
            value = self.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error in CacheRepository.get_json: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set a value in the cache with TTL in seconds"""
        try:
            redis_client = self.get_redis()
            if not redis_client:
                return False
            
            result = redis_client.setex(key, ttl, value)
            return bool(result)
        except Exception as e:
            logger.error(f"Error in CacheRepository.set: {e}")
            return False
    
    def set_json(self, key: str, value: Union[Dict, List], ttl: int = 3600) -> bool:
        """Set a JSON value in the cache"""
        try:
            json_str = json.dumps(value)
            return self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Error in CacheRepository.set_json: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache"""
        try:
            redis_client = self.get_redis()
            if not redis_client:
                return False
            
            result = redis_client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error in CacheRepository.delete: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        try:
            redis_client = self.get_redis()
            if not redis_client:
                logger.debug(f"Redis not available, skipping delete_pattern for: {pattern}")
                return 0
            
            # Check if keys method is available (some Redis clients might not support it)
            if not hasattr(redis_client, 'keys'):
                logger.warning("Redis client does not support 'keys' method")
                return 0
                
            try:
                keys = redis_client.keys(pattern)
                if not keys:
                    return 0
                    
                return redis_client.delete(*keys)
            except redis.exceptions.ResponseError as e:
                logger.warning(f"Redis pattern matching error: {e}")
                return 0
        except Exception as e:
            logger.error(f"Error in CacheRepository.delete_pattern: {e}")
            return 0 