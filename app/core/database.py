from motor.motor_asyncio import AsyncIOMotorClient
import redis
from loguru import logger
from .config import settings
import os


# MongoDB
mongodb_client: AsyncIOMotorClient = None


async def connect_to_mongodb():
    """Connect to MongoDB Atlas"""
    global mongodb_client
    try:
        mongodb_client = AsyncIOMotorClient(settings.MONGODB_URI)
        logger.info("Connected to MongoDB Atlas")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongodb_connection():
    """Close MongoDB connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        logger.info("MongoDB connection closed")


def get_database():
    """Get MongoDB database instance"""
    if not mongodb_client:
        raise Exception("MongoDB client not initialized")
    # Extract database name from connection URI - assumes standard MongoDB URI format
    db_name = settings.MONGODB_DB_NAME or settings.MONGODB_URI.split("/")[-1].split("?")[0]
    return mongodb_client[db_name]


# Redis
_redis_client = None
_redis_connection_attempted = False  # Flag to track if we've already tried to connect


async def init_redis():
    """Initialize Redis connection."""
    global _redis_client, _redis_connection_attempted
    
    # Don't attempt connection more than once
    if _redis_connection_attempted:
        return
    
    _redis_connection_attempted = True
    
    try:
        # For development or testing, use a local Redis if available
        if settings.ENV in ("development", "testing"):
            try:
                # Try to connect to local Redis first
                test_client = redis.Redis(
                    host="localhost",
                    port=6379,
                    db=0,
                    socket_connect_timeout=2.0,  # Short timeout for quick fail
                    decode_responses=False
                )
                test_client.ping()  # Test connection
                
                _redis_client = test_client
                logger.info("Connected to local Redis")
                return
            except Exception as local_error:
                logger.warning(f"Could not connect to local Redis: {local_error}, will try configured Redis")
        
        # If individual Redis settings are provided, use those
        if settings.REDIS_HOST:
            try:
                _redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT or 6379,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB or 0,
                    decode_responses=False,
                    socket_connect_timeout=5.0  # Timeout after 5 seconds
                )
                _redis_client.ping()  # Test connection
                logger.info("Connected to Redis via host/port settings")
                return
            except Exception as redis_config_error:
                logger.warning(f"Failed to connect to Redis with configured settings: {redis_config_error}")
                _redis_client = None
                
        # Otherwise, try to use REDIS_URL if available
        elif os.getenv("REDIS_URL"):
            try:
                _redis_client = redis.from_url(
                    os.getenv("REDIS_URL"),
                    decode_responses=False,
                    socket_connect_timeout=5.0  # Timeout after 5 seconds
                )
                _redis_client.ping()  # Test connection
                logger.info("Connected to Redis via URL")
                return
            except Exception as redis_url_error:
                logger.warning(f"Failed to connect to Redis with URL: {redis_url_error}")
                _redis_client = None
        else:
            logger.warning("Redis configuration not found, caching will be disabled")
            _redis_client = None
            
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        _redis_client = None
        logger.warning("Redis will be disabled for this session")


def get_redis():
    """Get Redis client instance"""
    global _redis_client
    return _redis_client 


def init_app(app):
    """Initialize app with database connections"""
    
    @app.on_event("startup")
    async def startup_db_client():
        await connect_to_mongodb()
        await init_redis()
        
        # Debug log to see if CORS origins are being properly loaded
        logger.debug(f"Configured CORS Origins: {settings.CORS_ORIGINS}")
        
    @app.on_event("shutdown")
    async def shutdown_db_client():
        await close_mongodb_connection() 