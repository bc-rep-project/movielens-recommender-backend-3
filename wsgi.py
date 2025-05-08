"""
WSGI entry point for Google Cloud Run and other environments
using Gunicorn as the WSGI server.
"""

import os
import sys
from loguru import logger

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure enhanced logging for production
if os.environ.get('ENV') == 'production' or os.environ.get('CLOUD_RUN'):
    import logging
    logger.remove()
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    logger.add(sys.stdout, format="{time} {level} {message}", level="ERROR")
    logging.getLogger().setLevel(logging.INFO)
    
    logger.info("=== Starting application in production mode ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python path: {sys.path}")
    logger.info(f"Working directory: {os.getcwd()}")
    try:
        logger.info(f"Directory contents: {os.listdir('.')}")
        if os.path.exists('./app'):
            logger.info(f"App directory contents: {os.listdir('./app')}")
    except Exception as e:
        logger.error(f"Error listing directory contents: {e}")

# Import the FastAPI application
try:
    from app.main import app as application
    logger.info("Successfully imported FastAPI application")
except ImportError as e:
    logger.error(f"Failed to import application: {e}")
    # Try an alternative import path
    try:
        import app.main
        application = app.main.app
        logger.info("Successfully imported FastAPI application via alternative path")
    except ImportError as e2:
        logger.error(f"Failed alternative import: {e2}")
        raise

# This is what Gunicorn expects
app = application 