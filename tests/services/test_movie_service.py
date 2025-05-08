import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.movie_service import MovieService, MovieNotFoundError
from app.models.movie import MovieResponse

@pytest.fixture
def movie_service():
    # Create a service with mocked repositories
    service = MovieService()
    service.movie_repo = AsyncMock()
    service.cache_repo = MagicMock()
    return service

@pytest.mark.asyncio
async def test_get_movies_cache_hit(movie_service):
    # Setup
    cached_movies = [{"_id": "123", "title": "Test Movie", "genres": ["Action"]}]
    movie_service.cache_repo.get_json.return_value = cached_movies
    
    # Execute
    result = await movie_service.get_movies(skip=0, limit=10)
    
    # Assert
    assert len(result) == 1
    assert result[0].title == "Test Movie"
    movie_service.cache_repo.get_json.assert_called_once()
    movie_service.movie_repo.get_movies.assert_not_called()

@pytest.mark.asyncio
async def test_get_movies_cache_miss(movie_service):
    # Setup
    movie_service.cache_repo.get_json.return_value = None
    movie_service.movie_repo.get_movies.return_value = [
        {"_id": "123", "title": "Test Movie", "genres": ["Action"]}
    ]
    
    # Execute
    result = await movie_service.get_movies(skip=0, limit=10)
    
    # Assert
    assert len(result) == 1
    assert result[0].title == "Test Movie"
    movie_service.cache_repo.get_json.assert_called_once()
    movie_service.movie_repo.get_movies.assert_called_once_with(skip=0, limit=10)
    movie_service.cache_repo.set_json.assert_called_once() 