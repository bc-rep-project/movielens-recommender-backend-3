import os
import pymongo
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

def get_mongodb_client() -> pymongo.MongoClient:
    """
    Get MongoDB client connection
    
    Returns:
        MongoDB client instance
    """
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URI environment variable is not set")
    
    client = pymongo.MongoClient(mongodb_uri)
    
    # Test connection
    try:
        client.admin.command("ping")
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    
    return client

def get_database(client: pymongo.MongoClient = None):
    """
    Get MongoDB database object
    
    Args:
        client: Optional existing MongoDB client
        
    Returns:
        MongoDB database instance
    """
    if client is None:
        client = get_mongodb_client()
    
    # Extract database name from connection string
    mongodb_uri = os.getenv("MONGODB_URI")
    db_name = mongodb_uri.split("/")[-1].split("?")[0]
    
    if not db_name:
        db_name = "movielens"  # Default database name
    
    return client[db_name] 