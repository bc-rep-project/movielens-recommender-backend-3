from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
from loguru import logger
from contextlib import asynccontextmanager

from .api.api import api_router
from .core.config import settings
from .core.database import connect_to_mongodb, close_mongodb_connection, init_redis
from .core.init_db import ensure_movies_exist
import uvicorn

# Define lifespan for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections, etc.
    logger.info("Starting up MovieLens Recommender API")
    await connect_to_mongodb()
    await init_redis()
    
    # Initialize database if needed
    logger.info("Checking if movie data exists in database")
    data_loaded = await ensure_movies_exist()
    if data_loaded:
        logger.info("Sample movie data has been loaded")
    else:
        logger.info("Using existing movie data")
    
    yield
    
    # Shutdown: Close connections, etc.
    logger.info("Shutting down MovieLens Recommender API")
    await close_mongodb_connection()

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
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 