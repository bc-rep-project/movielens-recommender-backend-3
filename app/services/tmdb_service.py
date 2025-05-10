import os
import httpx
import re
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
from ..core.config import settings

class TMDBService:
    """Service for The Movie Database (TMDB) API integration"""
    
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY")
        self.base_url = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3")
        self.image_base_url = os.getenv("TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p/w500")
    
    async def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Search for a movie in TMDB by title and optionally year
        
        Args:
            title: Movie title to search for
            year: Optional release year to narrow search
            
        Returns:
            Dictionary with movie details or None if not found
        """
        if not self.api_key:
            logger.warning("TMDB API key not configured, skipping search")
            return None
        
        try:
            # Clean title for search
            search_title = self._clean_movie_title(title)
            
            # Prepare query parameters
            params = {
                "api_key": self.api_key,
                "query": search_title,
                "language": "en-US",
                "include_adult": "false",
                "page": "1"
            }
            
            if year:
                params["year"] = str(year)
            
            # Make the request
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search/movie",
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"TMDB API error: {response.status_code} - {response.text}")
                    return None
                
                data = response.json()
                
                # Check if we have results
                if not data.get("results") or len(data["results"]) == 0:
                    logger.debug(f"No TMDB results for {title}")
                    return None
                
                # Best match is usually the first result
                # But we could implement better matching here if needed
                return data["results"][0]
                
        except Exception as e:
            logger.error(f"Error searching TMDB for {title}: {str(e)}")
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
    
    async def enrich_movie_data(self, movie_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich movie data with TMDB information
        
        Args:
            movie_data: Dictionary with movie data
            
        Returns:
            Enhanced movie data
        """
        title = movie_data.get("title", "")
        
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