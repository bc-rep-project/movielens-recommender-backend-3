from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List


class UserCreate(BaseModel):
    """Model for user registration"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class UserLogin(BaseModel):
    """Model for user login"""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response model for successful authentication"""
    session: Dict[str, Any]
    user: Dict[str, Any]


class RegisterResponse(BaseModel):
    """Response model for successful registration"""
    message: str
    user_id: str
    email: str 