from pydantic import BaseModel, Field, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from typing import List, Optional, Dict, Any, Annotated
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic models"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _schema_generator: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """Return the JSON Schema representation for the ObjectId."""
        return {"type": "string"}


class MovieBase(BaseModel):
    """Base movie model with common attributes"""
    title: str = Field(..., description="The title of the movie")
    genres: List[str] = Field(..., description="List of genres the movie belongs to")
    year: Optional[int] = Field(None, description="Year the movie was released")
    poster_path: Optional[str] = Field(None, description="Relative path to movie poster image")
    backdrop_path: Optional[str] = Field(None, description="Relative path to movie backdrop image")
    tmdb_id: Optional[int] = Field(None, description="The Movie Database ID for the movie")
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }


class MovieCreate(MovieBase):
    """Model for creating a new movie"""
    embedding: Optional[List[float]] = None


class MovieInDB(MovieBase):
    """Movie model as stored in the database, including embedding"""
    id: str = Field(alias="_id")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for content-based filtering")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str
        }
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "title": "The Shawshank Redemption",
                "genres": ["Drama"],
                "year": 1994,
                "embedding": [0.1, 0.2, 0.3, 0.4]  # Shortened for brevity
            }
        }


class MovieResponse(MovieBase):
    """Movie model returned in API responses"""
    id: str = Field(..., description="Unique identifier for the movie")
    poster_url: Optional[str] = Field(None, description="Full URL to movie poster image")
    backdrop_url: Optional[str] = Field(None, description="Full URL to movie backdrop image")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "title": "The Shawshank Redemption",
                "genres": ["Drama"],
                "year": 1994,
                "poster_path": "/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",
                "poster_url": "https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",
                "tmdb_id": 278
            }
        }


class PaginatedMovieResponse(BaseModel):
    """Paginated response for movie listings"""
    items: List[MovieResponse] = Field(..., description="List of movies")
    total: int = Field(..., description="Total number of movies matching criteria")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages") 