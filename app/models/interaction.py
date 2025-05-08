from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId
from .movie import PyObjectId


class InteractionBase(BaseModel):
    """Base Interaction model with common fields"""
    userId: str
    movieId: str  # This is the MongoDB _id of the movie
    type: Literal["rate", "view"] = "view"
    value: Optional[float] = None  # Rating value (1-5) if type is "rate"
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }


class InteractionCreate(InteractionBase):
    """Model for creating an interaction"""
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class InteractionRead(InteractionBase):
    """Model for reading an interaction"""
    id: str = Field(..., description="Unique identifier for the interaction")
    timestamp: datetime = Field(..., description="When the interaction occurred")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "userId": "user123",
                "movieId": "movie456",
                "type": "like",
                "timestamp": "2023-10-15T12:34:56.789Z" 
            }
        }


class InteractionInDB(InteractionBase):
    """Interaction model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }


class InteractionResponse(InteractionBase):
    """Interaction response model"""
    id: str = Field(..., alias="_id")
    timestamp: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        } 