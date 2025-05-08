from fastapi import APIRouter
from .endpoints import health, auth, movies, interactions, recommendations

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(movies.router, prefix="/movies", tags=["movies"])
api_router.include_router(interactions.router, prefix="/interactions", tags=["interactions"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"]) 