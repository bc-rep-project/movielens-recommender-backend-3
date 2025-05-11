from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId
from typing import List, Dict, Any, Optional
from ..core.database import get_database
from loguru import logger

class BaseRepository:
    """Base repository class for MongoDB collections"""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the MongoDB collection"""
        db = get_database()
        return db[self.collection_name]


class MovieRepository(BaseRepository):
    """Repository for movie-related database operations"""
    
    def __init__(self):
        super().__init__("movies")
    
    async def get_by_id(self, movie_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a movie by ID
        
        Args:
            movie_id: MongoDB ObjectId as string
            
        Returns:
            Movie document if found, None otherwise
            
        Raises:
            ValueError: If movie_id is not a valid ObjectId
        """
        try:
            # Validate movie_id format before query
            if not ObjectId.is_valid(movie_id):
                raise ValueError(f"Invalid ObjectId format: {movie_id}")
                
            collection = await self.get_collection()
            return await collection.find_one({"_id": ObjectId(movie_id)})
        except Exception as e:
            # Log the error but don't mask the original exception
            logger.error(f"Error in MovieRepository.get_by_id: {e}")
            raise
    
    async def get_movies(self, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """Get a paginated list of movies"""
        try:
            print(f"MovieRepository.get_movies called with skip={skip}, limit={limit}")
            collection = await self.get_collection()
            print("Got collection, executing find query...")
            # Exclude embedding field as it's large and not needed for listing
            cursor = collection.find({}, {"embedding": 0}).skip(skip).limit(limit)
            
            print("Converting cursor to list...")
            result = await cursor.to_list(length=limit)
            print(f"Found {len(result)} movies")
            
            if len(result) > 0:
                print(f"First movie (sample): {result[0]['title']}")
                print(f"First movie fields: {list(result[0].keys())}")
            
            return result
        except Exception as e:
            logger.error(f"Error in MovieRepository.get_movies: {e}")
            print(f"Error in MovieRepository.get_movies: {e}")
            return []
    
    async def search_movies(self, query: str, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for movies by title"""
        try:
            collection = await self.get_collection()
            # Create a text index on title if it doesn't exist
            await collection.create_index([("title", "text")])
            
            cursor = collection.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}, "embedding": 0}
            ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(limit)
            
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error in MovieRepository.search_movies: {e}")
            return []
    
    async def get_embedding(self, movie_id: str) -> Optional[List[float]]:
        """Get the embedding vector for a movie"""
        try:
            collection = await self.get_collection()
            result = await collection.find_one(
                {"_id": ObjectId(movie_id)},
                {"embedding": 1}
            )
            
            if result and "embedding" in result:
                return result["embedding"]
            return None
        except Exception as e:
            logger.error(f"Error in MovieRepository.get_embedding: {e}")
            return None


class InteractionRepository(BaseRepository):
    """Repository for interaction-related database operations"""
    
    def __init__(self):
        super().__init__("interactions")
    
    async def create_interaction(self, interaction_data: Dict[str, Any]) -> Optional[str]:
        """Create a new interaction"""
        try:
            collection = await self.get_collection()
            result = await collection.insert_one(interaction_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error in InteractionRepository.create_interaction: {e}")
            return None
    
    async def get_user_interactions(self, user_id: str, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """Get a user's interactions"""
        try:
            collection = await self.get_collection()
            cursor = collection.find({"user_id": user_id}).sort("timestamp", -1).skip(skip).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error in InteractionRepository.get_user_interactions: {e}")
            return []
    
    async def get_user_movie_ids(self, user_id: str, interaction_type: Optional[str] = None) -> List[str]:
        """Get movie IDs that a user has interacted with"""
        try:
            collection = await self.get_collection()
            query = {"user_id": user_id}
            if interaction_type:
                query["type"] = interaction_type
                
            cursor = collection.find(query, {"movie_id": 1})
            
            results = await cursor.to_list(length=None)
            return [doc["movie_id"] for doc in results if "movie_id" in doc]
        except Exception as e:
            logger.error(f"Error in InteractionRepository.get_user_movie_ids: {e}")
            return [] 