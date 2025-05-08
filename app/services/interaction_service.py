from typing import List, Dict, Any, Optional
from bson import ObjectId
from loguru import logger
from ..core.database import get_database, get_redis
from ..models.interaction import InteractionCreate, InteractionInDB
from datetime import datetime
import json
from ..data_access.mongo_client import InteractionRepository
from ..data_access.redis_client import CacheRepository

class InteractionServiceError(Exception):
    """Base exception for interaction service errors"""
    pass

class InteractionService:
    def __init__(self):
        self.interaction_repo = InteractionRepository()
        self.cache_repo = CacheRepository()
        
    async def create_interaction(self, user_id: str, interaction_data: InteractionCreate) -> Dict[str, Any]:
        """
        Create a new user interaction (e.g., rating, view)
        
        Args:
            user_id: ID of the user performing the interaction
            interaction_data: Interaction data like movie_id, type, value
            
        Returns:
            Dictionary with interaction details, including ID
        """
        try:
            # Create interaction document
            interaction_doc = {
                "user_id": user_id,
                "movie_id": interaction_data.movie_id,
                "type": interaction_data.type,
                "value": interaction_data.value,
                "timestamp": datetime.utcnow()
            }
            
            # Save to database
            result_id = await self.interaction_repo.create_interaction(interaction_doc)
            
            if not result_id:
                raise InteractionServiceError("Failed to create interaction")
                
            # Invalidate cached recommendations for this user
            self.cache_repo.delete_pattern(f"recommendations:user:{user_id}:*")
            
            # Return interaction with ID
            return {
                "id": result_id,
                **interaction_doc
            }
            
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
    
    cursor = db.interactions.find(
        {
            "userId": user_id,
            "type": "rate",
            "value": {"$gte": min_rating}
        },
        {"movieId": 1}
    ).sort("timestamp", -1).limit(limit)
    
    interactions = await cursor.to_list(length=limit)
    return [interaction["movieId"] for interaction in interactions]


async def get_user_viewed_movies(user_id: str) -> List[str]:
    """
    Get all movie IDs that the user has interacted with (for filtering recommendations)
    """
    db = get_database()
    
    cursor = db.interactions.find(
        {"userId": user_id},
        {"movieId": 1}
    )
    
    interactions = await cursor.to_list(length=None)
    return [interaction["movieId"] for interaction in interactions] 