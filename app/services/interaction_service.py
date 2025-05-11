from typing import List, Dict, Any, Optional
from bson import ObjectId
from loguru import logger
from ..core.database import get_database, get_redis
from ..models.interaction import InteractionCreate, InteractionInDB
from datetime import datetime
import json
from ..data_access.mongo_client import InteractionRepository
from ..data_access.redis_client import CacheRepository
from ..core.exceptions import InteractionServiceError

class InteractionService:
    def __init__(self):
        self.interaction_repo = InteractionRepository()
        self.cache_repo = CacheRepository()
        
    async def create_interaction(self, user_id: str, interaction_data: InteractionCreate) -> Dict[str, Any]:
        """
        Create a new user interaction (e.g., rating, view)
        
        Args:
            user_id: ID of the user performing the interaction (from token)
            interaction_data: Interaction data like movie_id, type, value
            
        Returns:
            Dictionary with interaction details, including ID
        """
        try:
            # Use token user_id if not provided in request body
            effective_user_id = interaction_data.userId or user_id
            
            # Create interaction document
            interaction_doc = {
                "user_id": effective_user_id,
                "movie_id": interaction_data.movieId,
                "type": interaction_data.type,
                "value": interaction_data.value,
                "timestamp": datetime.utcnow()
            }
            
            logger.debug(f"Creating interaction: {interaction_doc}")
            
            # Save to database
            result_id = await self.interaction_repo.create_interaction(interaction_doc)
            
            if not result_id:
                raise InteractionServiceError("Failed to create interaction")
                
            # Invalidate cached recommendations for this user - handle potential Redis failures
            try:
                self.cache_repo.delete_pattern(f"recommendations:user:{effective_user_id}:*")
            except Exception as cache_error:
                logger.warning(f"Failed to invalidate cache: {cache_error}")
                # Continue execution even if cache invalidation fails
            
            # Create a new response object with only JSON serializable fields
            response_doc = {
                "id": str(result_id),
                "user_id": effective_user_id,
                "movie_id": interaction_data.movieId,
                "type": interaction_data.type,
                "value": interaction_data.value,
                "timestamp": interaction_doc["timestamp"].isoformat()
            }
            
            # Log the response document for debugging
            logger.debug(f"Response document: {response_doc}")
            
            return response_doc
            
        except Exception as e:
            logger.error(f"Error creating interaction: {str(e)}")
            raise InteractionServiceError(f"Failed to create interaction: {str(e)}")
    
    async def get_user_interactions(self, user_id: str, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get interactions for a specific user
        
        Args:
            user_id: ID of the user
            skip: Number of interactions to skip
            limit: Maximum number of interactions to return
            
        Returns:
            List of interactions
        """
        try:
            results = await self.interaction_repo.get_user_interactions(
                user_id=user_id,
                skip=skip,
                limit=limit
            )
            
            # Convert ObjectIds to strings
            for interaction in results:
                if '_id' in interaction:
                    interaction['_id'] = str(interaction['_id'])
                    
            return results
            
        except Exception as e:
            logger.error(f"Error getting user interactions: {str(e)}")
            return []

# Create a singleton instance
interaction_service = InteractionService()

async def get_user_rated_movies(user_id: str, min_rating: float = 3.5, limit: int = 20) -> List[str]:
    """
    Get movie IDs that the user has rated highly (for recommendation generation)
    """
    db = get_database()
    
    # Log the query for debugging
    logger.debug(f"Querying highly rated movies for user_id: {user_id}, min_rating: {min_rating}")
    
    cursor = db.interactions.find(
        {
            "user_id": user_id,
            "type": "rate",
            "value": {"$gte": min_rating}
        },
        {"movie_id": 1}
    ).sort("timestamp", -1).limit(limit)
    
    interactions = await cursor.to_list(length=limit)
    result = [interaction["movie_id"] for interaction in interactions if "movie_id" in interaction]
    
    # Log the number of movies found
    logger.debug(f"Found {len(result)} highly rated movies for user: {user_id}")
    
    return result


async def get_user_viewed_movies(user_id: str) -> List[str]:
    """
    Get all movie IDs that the user has interacted with (for filtering recommendations)
    """
    db = get_database()
    
    # Log the query for debugging
    logger.debug(f"Querying all viewed movies for user_id: {user_id}")
    
    cursor = db.interactions.find(
        {"user_id": user_id},
        {"movie_id": 1}
    )
    
    interactions = await cursor.to_list(length=None)
    result = [interaction["movie_id"] for interaction in interactions if "movie_id" in interaction]
    
    # Log the number of movies found
    logger.debug(f"Found {len(result)} viewed movies for user: {user_id}")
    
    return result 