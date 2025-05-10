import os
import httpx
import re
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
from ..core.config import settings

class TMDBService:
    """Service for The Movie Database (TMDB) API integration"""
    
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY")
        self.base_url = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3")
        self.image_base_url = os.getenv("TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p/w500")
        self.retry_attempts = 3
        self.retry_delay = 1  # Initial retry delay in seconds
        self.rate_limit_delay = 0.25  # 250ms between requests to respect rate limits
        self.last_request_time = 0
    
    async def _wait_for_rate_limit(self):
        """Implement rate limiting to avoid hitting TMDb API limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - time_since_last_request
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Make a request to TMDb API with retry logic and rate limiting
        
        Args:
            endpoint: API endpoint path (e.g., /movie/{id})
            params: Additional query parameters
            
        Returns:
            JSON response or None if request failed
        """
        if not self.api_key:
            logger.warning("TMDB API key not configured, skipping API call")
            return None
            
        # Ensure params dict exists
        if params is None:
            params = {}
            
        # Add API key to params
        params["api_key"] = self.api_key
        
        # Full URL
        url = f"{self.base_url}{endpoint}"
        
        # Implement retry logic
        for attempt in range(self.retry_attempts):
            try:
                # Wait for rate limit
                await self._wait_for_rate_limit()
                
                # Make the request
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, params=params)
                    
                    # Handle rate limiting from TMDb
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", self.retry_delay * 2))
                        logger.warning(f"Rate limited by TMDb API. Waiting {retry_after} seconds.")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    # Handle other errors
                    if response.status_code != 200:
                        logger.error(f"TMDb API error: {response.status_code} - {response.text}")
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        return None
                    
                    # Parse JSON response
                    return response.json()
                
            except Exception as e:
                logger.error(f"Error in TMDb API request: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                return None
        
        return None
    
    async def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Search for a movie in TMDB by title and optionally year
        
        Args:
            title: Movie title to search for
            year: Optional release year to narrow search
            
        Returns:
            Dictionary with movie details or None if not found
        """
        try:
            # Clean title for search
            search_title = self._clean_movie_title(title)
            
            # Prepare query parameters
            params = {
                "query": search_title,
                "language": "en-US",
                "include_adult": "false",
                "page": "1"
            }
            
            if year:
                params["year"] = str(year)
            
            # Make the request
            data = await self._make_request("/search/movie", params)
            
            # Check if we have results
            if not data or not data.get("results") or len(data["results"]) == 0:
                logger.debug(f"No TMDb results for {title}")
                return None
            
            # Best match is usually the first result
            return data["results"][0]
                
        except Exception as e:
            logger.error(f"Error searching TMDb for {title}: {str(e)}")
            return None
    
    async def get_movie_by_tmdb_id(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed movie information by TMDb ID
        
        Args:
            tmdb_id: The TMDb ID of the movie
            
        Returns:
            Dictionary with movie details or None if not found
        """
        try:
            return await self._make_request(f"/movie/{tmdb_id}", {
                "language": "en-US",
                "append_to_response": "credits,release_dates,videos"
            })
        except Exception as e:
            logger.error(f"Error getting movie details for TMDb ID {tmdb_id}: {str(e)}")
            return None
    
    async def get_movie_images(self, movie_title: str, year: Optional[int] = None) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        Get poster and backdrop paths for a movie
        
        Args:
            movie_title: Title of the movie
            year: Optional release year
            
        Returns:
            Tuple of (poster_path, backdrop_path, tmdb_id)
        """
        movie_data = await self.search_movie(movie_title, year)
        
        if not movie_data:
            return None, None, None
        
        poster_path = movie_data.get("poster_path")
        backdrop_path = movie_data.get("backdrop_path")
        tmdb_id = movie_data.get("id")
        
        return poster_path, backdrop_path, tmdb_id
    
    async def get_movie_images_by_tmdb_id(self, tmdb_id: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Get poster and backdrop paths by TMDb ID
        
        Args:
            tmdb_id: The TMDb ID of the movie
            
        Returns:
            Tuple of (poster_path, backdrop_path)
        """
        movie_data = await self.get_movie_by_tmdb_id(tmdb_id)
        
        if not movie_data:
            return None, None
        
        poster_path = movie_data.get("poster_path")
        backdrop_path = movie_data.get("backdrop_path")
        
        return poster_path, backdrop_path
    
    def get_full_image_url(self, path: Optional[str], size: str = "w500") -> Optional[str]:
        """
        Get full image URL from relative path
        
        Args:
            path: Relative image path (e.g., /pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg)
            size: Image size (w92, w154, w185, w342, w500, w780, original)
            
        Returns:
            Full image URL or None if path is None
        """
        if not path:
            return None
            
        # Ensure path starts with a slash
        if not path.startswith("/"):
            path = f"/{path}"
            
        # Get base URL and ensure it doesn't end with a slash
        base_url = self.image_base_url
        if base_url.endswith("/"):
            base_url = base_url[:-1]
            
        # Replace size in base URL if it contains a size
        if any(s in base_url for s in ["w92", "w154", "w185", "w342", "w500", "w780", "original"]):
            # Extract base without size
            base_without_size = re.sub(r"/(w\d+|original)$", "", base_url)
            return f"{base_without_size}/{size}{path}"
        
        return f"{base_url}/{path}"
    
    async def enrich_movie_data(self, movie_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich movie data with TMDB information
        
        Args:
            movie_data: Dictionary with movie data
            
        Returns:
            Enhanced movie data
        """
        title = movie_data.get("title", "")
        tmdb_id = movie_data.get("tmdb_id")
        
        # If we already have a TMDb ID, use it to fetch data
        if tmdb_id:
            poster_path, backdrop_path = await self.get_movie_images_by_tmdb_id(tmdb_id)
        else:
            # Extract year from title if available (format: "Movie Title (YYYY)")
            year = None
            year_match = re.search(r"\((\d{4})\)$", title)
            if year_match:
                year = int(year_match.group(1))
                # Clean title by removing year
                clean_title = re.sub(r"\s*\(\d{4}\)$", "", title)
            else:
                clean_title = title
                
            # Get poster and backdrop paths
            poster_path, backdrop_path, tmdb_id = await self.get_movie_images(clean_title, year)
            
        # Add TMDB data to movie
        movie_data["poster_path"] = poster_path
        movie_data["backdrop_path"] = backdrop_path
        movie_data["tmdb_id"] = tmdb_id
        
        # Add full URLs
        movie_data["poster_url"] = self.get_full_image_url(poster_path)
        movie_data["backdrop_url"] = self.get_full_image_url(backdrop_path, "original")
        
        # If we have a TMDb ID, try to get additional data
        if tmdb_id:
            try:
                details = await self.get_movie_by_tmdb_id(tmdb_id)
                if details:
                    # Add overview if not already present
                    if "overview" not in movie_data or not movie_data["overview"]:
                        movie_data["overview"] = details.get("overview")
                    
                    # Add runtime
                    if "runtime" not in movie_data or not movie_data["runtime"]:
                        movie_data["runtime"] = details.get("runtime")
                    
                    # Add release date if we don't have a year
                    if ("year" not in movie_data or not movie_data["year"]) and "release_date" in details:
                        release_date = details.get("release_date", "")
                        if release_date and len(release_date) >= 4:
                            movie_data["year"] = int(release_date[:4])
            except Exception as e:
                logger.error(f"Error enriching movie data with TMDb details: {str(e)}")
        
        return movie_data
    
    def _clean_movie_title(self, title: str) -> str:
        """
        Clean movie title for better searching
        
        Args:
            title: Original movie title
            
        Returns:
            Cleaned title
        """
        # Remove year in parentheses
        title = re.sub(r"\s*\(\d{4}\)$", "", title)
        
        # Remove special editions, etc.
        title = re.sub(r"\s*[:]\s*.*$", "", title)
        
        return title

# Create a singleton instance
tmdb_service = TMDBService() 