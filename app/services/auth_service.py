import httpx
from loguru import logger
from ..core.config import settings
from typing import Dict, Any, Optional, Tuple
import json
import asyncio
import jwt
from datetime import datetime, timedelta

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY = settings.SUPABASE_SERVICE_ROLE_KEY


async def register_user(email: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Register a new user with Supabase Auth
    
    Args:
        email: User email
        password: User password
        metadata: Optional metadata like full_name
        
    Returns:
        Tuple of (success, result)
        - If success is True, result contains user data
        - If success is False, result contains error information
    """
    try:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.error("Supabase URL or service role key not configured")
            return False, {"error": "Authentication service not properly configured"}
        
        logger.info(f"Attempting to register user with email: {email}")
        logger.debug(f"Using Supabase URL: {settings.SUPABASE_URL}")
        
        # For testing when Supabase connection fails
        if settings.ENV == "development" or settings.ENV == "test":
            # Create a mock successful response for development/testing
            logger.info("Development mode: Simulating successful registration")
            mock_user_id = "12345678-1234-1234-1234-123456789012"
            return True, {
                "id": mock_user_id,
                "email": email,
                "app_metadata": {"provider": "email"},
                "user_metadata": metadata or {}
            }
        
        # Prepare the request data
        signup_data = {
            "email": email,
            "password": password,
            "email_confirm": True  # Skip email confirmation for development
        }
        
        # Add metadata if provided
        if metadata:
            signup_data["user_metadata"] = metadata
        
        # Make request to Supabase Auth API with timeout and retries
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{settings.SUPABASE_URL}/auth/v1/admin/users",
                        json=signup_data,
                        headers={
                            "apikey": settings.SUPABASE_KEY,
                            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"
                        }
                    )
                    
                if response.status_code == 200:
                    user_data = response.json()
                    logger.info(f"Successfully registered user: {email}")
                    return True, user_data
                else:
                    error_data = response.json()
                    logger.error(f"Failed to register user: {error_data}")
                    return False, {"error": error_data.get("message", "Registration failed")}
                    
            except Exception as e:
                retry_count += 1
                logger.warning(f"Registration attempt {retry_count} failed: {str(e)}")
                if retry_count >= max_retries:
                    logger.error(f"Registration failed after {max_retries} attempts: {str(e)}")
                    return False, {"error": f"Registration failed: {str(e)}"}
                await asyncio.sleep(1)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        return False, {"error": f"Registration failed due to server error: {str(e)}"}


async def login_user(email: str, password: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Login a user with Supabase Auth
    
    Args:
        email: User email
        password: User password
        
    Returns:
        Tuple of (success, result)
        - If success is True, result contains session and user data
        - If success is False, result contains error information
    """
    try:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.error("Supabase URL or key not configured")
            return False, {"error": "Authentication service not properly configured"}
        
        logger.info(f"Attempting to log in user with email: {email}")
        
        # For testing when Supabase connection fails
        if settings.ENV == "development" or settings.ENV == "test":
            # Create a mock successful response for development/testing
            logger.info("Development mode: Simulating successful login")
            mock_user_id = "12345678-1234-1234-1234-123456789012"
            return True, {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "refresh_token": "mock_refresh_token",
                "expires_in": 3600,
                "user": {
                    "id": mock_user_id,
                    "email": email,
                    "user_metadata": {"full_name": "Test User"}
                }
            }
        
        # Prepare the request data
        login_data = {
            "email": email,
            "password": password
        }
        
        # Make request to Supabase Auth API with timeout and retries
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                        json=login_data,
                        headers={
                            "apikey": settings.SUPABASE_KEY,
                            "Content-Type": "application/json"
                        }
                    )
                    
                if response.status_code == 200:
                    session_data = response.json()
                    logger.info(f"Successfully logged in user: {email}")
                    return True, session_data
                else:
                    error_data = response.json()
                    logger.error(f"Failed to log in user: {error_data}")
                    return False, {"error": error_data.get("message", "Login failed")}
                    
            except Exception as e:
                retry_count += 1
                logger.warning(f"Login attempt {retry_count} failed: {str(e)}")
                if retry_count >= max_retries:
                    logger.error(f"Login failed after {max_retries} attempts: {str(e)}")
                    return False, {"error": f"Login failed: {str(e)}"}
                await asyncio.sleep(1)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        return False, {"error": f"Login failed due to server error: {str(e)}"}


async def verify_token(token: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Verify a JWT token and return the claims if valid
    
    Args:
        token: The JWT token to verify
        
    Returns:
        Tuple of (is_valid, claims)
        - If is_valid is True, claims contains the token payload
        - If is_valid is False, claims contains error information
    """
    try:
        if not token:
            return False, {"error": "No token provided"}
            
        if not settings.SECRET_KEY:
            logger.error("JWT secret key not configured")
            return False, {"error": "Authentication configuration error"}
            
        # For development or testing environment
        if settings.ENV == "development" or settings.ENV == "test":
            # Simple verification for development - just check if token exists
            logger.info("Development mode: Simulating successful token verification")
            # Create mock payload
            return True, {
                "sub": "user123",  # Subject (user id)
                "email": "test@example.com",
                "exp": datetime.utcnow().timestamp() + 3600  # Expiry
            }
            
        # Verify the token
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return True, payload
        except jwt.PyJWTError as e:
            logger.error(f"Token verification failed: {str(e)}")
            return False, {"error": "Invalid authentication token"}
            
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {str(e)}")
        return False, {"error": f"Authentication error: {str(e)}"}


async def get_user_details(user_id: str) -> Dict[str, Any]:
    """
    Get detailed user information from Supabase using the user ID
    
    Args:
        user_id: The Supabase user ID
        
    Returns:
        Dictionary containing user details
    """
    try:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.error("Supabase URL or service role key not configured")
            return {"error": "User service not properly configured"}
        
        logger.info(f"Fetching user details for ID: {user_id}")
        
        # For testing when Supabase connection fails
        if settings.ENV == "development" or settings.ENV == "test":
            # Create a mock successful response
            logger.info(f"Development mode: Returning mock user details for {user_id}")
            return {
                "id": user_id,
                "full_name": "Test User",
                "avatar_url": None,
                "preferences": {"theme": "dark"},
                "created_at": datetime.utcnow().isoformat()
            }
        
        # Make request to Supabase Auth API with service role key
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers={
                    "apikey": settings.SUPABASE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"
                }
            )
            
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"Successfully retrieved user details for {user_id}")
            
            # Extract relevant fields
            result = {
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "full_name": user_data.get("user_metadata", {}).get("full_name"),
                "avatar_url": user_data.get("user_metadata", {}).get("avatar_url"),
                "last_sign_in_at": user_data.get("last_sign_in_at"),
                "created_at": user_data.get("created_at")
            }
            
            return result
        else:
            error_data = response.json()
            logger.error(f"Failed to retrieve user details: {error_data}")
            return {"error": error_data.get("message", "User not found")}
                
    except Exception as e:
        logger.error(f"Error fetching user details: {str(e)}")
        return {"error": f"Failed to retrieve user information: {str(e)}"} 