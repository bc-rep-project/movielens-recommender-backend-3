from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time
from loguru import logger
from contextlib import asynccontextmanager
import os
import sys
import traceback

from .api.api import api_router
from .core.config import settings
from .core.database import connect_to_mongodb, close_mongodb_connection, init_redis
import uvicorn

# Set up more verbose logging for cloud environment
if os.environ.get('ENV') == 'production' or os.environ.get('CLOUD_RUN'):
    logger.info("Running in production/cloud environment - configuring enhanced logging")
    import logging
    logger.remove()
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    logger.add(sys.stdout, format="{time} {level} {message}", level="ERROR")
    # Make sure all standard library logs are visible
    logging.getLogger().setLevel(logging.INFO)

# Define lifespan for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections, etc.
    logger.info("Starting up MovieLens Recommender API")
    try:
        await connect_to_mongodb()
        logger.info("MongoDB connection established")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # Log detailed traceback but continue - we don't want to prevent app startup
        logger.error(traceback.format_exc())
        
    try:
        await init_redis()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        logger.error(traceback.format_exc())
    
    logger.info("Application startup complete")
    yield
    
    # Shutdown: Close connections, etc.
    logger.info("Shutting down MovieLens Recommender API")
    try:
        await close_mongodb_connection()
    except Exception as e:
        logger.error(f"Error during MongoDB disconnect: {e}")

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)

# Simple health check endpoint for Google Cloud Run
@app.get("/_ah/health")
async def cloud_run_health_check():
    """
    Health check endpoint for Google Cloud Run
    """
    return {"status": "ok"}

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint - redirects to API documentation
    """
    return {
        "message": "Welcome to MovieLens Recommender API",
        "documentation": f"{settings.API_PREFIX}/docs"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 