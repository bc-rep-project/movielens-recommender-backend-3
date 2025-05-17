from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId
import numpy as np
from loguru import logger
import os
import pickle
import json
from ..core.database import get_database, get_redis
from ..core.config import settings
from .movie_service import get_movie_embedding
from .interaction_service import get_user_rated_movies, get_user_viewed_movies
from ..data_access.mongo_client import MovieRepository, InteractionRepository
from ..data_access.redis_client import CacheRepository
from ..models.movie import MovieResponse
from ..models.recommendation import RecommendationResponse
from scipy.spatial.distance import cosine
from ..core.exceptions import RecommendationServiceError


# Load environment variables
MODEL_STORAGE_PATH = os.getenv("MODEL_STORAGE_PATH", "/app/models")
MODEL_VERSION = os.getenv("MODEL_VERSION", "v1.0")


class AdvancedRecommendationService:
    def __init__(self):
        self.movie_repo = MovieRepository()
        self.interaction_repo = InteractionRepository()
        self.cache_repo = CacheRepository()
        
        # Initialize model properties
        self.cf_model = None
        self.cf_mappings = None
        self.cb_model = None
        self.hybrid_config = None
        
        # Try to load models
        self.load_models()
    
    def load_models(self):
        """Load trained recommendation models"""
        try:
            # Collaborative filtering model
            cf_model_path = os.path.join(MODEL_STORAGE_PATH, f"cf_model_{MODEL_VERSION}.pkl")
            if os.path.exists(cf_model_path):
                logger.info(f"Loading collaborative filtering model from {cf_model_path}")
                with open(cf_model_path, 'rb') as f:
                    self.cf_model = pickle.load(f)
                    
                # Load mappings
                cf_mappings_path = os.path.join(MODEL_STORAGE_PATH, f"cf_mappings_{MODEL_VERSION}.pkl")
                if os.path.exists(cf_mappings_path):
                    with open(cf_mappings_path, 'rb') as f:
                        self.cf_mappings = pickle.load(f)
            else:
                logger.warning(f"Collaborative filtering model not found at {cf_model_path}")
            
            # Content-based model
            cb_model_path = os.path.join(MODEL_STORAGE_PATH, f"cb_model_{MODEL_VERSION}.pkl")
            if os.path.exists(cb_model_path):
                logger.info(f"Loading content-based model from {cb_model_path}")
                with open(cb_model_path, 'rb') as f:
                    self.cb_model = pickle.load(f)
            else:
                logger.warning(f"Content-based model not found at {cb_model_path}")
            
            # Hybrid configuration
            hybrid_path = os.path.join(MODEL_STORAGE_PATH, f"hybrid_config_{MODEL_VERSION}.json")
            if os.path.exists(hybrid_path):
                logger.info(f"Loading hybrid model configuration from {hybrid_path}")
                with open(hybrid_path, 'r') as f:
                    self.hybrid_config = json.load(f)
            else:
                logger.warning(f"Hybrid configuration not found at {hybrid_path}")
            
            logger.info("Model loading completed")
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}", exc_info=True)
    
    async def get_similar_movies_from_db(self, movie_id: str, limit: int = 10) -> List[MovieResponse]:
        """
        Get similar movies from pre-computed item similarity collection in MongoDB
        
        Args:
            movie_id: Source movie ID
            limit: Maximum number of similar movies to return
            
        Returns:
            List of similar movies
        """
        try:
            # Check cache first
            cache_key = f"similar:db:{movie_id}:{limit}"
            cached_recommendations = self.cache_repo.get_json(cache_key)
            
            if cached_recommendations:
                logger.debug(f"Cache hit for similar movies: {cache_key}")
                return [MovieResponse(**movie) for movie in cached_recommendations]
            
            # Query MongoDB for pre-computed similarities
            db = get_database()
            item_similarity = await db.item_similarity.find_one({"movie_id": movie_id})
            
            if not item_similarity or "similar_movies" not in item_similarity:
                logger.warning(f"No similarity data found for movie {movie_id}")
                return []
            
            # Get similar movie IDs with similarity score
            similar_items = item_similarity["similar_movies"]
            
            # Sort by similarity (highest first) and limit
            similar_items.sort(key=lambda x: x["similarity"], reverse=True)
            similar_items = similar_items[:limit]
            
            # Get full movie details
            recommendations = []
            for item in similar_items:
                similar_movie_id = item["similarity"]
                movie = await self.movie_repo.get_by_id(similar_movie_id)
                
                if movie:
                    # Create a properly formatted dict for MovieResponse
                    movie_response_dict = {
                        "id": str(movie["_id"]),
                        "title": movie["title"],
                        "genres": movie["genres"],
                        "year": movie.get("year")
                    }
                    
                    # Add poster URL if available
                    if "poster_path" in movie:
                        movie_response_dict["posterUrl"] = self._get_full_poster_url(movie["poster_path"])
                    
                    recommendations.append(MovieResponse(**movie_response_dict))
            
            # Cache the results
            if recommendations:
                self.cache_repo.set_json(
                    cache_key,
                    [movie.dict() for movie in recommendations],
                    settings.RECOMMENDATIONS_CACHE_TTL
                )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting similar movies from DB for {movie_id}: {str(e)}", exc_info=True)
            return []
    
    async def get_collaborative_filtering_recommendations(
        self, 
        user_id: str, 
        limit: int = 10, 
        exclude_seen: bool = True
    ) -> List[MovieResponse]:
        """
        Get movie recommendations using collaborative filtering model
        
        Args:
            user_id: User ID to get recommendations for
            limit: Number of recommendations to return
            exclude_seen: Whether to exclude movies the user has already seen
            
        Returns:
            List of recommended movies
        """
        try:
            # Check if we have a trained model
            if self.cf_model is None or self.cf_mappings is None:
                logger.warning("Collaborative filtering model not loaded. Using fallback.")
                return await self.get_content_based_recommendations(user_id, limit, exclude_seen)
            
            # Check cache first
            cache_key = f"recommendations:cf:user:{user_id}:{limit}:{exclude_seen}"
            cached_recommendations = self.cache_repo.get_json(cache_key)
            
            if cached_recommendations:
                logger.debug(f"Cache hit for CF recommendations: {cache_key}")
                return [MovieResponse(**movie) for movie in cached_recommendations]
                
            # Get movies the user has already seen/rated
            if exclude_seen:
                seen_movie_ids = await self.interaction_repo.get_user_movie_ids(user_id)
            else:
                seen_movie_ids = []
            
            # Get predictions for this user for all movies
            predictions = []
            
            # Get list of all available movies
            all_movies = await self.movie_repo.get_movies(limit=500)  # Consider a smaller set for performance
            
            for movie in all_movies:
                movie_id = str(movie.get("_id"))
                
                # Skip if already seen
                if movie_id in seen_movie_ids:
                    continue
                
                # Get movie index if available in our training data
                if movie_id not in self.cf_mappings['movie_id_map']:
                    continue
                
                # Get user index if available in our training data
                if user_id not in self.cf_mappings['user_id_map']:
                    # If we don't have this user in our training data, 
                    # fallback to content-based recommendations
                    logger.debug(f"User {user_id} not found in CF model. Using content-based fallback.")
                    return await self.get_content_based_recommendations(user_id, limit, exclude_seen)
                
                # Predict rating
                try:
                    predicted_rating = self.cf_model.predict(
                        uid=user_id, 
                        iid=movie_id
                    ).est
                    
                    predictions.append((movie_id, predicted_rating))
                except Exception as e:
                    logger.error(f"Error predicting rating for user {user_id}, movie {movie_id}: {e}")
                    continue
            
            # Sort by predicted rating (highest first)
            predictions.sort(key=lambda x: x[1], reverse=True)
            
            # Get top recommendations
            top_movie_ids = [movie_id for movie_id, _ in predictions[:limit]]
            
            # Get full details for top movies
            recommendations = []
            for movie_id in top_movie_ids:
                movie = await self.movie_repo.get_by_id(movie_id)
                if movie:
                    # Create a properly formatted dict for MovieResponse
                    movie_response_dict = {
                        "id": str(movie["_id"]),
                        "title": movie["title"],
                        "genres": movie["genres"],
                        "year": movie.get("year")
                    }
                    # Add poster URL if available
                    if "poster_path" in movie:
                        movie_response_dict["posterUrl"] = self._get_full_poster_url(movie["poster_path"])
                    
                    recommendations.append(MovieResponse(**movie_response_dict))
            
            # Cache the results
            if recommendations:
                self.cache_repo.set_json(
                    cache_key,
                    [movie.dict() for movie in recommendations],
                    settings.RECOMMENDATIONS_CACHE_TTL
                )
            
            return recommendations
        
        except Exception as e:
            logger.error(f"Error getting CF recommendations for user {user_id}: {str(e)}", exc_info=True)
            # Fallback to content-based
            return await self.get_content_based_recommendations(user_id, limit, exclude_seen)
    
    async def get_content_based_recommendations(
        self, 
        user_id: str, 
        limit: int = 10, 
        exclude_seen: bool = True
    ) -> List[MovieResponse]:
        """
        Get movie recommendations using content-based filtering
        This is similar to the original recommendation service implementation
        
        Args:
            user_id: User ID to get recommendations for
            limit: Number of recommendations to return
            exclude_seen: Whether to exclude movies the user has already seen
            
        Returns:
            List of recommended movies
        """
        try:
            # Check cache first
            cache_key = f"recommendations:cb:user:{user_id}:{limit}:{exclude_seen}"
            cached_recommendations = self.cache_repo.get_json(cache_key)
            
            if cached_recommendations:
                logger.debug(f"Cache hit for CB recommendations: {cache_key}")
                return [MovieResponse(**movie) for movie in cached_recommendations]
                
            # Get user's interactions
            user_movies = await self.interaction_repo.get_user_interactions(
                user_id=user_id,
                limit=10  # Consider only the most recent interactions
            )
            
            if not user_movies:
                logger.info(f"No interactions found for user {user_id}, using popular movies")
                return await self.get_popular_movies(limit)
            
            # Get movies the user has already seen/rated
            if exclude_seen:
                seen_movie_ids = await self.interaction_repo.get_user_movie_ids(user_id)
            else:
                seen_movie_ids = []
            
            # Process each movie the user has interacted with
            movie_scores = {}  # Will store movie_id -> similarity score
            
            for interaction in user_movies:
                movie_id = interaction.get("movie_id")
                if not movie_id:
                    continue
                    
                # Give more weight to higher ratings
                value = interaction.get("value")
                if value is None:
                    interaction_weight = 0.6  # Default weight if no value
                else:
                    interaction_weight = float(value) / 5.0  # Normalize to 0-1
                
                # Get similar movies for this one
                similar_movies = await self.get_similar_movies_from_db(movie_id, limit=20)
                
                # Score each similar movie
                for similar_movie in similar_movies:
                    if similar_movie.id in seen_movie_ids or similar_movie.id in movie_scores:
                        continue
                    
                    # Get similarity from the pre-computed data
                    # For now, use a default similarity value
                    similarity = 0.8
                    
                    # Weight by user's rating
                    weighted_similarity = similarity * interaction_weight
                    
                    # Update score
                    if similar_movie.id in movie_scores:
                        movie_scores[similar_movie.id] = {
                            "movie": similar_movie,
                            "score": movie_scores[similar_movie.id]["score"] + weighted_similarity
                        }
                    else:
                        movie_scores[similar_movie.id] = {
                            "movie": similar_movie,
                            "score": weighted_similarity
                        }
            
            # Sort by score
            sorted_recommendations = sorted(
                movie_scores.values(),
                key=lambda x: x["score"],
                reverse=True
            )
            
            # Get top movies
            recommendations = [item["movie"] for item in sorted_recommendations[:limit]]
            
            # Cache the results
            if recommendations:
                self.cache_repo.set_json(
                    cache_key,
                    [movie.dict() for movie in recommendations],
                    settings.RECOMMENDATIONS_CACHE_TTL
                )
            
            return recommendations
        
        except Exception as e:
            logger.error(f"Error getting content-based recommendations for user {user_id}: {str(e)}", exc_info=True)
            # Fallback to popular movies
            return await self.get_popular_movies(limit)

    async def get_hybrid_recommendations(
        self,
        user_id: str,
        limit: int = 10,
        exclude_seen: bool = True
    ) -> List[MovieResponse]:
        """
        Get movie recommendations using a hybrid approach combining collaborative and content-based filtering
        
        Args:
            user_id: User ID to get recommendations for
            limit: Number of recommendations to return
            exclude_seen: Whether to exclude movies the user has already seen
            
        Returns:
            List of recommended movies
        """
        try:
            # Check if we have a hybrid config
            if self.hybrid_config is None:
                logger.warning("Hybrid configuration not loaded. Using content-based fallback.")
                return await self.get_content_based_recommendations(user_id, limit, exclude_seen)
            
            # Check cache first
            cache_key = f"recommendations:hybrid:user:{user_id}:{limit}:{exclude_seen}"
            cached_recommendations = self.cache_repo.get_json(cache_key)
            
            if cached_recommendations:
                logger.debug(f"Cache hit for hybrid recommendations: {cache_key}")
                return [MovieResponse(**movie) for movie in cached_recommendations]
            
            # Get recommendations from each model
            cf_weight = self.hybrid_config.get('cf_weight', 0.7)
            cb_weight = self.hybrid_config.get('cb_weight', 0.3)
            
            # Get more recommendations than needed from each model to have enough after combining
            larger_limit = min(limit * 3, 30)  # Get 3x more, but max 30
            
            # Get collaborative filtering recommendations
            cf_recommendations = await self.get_collaborative_filtering_recommendations(
                user_id=user_id,
                limit=larger_limit,
                exclude_seen=exclude_seen
            )
            
            # Get content-based recommendations
            cb_recommendations = await self.get_content_based_recommendations(
                user_id=user_id,
                limit=larger_limit,
                exclude_seen=exclude_seen
            )
            
            # Create a score for each recommendation
            movie_scores = {}
            
            # Score CF recommendations
            for i, rec in enumerate(cf_recommendations):
                # Score based on position in the list, higher for earlier positions
                position_score = 1.0 - (i / len(cf_recommendations))
                weighted_score = position_score * cf_weight
                movie_scores[rec.id] = {
                    "movie": rec,
                    "score": weighted_score,
                    "sources": ["collaborative"]
                }
            
            # Score content-based recommendations
            for i, rec in enumerate(cb_recommendations):
                position_score = 1.0 - (i / len(cb_recommendations))
                weighted_score = position_score * cb_weight
                
                if rec.id in movie_scores:
                    # Update existing entry
                    movie_scores[rec.id]["score"] += weighted_score
                    movie_scores[rec.id]["sources"].append("content")
                else:
                    # Add new entry
                    movie_scores[rec.id] = {
                        "movie": rec,
                        "score": weighted_score,
                        "sources": ["content"]
                    }
            
            # Sort by combined score
            sorted_recommendations = sorted(
                movie_scores.values(),
                key=lambda x: x["score"],
                reverse=True
            )
            
            # Extract just the movies for the top items
            recommendations = [item["movie"] for item in sorted_recommendations[:limit]]
            
            # Cache the results
            if recommendations:
                self.cache_repo.set_json(
                    cache_key,
                    [movie.dict() for movie in recommendations],
                    settings.RECOMMENDATIONS_CACHE_TTL
                )
            
            return recommendations
        
        except Exception as e:
            logger.error(f"Error getting hybrid recommendations for user {user_id}: {str(e)}", exc_info=True)
            # Fallback to content-based
            return await self.get_content_based_recommendations(user_id, limit, exclude_seen)
    
    async def get_popular_movies(self, limit: int = 10) -> List[MovieResponse]:
        """
        Get popular movies as a fallback recommendation strategy
        
        Args:
            limit: Number of movies to return
            
        Returns:
            List of popular movies
        """
        try:
            # Check cache first
            cache_key = f"recommendations:popular:{limit}"
            cached_recommendations = self.cache_repo.get_json(cache_key)
            
            if cached_recommendations:
                logger.debug(f"Cache hit for popular movies: {cache_key}")
                return [MovieResponse(**movie) for movie in cached_recommendations]
            
            # Get most rated movies
            popular_movies = await self.movie_repo.get_popular_movies(limit=limit)
            
            recommendations = []
            for movie in popular_movies:
                try:
                    # Create a properly formatted dict for MovieResponse
                    movie_response_dict = {
                        "id": str(movie["_id"]),
                        "title": movie["title"],
                        "genres": movie["genres"],
                        "year": movie.get("year")
                    }
                    
                    # Add poster URL if available
                    if "poster_path" in movie:
                        movie_response_dict["posterUrl"] = self._get_full_poster_url(movie["poster_path"])
                    
                    recommendations.append(MovieResponse(**movie_response_dict))
                except Exception as e:
                    logger.error(f"Error creating MovieResponse for popular movie: {e}")
            
            # Cache the results
            if recommendations:
                self.cache_repo.set_json(
                    cache_key,
                    [movie.dict() for movie in recommendations],
                    settings.POPULAR_ITEMS_CACHE_TTL  # Use longer TTL for popular items
                )
            
            return recommendations
        
        except Exception as e:
            logger.error(f"Error getting popular movies: {str(e)}", exc_info=True)
            return []
    
    def _get_full_poster_url(self, poster_path: Optional[str]) -> Optional[str]:
        """Convert a TMDB poster path to a full URL"""
        if not poster_path:
            return None
        return f"https://image.tmdb.org/t/p/w500{poster_path}"
    
    def _get_full_backdrop_url(self, backdrop_path: Optional[str]) -> Optional[str]:
        """Convert a TMDB backdrop path to a full URL"""
        if not backdrop_path:
            return None
        return f"https://image.tmdb.org/t/p/original{backdrop_path}"


# Create a single instance to be reused
advanced_recommendation_service = AdvancedRecommendationService() 