from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId
import numpy as np
from loguru import logger
from ..core.database import get_database, get_redis
from ..core.config import settings
from .movie_service import get_movie_embedding
from .interaction_service import get_user_rated_movies, get_user_viewed_movies
import json
from ..data_access.mongo_client import MovieRepository, InteractionRepository
from ..data_access.redis_client import CacheRepository
from ..models.movie import MovieResponse
from ..models.recommendation import RecommendationResponse
from scipy.spatial.distance import cosine
from ..core.exceptions import RecommendationServiceError


class RecommendationService:
    def __init__(self):
        self.movie_repo = MovieRepository()
        self.interaction_repo = InteractionRepository()
        self.cache_repo = CacheRepository()
    
    async def get_recommendations_for_user(
        self, 
        user_id: str, 
        limit: int = 10, 
        exclude_seen: bool = True
    ) -> List[MovieResponse]:
        """
        Get movie recommendations for a user based on their past interactions
        
        Args:
            user_id: User ID to get recommendations for
            limit: Number of recommendations to return
            exclude_seen: Whether to exclude movies the user has already seen
            
        Returns:
            List of recommended movies
        """
        try:
            # Add debug logging
            logger.debug(f"Getting recommendations for user_id: {user_id}, limit: {limit}, exclude_seen: {exclude_seen}")
            
            # Check cache first
            cache_key = f"recommendations:user:{user_id}:{limit}:{exclude_seen}"
            cached_recommendations = self.cache_repo.get_json(cache_key)
            
            if cached_recommendations:
                logger.debug(f"Cache hit for recommendations: {cache_key}")
                return [MovieResponse(**movie) for movie in cached_recommendations]
                
            # Content-based approach:
            # 1. Get user's highly rated movies
            logger.debug(f"Fetching user interactions for {user_id}")
            user_movies = await self.interaction_repo.get_user_interactions(
                user_id=user_id,
                limit=10  # Consider only the most recent interactions
            )
            
            logger.debug(f"Found {len(user_movies)} user interactions")
            if not user_movies:
                logger.info(f"No interactions found for user {user_id}, using default recommendations")
                # Fall back to popular movies
                return await self._get_default_recommendations(limit)
            
            # Log some details about the interactions found
            logger.debug(f"User interactions sample: {user_movies[:2]}")
            
            # 2. Get embeddings for user's favorite movies
            movie_scores = {}  # Will store movie_id -> similarity score
            
            # Get movies the user has already seen/rated
            if exclude_seen:
                logger.debug(f"Fetching movies user {user_id} has already seen")
                seen_movie_ids = await self.interaction_repo.get_user_movie_ids(user_id)
                logger.debug(f"User has seen {len(seen_movie_ids)} movies")
            else:
                seen_movie_ids = []
            
            # Process each movie the user has interacted with
            for interaction in user_movies:
                movie_id = interaction.get("movie_id")
                if not movie_id:
                    logger.warning(f"Interaction missing movie_id field: {interaction}")
                    continue
                    
                # Give more weight to higher ratings
                value = interaction.get("value")
                # Make sure we have a numeric value
                if value is None:
                    interaction_weight = 0.6  # Default weight if no value
                    logger.debug(f"No rating value for movie {movie_id}, using default weight {interaction_weight}")
                else:
                    interaction_weight = float(value) / 5.0  # Normalize to 0-1
                logger.debug(f"Processing movie {movie_id} with weight {interaction_weight}")
                
                # Get this movie's embedding
                source_embedding = await self.movie_repo.get_embedding(movie_id)
                if not source_embedding:
                    logger.warning(f"No embedding found for movie {movie_id}")
                    continue
                
                # Compare it to other movies
                # We can optimize this by getting all embeddings at once or using a vector DB
                # But for now, we'll do it one by one
                logger.debug(f"Fetching candidate movies to compare with {movie_id}")
                candidate_movies = await self.movie_repo.get_movies(limit=100)  # Get candidates
                logger.debug(f"Found {len(candidate_movies)} candidate movies")
                
                for candidate in candidate_movies:
                    candidate_id = str(candidate.get("_id"))
                    
                    # Skip if already seen or already scored
                    if candidate_id in seen_movie_ids or candidate_id in movie_scores:
                        continue
                        
                    # Skip if it's the same movie
                    if candidate_id == movie_id:
                        continue
                    
                    # Get embedding for comparison
                    candidate_embedding = await self.movie_repo.get_embedding(candidate_id)
                    if not candidate_embedding:
                        continue
                    
                    # Calculate similarity
                    try:
                        similarity = 1 - cosine(source_embedding, candidate_embedding)
                        
                        # Apply weight from the interaction
                        weighted_similarity = similarity * interaction_weight
                        
                        # Update score (sum of weighted similarities)
                        if candidate_id in movie_scores:
                            movie_scores[candidate_id] += weighted_similarity
                        else:
                            movie_scores[candidate_id] = weighted_similarity
                    except Exception as e:
                        logger.error(f"Error calculating similarity between {movie_id} and {candidate_id}: {e}")
                        continue
            
            # Sort movies by total score
            logger.debug(f"Calculated scores for {len(movie_scores)} movies")
            sorted_movies = sorted(
                movie_scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Get top N movies
            top_movie_ids = [movie_id for movie_id, _ in sorted_movies[:limit]]
            logger.debug(f"Top movie IDs: {top_movie_ids}")
            
            # Get full details for top movies
            recommendations = []
            for movie_id in top_movie_ids:
                try:
                    movie = await self.movie_repo.get_by_id(movie_id)
                    if movie:
                        # Create a properly formatted dict for MovieResponse
                        movie_response_dict = {
                            "id": str(movie["_id"]),  # Map _id to id
                            "title": movie["title"],
                            "genres": movie["genres"],
                            "year": movie.get("year")  # This field is optional
                        }
                        recommendations.append(MovieResponse(**movie_response_dict))
                except Exception as e:
                    logger.error(f"Error creating MovieResponse for movie {movie_id}: {e}")
            
            logger.debug(f"Returning {len(recommendations)} recommendations")
            
            # Cache the results
            if recommendations:
                self.cache_repo.set_json(
                    cache_key,
                    [movie.dict() for movie in recommendations],
                    settings.RECOMMENDATIONS_CACHE_TTL
                )
            
            return recommendations
                
        except Exception as e:
            logger.error(f"Error getting recommendations for user: {str(e)}", exc_info=True)
            return []
    
    async def get_similar_movies(self, movie_id: str, limit: int = 10) -> List[RecommendationResponse]:
        """
        Get movies similar to the specified movie
        
        Args:
            movie_id: Base movie ID to find similar movies for
            limit: Number of similar movies to return
            
        Returns:
            List of similar movies as RecommendationResponse objects
        """
        try:
            # Check cache first
            cache_key = f"recommendations:similar:{movie_id}:{limit}"
            cached_recommendations = self.cache_repo.get_json(cache_key)
            
            if cached_recommendations:
                logger.debug(f"Cache hit for similar movies: {cache_key}")
                return [RecommendationResponse(**rec) for rec in cached_recommendations]
            
            # Get the source movie's embedding
            source_embedding = await self.movie_repo.get_embedding(movie_id)
            if not source_embedding:
                raise RecommendationServiceError(f"Movie {movie_id} not found or has no embedding")
            
            # Get candidate movies
            candidate_movies = await self.movie_repo.get_movies(limit=100)
            
            # Calculate similarities
            similarities = []
            for candidate in candidate_movies:
                candidate_id = str(candidate.get("_id"))
                
                # Skip if it's the same movie
                if candidate_id == movie_id:
                    continue
                
                # Get embedding for comparison
                candidate_embedding = await self.movie_repo.get_embedding(candidate_id)
                if not candidate_embedding:
                    continue
                
                try:
                    # Calculate similarity
                    similarity = 1 - cosine(source_embedding, candidate_embedding)
                    similarities.append((candidate_id, similarity))
                except Exception as e:
                    logger.error(f"Error calculating similarity between {movie_id} and {candidate_id}: {e}")
                    continue
            
            # Sort by similarity
            sorted_similarities = sorted(similarities, key=lambda x: x[1], reverse=True)
            
            # Get top N movies with their similarity scores
            top_movie_pairs = sorted_similarities[:limit]
            
            # Get full details for top movies
            similar_movies = []
            for similar_id, similarity_score in top_movie_pairs:
                try:
                    movie = await self.movie_repo.get_by_id(similar_id)
                    if movie:
                        # Create a properly formatted dict for MovieResponse
                        movie_response_dict = {
                            "id": str(movie["_id"]),  # Map _id to id
                            "title": movie["title"],
                            "genres": movie["genres"],
                            "year": movie.get("year")  # This field is optional
                        }
                        movie_response = MovieResponse(**movie_response_dict)
                        
                        # Create Recommendation response with movie and score
                        recommendation = RecommendationResponse(
                            movie=movie_response,
                            score=float(similarity_score)
                        )
                        similar_movies.append(recommendation)
                except Exception as e:
                    logger.error(f"Error creating RecommendationResponse for similar movie {similar_id}: {e}")
            
            # Cache the results
            if similar_movies:
                self.cache_repo.set_json(
                    cache_key,
                    [rec.dict() for rec in similar_movies],
                    settings.RECOMMENDATIONS_CACHE_TTL
                )
                
            return similar_movies
            
        except Exception as e:
            logger.error(f"Error getting similar movies: {str(e)}")
            return []
    
    async def _get_default_recommendations(self, limit: int = 10) -> List[MovieResponse]:
        """
        Get default recommendations (fallback when no user data is available)
        Currently returns most recent/popular movies
        """
        try:
            # Could be optimized to be pre-computed in the data processing pipeline
            # For now, just get the first N movies sorted by default
            movies = await self.movie_repo.get_movies(limit=limit)
            
            recommendations = []
            for movie in movies:
                try:
                    # Create a properly formatted dict for MovieResponse
                    movie_response_dict = {
                        "id": str(movie["_id"]),  # Map _id to id
                        "title": movie["title"],
                        "genres": movie["genres"],
                        "year": movie.get("year")  # This field is optional
                    }
                    recommendations.append(MovieResponse(**movie_response_dict))
                except Exception as e:
                    logger.error(f"Error creating MovieResponse for default recommendation: {e}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting default recommendations: {str(e)}")
            return []
            
    async def get_popular_movies(self, limit: int = 10) -> List[MovieResponse]:
        """
        Get popular movies based on interaction count
        
        Args:
            limit: Number of popular movies to return
            
        Returns:
            List of popular movies
        """
        try:
            # Try to get from cache first
            cache_key = f"movies:popular:{limit}"
            try:
                cached_data = self.cache_repo.get_json(cache_key)
                if cached_data:
                    logger.debug(f"Cache hit for {cache_key}")
                    return [MovieResponse(**movie) for movie in cached_data]
            except Exception as cache_error:
                logger.warning(f"Cache error in get_popular_movies: {cache_error}, proceeding without cache")
            
            # Get database connection
            db = get_database()
            
            # MongoDB aggregation to get popular movies
            try:
                # Try aggregation based on interactions
                pipeline = [
                    {"$group": {"_id": "$movieId", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": limit * 2}  # Get more than needed to allow for possible missing movies
                ]
                
                popular_movie_ids_cursor = db.interactions.aggregate(pipeline)
                popular_movie_ids = await popular_movie_ids_cursor.to_list(length=limit * 2)
                
                # Convert to ObjectIds and fetch the movies
                movie_ids = []
                for item in popular_movie_ids:
                    try:
                        movie_ids.append(ObjectId(item["_id"]))
                    except Exception:
                        logger.warning(f"Invalid ObjectId in popular_movie_ids: {item}")
                        continue
                
                if movie_ids:
                    # Fetch movie details
                    cursor = db.movies.find(
                        {"_id": {"$in": movie_ids}},
                        {"embedding": 0}
                    ).limit(limit)
                    
                    movies_data = await cursor.to_list(length=limit)
                    
                    if movies_data:
                        # Convert to MovieResponse objects with CONSISTENT ID FORMAT
                        movies = []
                        for movie in movies_data:
                            try:
                                # Use the same movie_dict structure as in movie_service
                                movie_dict = {
                                    "id": str(movie["_id"]),  # Always use MongoDB ObjectId as the standard
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
                                logger.error(f"Error creating MovieResponse in get_popular_movies: {e}")
                        
                        # Try to cache the result
                        try:
                            if movies:
                                self.cache_repo.set_json(
                                    cache_key,
                                    [movie.dict() for movie in movies],
                                    settings.RECOMMENDATIONS_CACHE_TTL
                                )
                        except Exception as cache_error:
                            logger.warning(f"Cache error when storing popular movies: {cache_error}")
                        
                        return movies
            
            except Exception as agg_error:
                logger.warning(f"Error in MongoDB aggregation for popular movies: {agg_error}")
            
            # Fallback: just get recent movies if aggregation failed or returned no results
            logger.info("Using fallback method to get popular movies")
            return await self._get_default_recommendations(limit)
            
        except Exception as e:
            logger.error(f"Error getting popular movies: {str(e)}")
            # Return empty list on error
            return []

    # Add helper method for poster URL construction (same as in MovieService)
    def _get_full_poster_url(self, poster_path: Optional[str]) -> Optional[str]:
        """Create a full poster URL from a relative path"""
        if not poster_path:
            return None
        return f"{settings.TMDB_IMAGE_BASE_URL}{poster_path}"

    def _get_full_backdrop_url(self, backdrop_path: Optional[str]) -> Optional[str]:
        """Create a full backdrop URL from a relative path"""
        if not backdrop_path:
            return None
        return f"{settings.TMDB_IMAGE_BASE_URL.replace('w500', 'original')}{backdrop_path}"

# Create a singleton instance
recommendation_service = RecommendationService()


async def get_user_recommendations(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get personalized recommendations for a user
    """
    db = get_database()
    redis_client = get_redis()
    
    # Check Redis cache first
    cache_key = f"rec:{user_id}"
    if redis_client:
        try:
            cached_recs = redis_client.get(cache_key)
            if cached_recs:
                logger.debug(f"Cache hit for user recommendations: {user_id}")
                return json.loads(cached_recs)
        except Exception as e:
            logger.warning(f"Redis error in get_user_recommendations: {e}")
    
    # Get user's highly rated movies
    liked_movie_ids = await get_user_rated_movies(user_id)
    
    if not liked_movie_ids:
        # User has no ratings, return popular movies instead
        return await get_popular_movies(limit)
    
    # Get all movies the user has interacted with (to exclude from recommendations)
    viewed_movie_ids = await get_user_viewed_movies(user_id)
    viewed_movie_ids_set = set(viewed_movie_ids)
    
    # Get embeddings for liked movies
    liked_embeddings = []
    for movie_id in liked_movie_ids:
        embedding = await get_movie_embedding(movie_id)
        if embedding:
            liked_embeddings.append(embedding)
    
    if not liked_embeddings:
        # No embeddings found, return popular movies
        return await get_popular_movies(limit)
    
    # Convert embeddings to numpy arrays for faster computation
    liked_embeddings_np = np.array(liked_embeddings)
    
    # Get candidate movies (popular ones to avoid loading all movies)
    # This is an optimization for the free tier - in production, we might use a vector DB
    popular_movie_docs = await get_popular_movies(100)  # Get more than needed for filtering
    
    # Calculate similarity with each candidate movie
    recommendations = []
    
    for movie_doc in popular_movie_docs:
        movie_id = str(movie_doc["_id"])
        
        # Skip if user already interacted with this movie
        if movie_id in viewed_movie_ids_set:
            continue
        
        # Get movie embedding
        movie_embedding = await get_movie_embedding(movie_id)
        
        if movie_embedding:
            # Calculate similarity with liked movies
            movie_embedding_np = np.array(movie_embedding)
            
            # Calculate cosine similarity with each liked movie
            similarities = np.dot(liked_embeddings_np, movie_embedding_np) / (
                np.linalg.norm(liked_embeddings_np, axis=1) * np.linalg.norm(movie_embedding_np)
            )
            
            # Take the maximum similarity as the score
            similarity_score = float(np.max(similarities))
            
            recommendations.append({
                "movie": movie_doc,
                "score": similarity_score
            })
    
    # Sort by score (descending) and take top N
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    top_recommendations = recommendations[:limit]
    
    # Cache the results
    if redis_client:
        try:
            redis_client.setex(
                cache_key,
                settings.RECOMMENDATIONS_CACHE_TTL,
                json.dumps(top_recommendations, default=str)
            )
        except Exception as e:
            logger.warning(f"Redis error when caching user recommendations: {e}")
    
    return top_recommendations


async def get_popular_movies(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get popular movies based on interaction count
    Used as a fallback recommendation strategy
    """
    db = get_database()
    redis_client = get_redis()
    
    # Check Redis cache
    cache_key = f"movies:popular:{limit}"
    if redis_client:
        try:
            cached_popular = redis_client.get(cache_key)
            if cached_popular:
                return json.loads(cached_popular)
        except Exception as e:
            logger.warning(f"Redis error when getting popular movies from cache: {e}")
    
    try:
        # MongoDB aggregation to get popular movies
        pipeline = [
            {"$group": {"_id": "$movieId", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit * 2}  # Get more than needed to allow for possible missing movies
        ]
        
        popular_movie_ids_cursor = db.interactions.aggregate(pipeline)
        popular_movie_ids = await popular_movie_ids_cursor.to_list(length=limit * 2)
        
        # Convert to ObjectIds and fetch the movies
        movie_ids = []
        for item in popular_movie_ids:
            try:
                movie_ids.append(ObjectId(item["_id"]))
            except Exception as e:
                logger.warning(f"Invalid ObjectId: {e}")
                continue
        
        if not movie_ids:
            # Fallback: just get recent movies if no interactions exist
            cursor = db.movies.find({}, {"embedding": 0}).sort("_id", -1).limit(limit)
            movies = await cursor.to_list(length=limit)
            return movies
        
        # Fetch movie details (excluding embeddings to save memory)
        cursor = db.movies.find(
            {"_id": {"$in": movie_ids}},
            {"embedding": 0}
        ).limit(limit)
        
        movies = await cursor.to_list(length=limit)
        
        # Cache the results
        if redis_client and movies:
            try:
                redis_client.setex(
                    cache_key,
                    settings.RECOMMENDATIONS_CACHE_TTL,
                    json.dumps(movies, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis error when caching popular movies: {e}")
        
        return movies
    except Exception as e:
        logger.error(f"Error getting popular movies: {e}")
        # Fallback to simple query if aggregation fails
        try:
            cursor = db.movies.find({}, {"embedding": 0}).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as fallback_error:
            logger.error(f"Error in fallback for popular movies: {fallback_error}")
            return []


async def get_similar_movies(movie_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get movies similar to the given movie based on embedding similarity
    """
    db = get_database()
    redis_client = get_redis()
    
    # Check Redis cache
    cache_key = f"similar:{movie_id}:{limit}"
    if redis_client:
        cached_similar = redis_client.get(cache_key)
        if cached_similar:
            return json.loads(cached_similar)
    
    # Get the movie embedding
    movie_embedding = await get_movie_embedding(movie_id)
    
    if not movie_embedding:
        logger.error(f"Embedding not found for movie {movie_id}")
        return []
    
    # Convert to numpy array
    movie_embedding_np = np.array(movie_embedding)
    
    # Get a sample of movies to compare with
    # In production, this would use a vector DB or pre-computed similarities
    cursor = db.movies.find(
        {"_id": {"$ne": ObjectId(movie_id)}},
        {"embedding": 1, "title": 1, "genres": 1, "movieId_ml": 1}
    ).limit(100)  # Limit to avoid loading too many embeddings
    
    candidate_movies = await cursor.to_list(length=100)
    
    # Calculate similarities
    similar_movies = []
    
    for candidate in candidate_movies:
        if "embedding" not in candidate:
            continue
            
        candidate_embedding = np.array(candidate["embedding"])
        
        # Calculate cosine similarity
        similarity = np.dot(movie_embedding_np, candidate_embedding) / (
            np.linalg.norm(movie_embedding_np) * np.linalg.norm(candidate_embedding)
        )
        
        # Remove embedding to save space
        movie_dict = dict(candidate)
        del movie_dict["embedding"]
        
        similar_movies.append({
            "movie": movie_dict,
            "score": float(similarity)
        })
    
    # Sort by similarity and get top N
    similar_movies.sort(key=lambda x: x["score"], reverse=True)
    top_similar = similar_movies[:limit]
    
    # Cache the results
    if redis_client:
        redis_client.setex(
            cache_key,
            settings.RECOMMENDATIONS_CACHE_TTL,
            json.dumps(top_similar, default=str)
        )
    
    return top_similar 