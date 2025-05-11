from fastapi import APIRouter, HTTPException, Depends, Path, Query, status
from typing import Dict, Any
from ...models.auth import UserCreate, UserLogin, AuthResponse, RegisterResponse
from ...services import auth_service, pipeline_trigger_service
from loguru import logger
from app.core.auth import get_current_user
from app.services.auth_service import get_user_details

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """
    Register a new user
    
    This endpoint creates a new user in Supabase Auth and triggers the data pipeline
    process if it's the first user to register.
    """
    # Convert user metadata
    metadata = {}
    if user.full_name:
        metadata["full_name"] = user.full_name
    
    # Call auth service to register the user
    success, result = await auth_service.register_user(user.email, user.password, metadata)
    
    if not success:
        # If there's an 'already exists' message, return 409 Conflict
        if "already exists" in result.get("error", "").lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                               detail=result.get("error", "User already exists"))
        
        # Otherwise, return 400 Bad Request
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                           detail=result.get("error", "Registration failed"))
    
    # Extract user ID from result
    user_id = result.get("id", "unknown")
    
    # Trigger the data pipeline asynchronously
    # We do this after successful registration but don't wait for its completion
    try:
        await pipeline_trigger_service.trigger_data_pipeline(user_id, user.email)
    except Exception as e:
        # Log error but don't fail the registration
        logger.error(f"Failed to trigger data pipeline: {str(e)}")
    
    # Return success response
    return RegisterResponse(
        message="Registration successful. Please check your email for verification.",
        user_id=user_id,
        email=user.email
    )


@router.post("/login", response_model=AuthResponse)
async def login(user: UserLogin):
    """
    Login a user and return session tokens
    """
    # Call auth service to login the user
    success, result = await auth_service.login_user(user.email, user.password)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                           detail=result.get("error", "Invalid email or password"))
    
    # Extract session and user info from result
    session = {
        "access_token": result.get("access_token", ""),
        "refresh_token": result.get("refresh_token", ""),
        "token_type": "bearer",
        "expires_in": result.get("expires_in", 3600)
    }
    
    user_info = result.get("user", {})
    
    # Return auth response
    return AuthResponse(
        session=session,
        user=user_info
    )

@router.get("/verify", response_model=Dict[str, Any])
async def verify_auth(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Verify if the current authentication token is valid.
    Returns user information if authenticated.
    """
    try:
        # The fact that we reached this point means the token is valid
        # We can return basic user info
        return {
            "isAuthenticated": True,
            "user": {
                "id": current_user.get("user_id"),
                "email": current_user.get("email")
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying authentication: {str(e)}"
        )

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get detailed information about the current authenticated user.
    """
    try:
        # Get additional user details from the database if needed
        user_details = await get_user_details(current_user["user_id"])
        
        # Merge with token info and return
        return {
            "id": current_user["user_id"],
            "email": current_user.get("email", ""),
            **user_details
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user details: {str(e)}"
        ) 