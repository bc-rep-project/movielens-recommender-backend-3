from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Dict, Any, Optional
from ...services.movie_service import movie_service
from ...models.movie import MovieResponse
from ..deps import get_optional_user_id
import json

router = APIRouter()


@router.get("")
async def get_movies(
    skip: int = Query(0, ge=0, description="Number of movies to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of movies to return"),
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Get a paginated list of movies
    """
    try:
        print("Fetching movies from movie_service...")
        # Optional: log that we have a user ID if available
        movies = await movie_service.get_movies(skip=skip, limit=limit)
        print(f"Movies returned: {len(movies)}")
        return movies
    except Exception as e:
        # Return an empty list if we encounter errors (like DB not initialized)
        print(f"Error in get_movies: {str(e)}")
        return []


@router.get("/search")
async def search_movies(
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of movies to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of movies to return")
):
    """
    Search for movies by title
    """
    try:
        movies = await movie_service.search_movies(query=query, skip=skip, limit=limit)
        return movies
    except Exception as e:
        # Return an empty list if we encounter errors
        return []


@router.get("/{movie_id}")
async def get_movie(
    movie_id: str = Path(..., description="The ID of the movie to get")
):
    """
    Get a specific movie by ID
    """
    try:
        movie = await movie_service.get_movie_by_id(movie_id)
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        return movie
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving movie: {str(e)}") 