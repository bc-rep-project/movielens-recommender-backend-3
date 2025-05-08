from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .movie import MovieResponse


class Recommendation(BaseModel):
    """Single movie recommendation with score"""
    movie: MovieResponse
    score: float = Field(..., description="Recommendation score/relevance (higher is more relevant)")
    

class RecommendationResponse(BaseModel):
    """Model for movie recommendations returned by the API"""
    movie: MovieResponse
    score: float = Field(..., description="Recommendation score or similarity")
    
    class Config:
        json_schema_extra = {
            "example": {
                "movie": {
                    "id": "507f1f77bcf86cd799439011",
                    "title": "The Shawshank Redemption",
                    "genres": ["Drama"],
                    "year": 1994
                },
                "score": 0.98
            }
        }


class UserRecommendationResponse(BaseModel):
    """Response model for user recommendations"""
    userId: str
    recommendations: List[Recommendation]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ItemRecommendationResponse(BaseModel):
    """Response model for item (movie) recommendations"""
    movieId: str
    similar_items: List[RecommendationResponse]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class RecommendationListResponse(BaseModel):
    """Response model for a list of recommendations"""
    items: List[RecommendationResponse]
    count: int = Field(..., description="Number of recommendations") 