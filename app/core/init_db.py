"""
Database initialization module for ensuring data exists.
"""
import asyncio
import os
from loguru import logger
from ..data_pipeline.check_db import check_movies_exist
from ..data_pipeline.quick_load import load_sample_data

# Constants for configuration
MIN_MOVIES_REQUIRED = 1000  # Require at least 1000 movies
USE_FULL_DATASET = os.getenv("USE_FULL_DATASET", "true").lower() == "true"

async def ensure_movies_exist():
    """
    Check if movies exist in the database, if not load data.
    
    Returns:
        bool: True if data was loaded, False if data already existed
    """
    # Require more movies when using full dataset
    min_count = MIN_MOVIES_REQUIRED if USE_FULL_DATASET else 10
    
    if not check_movies_exist(min_count=min_count):
        # Run data loading in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        
        # Try to load full dataset if configured to do so
        if USE_FULL_DATASET:
            logger.info(f"Less than {min_count} movies found. Attempting to load full dataset...")
            try:
                # Import here to avoid circular dependencies
                from ..data_pipeline.process import process_movielens_data
                success = await loop.run_in_executor(None, process_movielens_data)
                
                if success:
                    logger.info("Successfully loaded full MovieLens dataset")
                    return True
                else:
                    logger.warning("Failed to load full dataset, falling back to sample data")
            except Exception as e:
                logger.error(f"Error loading full dataset: {e}")
                logger.warning("Falling back to sample data")
        else:
            logger.info("No movies found in database. Loading sample data...")
        
        # Fall back to sample data if full dataset loading fails or is disabled
        success = await loop.run_in_executor(None, load_sample_data)
        
        if success:
            logger.info("Successfully loaded sample movies into database")
            return True
        else:
            logger.error("Failed to load sample movies into database")
            return False
    
    logger.info(f"At least {min_count} movies already exist in database")
    return False 