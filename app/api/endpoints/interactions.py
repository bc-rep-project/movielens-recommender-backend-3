from fastapi import APIRouter, Depends, HTTPException, Query
from ...services.interaction_service import interaction_service, InteractionServiceError
from ...models.interaction import InteractionCreate, InteractionRead
from ..deps import get_current_user_id
from typing import List, Dict, Any
from loguru import logger

router = APIRouter()

@router.post("")
async def create_interaction(
    interaction: InteractionCreate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new interaction (rating, view) for the authenticated user
    """
    try:
        logger.info(f"Creating interaction with user_id {user_id} and data: {interaction.dict()}")
        
        # Initialize response
        result = None
        
        # Call interaction service
        try:
            result = await interaction_service.create_interaction(
                user_id=user_id,
                interaction_data=interaction
            )
            logger.info(f"Interaction created successfully: {result}")
        except Exception as service_error:
            logger.error(f"Error in interaction_service.create_interaction: {service_error}")
            raise
            
        return result
    except InteractionServiceError as e:
        logger.error(f"InteractionServiceError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unhandled error in create_interaction: {str(e)}, type: {type(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating interaction: {str(e)}")

@router.get("/me")
async def get_my_interactions(
    skip: int = Query(0, ge=0, description="Number of interactions to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of interactions to return"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get interactions for the authenticated user
    """
    try:
        interactions = await interaction_service.get_user_interactions(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        return interactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving interactions: {str(e)}") 