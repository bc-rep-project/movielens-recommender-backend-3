"""
Database initialization module for ensuring data exists.
"""
import asyncio
import logging
from loguru import logger
from ..data_pipeline.check_db import check_movies_exist
from ..data_pipeline.quick_load import load_sample_data

async def ensure_movies_exist():
    """
    Check if movies exist in the database, if not load sample data.
    
    Returns:
        bool: True if data was loaded, False if data already existed
    """
    if not check_movies_exist():
        logger.info("No movies found in database. Loading sample data...")
        
        # Run the data loading in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, load_sample_data)
        
        if success:
            logger.info("Successfully loaded sample movies into database")
            return True
        else:
            logger.error("Failed to load sample movies into database")
            return False
    
    logger.info("Movies already exist in database")
    return False 