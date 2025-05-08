from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from .config import settings
from loguru import logger
import httpx
import json
from typing import Dict, Optional, Any

# Security scheme for JWT Bearer token
security = HTTPBearer()

# Cache the JWKS data to avoid frequent network requests
jwks_cache: Dict[str, Any] = {}


async def get_jwks():
    """
    Get JSON Web Key Set from Supabase for JWT verification
    Caches the JWKS data to avoid frequent network requests
    """
    global jwks_cache
    if jwks_cache:
        return jwks_cache
    
    try:
        async with httpx.AsyncClient() as client:
            jwks_url = f"{settings.SUPABASE_URL}/auth/v1/jwks"
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks_cache = response.json()
            return jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify Supabase JWT token and return user information
    """
    token = credentials.credentials
    
    try:
        # Get the JWKS to verify the token
        jwks = await get_jwks()
        
        # For simplicity in this example, we're using the first key in JWKS
        # A more robust implementation would select the key by 'kid' header in the JWT
        public_key = jwks['keys'][0]
        
        # Decode and verify the token
        payload = jwt.decode(
            token,
            key=json.dumps(public_key),
            algorithms=["RS256"],
            audience="authenticated"
        )
        
        # Check if token is valid
        if not payload:
            raise JWTError("Invalid token")
        
        # Extract user_id from the sub claim
        user_id = payload.get("sub")
        if not user_id:
            raise JWTError("User ID not found in token")
        
        return {
            "user_id": user_id,
            "email": payload.get("email", ""),
            # Add more user information as needed
        }
        
    except JWTError as e:
        logger.error(f"JWT verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )


# Dependency to use in protected routes
async def get_current_user(user_info: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get current authenticated user information
    """
    return user_info 