from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..services.auth_service import verify_token
from ..core.database import get_database, get_redis
from ..services.movie_service import movie_service
from typing import Optional
from loguru import logger

security = HTTPBearer()

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Get current user ID from JWT token
    """
    token = credentials.credentials
    result = await verify_token(token)
    
    # Handle tuple return value (is_valid, payload) from auth_service.verify_token
    if isinstance(result, tuple) and len(result) == 2:
        is_valid, payload = result
        if not is_valid:
            logger.error(f"Token verification failed: {payload.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # If valid, use the payload
        payload = result[1]
    else:
        # Direct payload return from core.auth.verify_token
        payload = result
    
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload["sub"]

async def get_optional_user_id(
    request: Request
) -> Optional[str]:
    """
    Get user ID from JWT token if present, otherwise return None
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
        
    token = auth_header.replace("Bearer ", "")
    try:
        result = await verify_token(token)
        
        # Handle tuple return value (is_valid, payload) from auth_service.verify_token
        if isinstance(result, tuple) and len(result) == 2:
            is_valid, payload = result
            if not is_valid:
                return None
            # If valid, use the payload
            payload = result[1]
        else:
            # Direct payload return from core.auth.verify_token
            payload = result
            
        if payload and "sub" in payload:
            return payload["sub"]
    except:
        pass
        
    return None

def get_movie_service():
    """
    Dependency for getting the movie service
    """
    return movie_service 