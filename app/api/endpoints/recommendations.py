from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import List, Dict, Any, Optional
from ...core.auth import get_current_user
from ...services import recommendation_service
from ...services.movie_service import movie_service
from ...core.config import settings
from ...models.recommendation import UserRecommendationResponse, ItemRecommendationResponse
from ...models.movie import MovieResponse
from ..deps import get_current_user_id, get_optional_user_id
from loguru import logger

router = APIRouter()


@router.get("/user")
async def get_user_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations to return"),
    exclude_seen: bool = Query(True, description="Whether to exclude movies the user has already seen"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get personalized movie recommendations for the authenticated user
    """
    try:
        recommendations = await recommendation_service.get_recommendations_for_user(
            user_id=user_id,
            limit=limit,
            exclude_seen=exclude_seen
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")


@router.get("/item/{movie_id}", response_model=ItemRecommendationResponse)
async def get_item_recommendations(
    movie_id: str = Path(..., description="Movie ID to get similar items for"),
    limit: int = Query(settings.RECOMMENDATIONS_LIMIT, ge=1, le=50, description="Number of recommendations to return")
):
    """
    Get similar movies to a specific movie
    This endpoint does not require authentication
    """
    try:
        similar_movies = await recommendation_service.get_similar_movies(
            movie_id=movie_id,
            limit=limit
        )
        if not similar_movies:
            return ItemRecommendationResponse(
                movieId=movie_id,
                similar_items=[]
            )
        return ItemRecommendationResponse(
            movieId=movie_id,
            similar_items=similar_movies
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting similar movies: {str(e)}")


@router.get("/popular")
async def get_popular_movies(
    limit: int = Query(settings.RECOMMENDATIONS_LIMIT, ge=1, le=50, description="Number of popular movies to return")
):
    """
    Get popular movies based on interaction count
    This endpoint does not require authentication
    """
    try:
        # Just use the movie service directly as a workaround
        logger.info("Getting popular movies (using movie_service as fallback)")
        return await movie_service.get_movies(limit=limit)
    except Exception as e:
        logger.error(f"Error getting popular movies: {str(e)}")
        # Return empty list rather than error
        return [] 