from typing import List, Dict, Any, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import redis
from loguru import logger
from ..core.database import get_database, get_redis
from ..models.movie import MovieCreate, MovieInDB, MovieResponse
from ..core.config import settings
import json
from ..data_access.mongo_client import MovieRepository
from ..data_access.redis_client import CacheRepository
import os


class MovieNotFoundError(Exception):
    """Exception raised when a movie is not found"""
    pass


class MovieService:
    def __init__(self):
        self.movie_repo = MovieRepository()
        self.cache_repo = CacheRepository()
        self.image_base_url = os.getenv("TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p/w500")
    
    def _get_full_poster_url(self, poster_path: Optional[str]) -> Optional[str]:
        """Create a full poster URL from a relative path"""
        if not poster_path:
            return None
        return f"{self.image_base_url}{poster_path}"
    
    def _get_full_backdrop_url(self, backdrop_path: Optional[str]) -> Optional[str]:
        """Create a full backdrop URL from a relative path"""
        if not backdrop_path:
            return None
        return f"{self.image_base_url}{backdrop_path}".replace("w500", "original")
    
    async def get_movies(self, skip: int = 0, limit: int = 20) -> List[MovieResponse]:
        """
        Get a paginated list of movies
        
        Args:
            skip: Number of movies to skip (pagination offset)
            limit: Maximum number of movies to return
            
        Returns:
            List of movies
        """
        try:
            print(f"MovieService.get_movies called with skip={skip}, limit={limit}")
            # Try to get from cache first
            cache_key = f"movies:list:{skip}:{limit}"
            cached_data = self.cache_repo.get_json(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for {cache_key}")
                return [MovieResponse(**movie) for movie in cached_data]
            
            # If not in cache, query repository
            print("Getting movies from repository...")
            movies_data = await self.movie_repo.get_movies(skip=skip, limit=limit)
            print(f"Repository returned {len(movies_data)} movies")
            
            if len(movies_data) > 0:
                print(f"Sample movie: {movies_data[0]}")
            
            # Convert ObjectId to string for _id
            movies = []
            for movie in movies_data:
                try:
                    # Properly map _id to id for MovieResponse
                    movie_dict = {
                        "id": str(movie["_id"]),  # Map _id to id
                        "title": movie["title"],
                        "genres": movie["genres"],
                        "year": movie.get("year"),
                        "poster_path": movie.get("poster_path"),
                        "backdrop_path": movie.get("backdrop_path"),
                        "tmdb_id": movie.get("tmdb_id"),
                        "poster_url": self._get_full_poster_url(movie.get("poster_path")),
                        "backdrop_url": self._get_full_backdrop_url(movie.get("backdrop_path"))
                    }
                    print(f"Creating MovieResponse for movie: {movie['title']} with id: {movie_dict['id']}")
                    movie_response = MovieResponse(**movie_dict)
                    movies.append(movie_response)
                except Exception as e:
                    print(f"Error creating MovieResponse: {str(e)}, movie data: {movie}")
            
            # Cache the result
            if movies:
                self.cache_repo.set_json(
                    cache_key,
                    [movie.dict() for movie in movies],
                    settings.MOVIE_CACHE_TTL if hasattr(settings, "MOVIE_CACHE_TTL") else 3600
                )
            
            print(f"Returning {len(movies)} movies")
            return movies
        
        except Exception as e:
            logger.error(f"Error getting movies: {str(e)}")
            print(f"Error in MovieService.get_movies: {str(e)}")
            # Return empty list on error
            return []
    
    async def get_movie_by_id(self, movie_id: str) -> Optional[MovieResponse]:
        """
        Get a specific movie by ID
        
        Args:
            movie_id: The ID of the movie to get
            
        Returns:
            Movie object if found, None otherwise
            
        Raises:
            MovieNotFoundError: When the movie is not found
            ValueError: When the movie_id format is invalid
        """
        try:
            # Try to get from cache first
            cache_key = f"movies:id:{movie_id}"
            cached_data = self.cache_repo.get_json(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for {cache_key}")
                return MovieResponse(**cached_data)
            
            # If not in cache, query repository
            movie = await self.movie_repo.get_by_id(movie_id)
            
            if not movie:
                raise MovieNotFoundError(f"Movie with ID {movie_id} not found")
            
            # Properly map _id to id for MovieResponse   
            movie_dict = {
                "id": str(movie["_id"]),  # Map _id to id
                "title": movie["title"],
                "genres": movie["genres"],
                "year": movie.get("year"),
                "poster_path": movie.get("poster_path"),
                "backdrop_path": movie.get("backdrop_path"),
                "tmdb_id": movie.get("tmdb_id"),
                "poster_url": self._get_full_poster_url(movie.get("poster_path")),
                "backdrop_url": self._get_full_backdrop_url(movie.get("backdrop_path"))
            }
            
            movie_response = MovieResponse(**movie_dict)
            
            # Cache the result
            self.cache_repo.set_json(
                cache_key,
                movie_response.dict(),
                settings.MOVIE_CACHE_TTL if hasattr(settings, "MOVIE_CACHE_TTL") else 3600
            )
            
            return movie_response
        
        except MovieNotFoundError:
            # Re-raise MovieNotFoundError
            raise
        except Exception as e:
            logger.error(f"Error getting movie by ID: {str(e)}")
            # Properly propagate value errors related to ObjectId parsing
            if "ObjectId" in str(e) and "not valid" in str(e):
                raise ValueError(f"Invalid movie ID format: {str(e)}")
            return None

    async def search_movies(self, query: str, skip: int = 0, limit: int = 20) -> List[MovieResponse]:
        """
        Search for movies by title
        
        Args:
            query: Search query string
            skip: Number of movies to skip (pagination offset)
            limit: Maximum number of movies to return
            
        Returns:
            List of matching movies
        """
        try:
            # Try to get from cache first (lowercase query for case insensitivity)
            cache_key = f"movies:search:{query.lower()}:{skip}:{limit}"
            cached_data = self.cache_repo.get_json(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for {cache_key}")
                return [MovieResponse(**movie) for movie in cached_data]
            
            # If not in cache, query repository
            movies_data = await self.movie_repo.search_movies(query, skip, limit)
            
            movies = []
            for movie in movies_data:
                try:
                    # Properly map _id to id for MovieResponse
                    movie_dict = {
                        "id": str(movie["_id"]),  # Map _id to id
                        "title": movie["title"],
                        "genres": movie["genres"],
                        "year": movie.get("year"),
                        "poster_path": movie.get("poster_path"),
                        "backdrop_path": movie.get("backdrop_path"),
                        "tmdb_id": movie.get("tmdb_id"),
                        "poster_url": self._get_full_poster_url(movie.get("poster_path")),
                        "backdrop_url": self._get_full_backdrop_url(movie.get("backdrop_path"))
                    }
                    movie_response = MovieResponse(**movie_dict)
                    movies.append(movie_response)
                except Exception as e:
                    print(f"Error creating MovieResponse during search: {str(e)}")
            
            # Cache the result
            if movies:
                self.cache_repo.set_json(
                    cache_key,
                    [movie.dict() for movie in movies],
                    60 * 60  # 1 hour TTL
                )
            
            return movies
        
        except Exception as e:
            logger.error(f"Error searching movies: {str(e)}")
            # Return empty list on error
            return []

# Create a singleton instance
movie_service = MovieService()


async def get_movie_embedding(movie_id: str) -> Optional[List[float]]:
    """
    Get the embedding vector for a movie
    """
    db = get_database()
    
    try:
        result = await db.movies.find_one(
            {"_id": ObjectId(movie_id)},
            {"embedding": 1}
        )
        
        if result and "embedding" in result:
            return result["embedding"]
        return None
    except Exception as e:
        logger.error(f"Error retrieving movie embedding for {movie_id}: {e}")
        return None 