import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router
from app.core.config import settings
from app.core.database import connect_to_mongodb, close_mongodb_connection, init_redis
import logging
from loguru import logger

# Show environment information for debugging
print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")
print(f"App directory contents: {os.listdir('./app') if os.path.exists('./app') else 'app directory not found'}")

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Default to allow all origins in development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_db_client():
    """Initialize database connections on app startup"""
    logger.info("Connecting to MongoDB...")
    await connect_to_mongodb()
    
    logger.info("Initializing Redis...")
    init_redis()
    
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connections on app shutdown"""
    logger.info("Closing MongoDB connection...")
    await close_mongodb_connection()
    
    logger.info("Application shutdown complete")


# Add a root endpoint for basic health checking
@app.get("/")
def read_root():
    return {"status": "ok", "message": "MovieLens Recommender API is running"}


if __name__ == "__main__":
    # For local development only
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 