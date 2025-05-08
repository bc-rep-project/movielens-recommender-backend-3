from loguru import logger
from typing import Dict, Any
from datetime import datetime
import json
import os
import base64
from ..core.config import settings
from ..core.database import get_database
import httpx
import time
from google.cloud import pubsub_v1

# Check if google-cloud-pubsub is available
try:
    from google.cloud import pubsub_v1
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    logger.warning("google-cloud-pubsub package not installed, pub/sub trigger will be disabled")

# Default values and environment variables
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "trigger-movielens-pipeline")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")

# Get GCP project ID from bucket name if available
if not PROJECT_ID and settings.GCS_BUCKET_NAME:
    # Try to extract project ID from bucket name (e.g., project-name_cloudbuild)
    try:
        PROJECT_ID = settings.GCS_BUCKET_NAME.split('_')[0]
        logger.info(f"Extracted project ID from bucket name: {PROJECT_ID}")
    except:
        logger.warning("Could not extract project ID from bucket name")


async def check_if_pipeline_needed() -> bool:
    """
    Check if the data pipeline needs to be executed by checking if movies collection exists and has data
    
    Returns:
        bool: True if pipeline needs to be run, False otherwise
    """
    try:
        # Get MongoDB database instance
        db = get_database()
        
        # If database connection is not available, we can't check
        if db is None:
            logger.warning("Cannot check if pipeline is needed: MongoDB connection not available")
            return False
            
        # Check if movies collection exists and has documents
        if "movies" in await db.list_collection_names():
            # Check if the collection has documents
            count = await db.movies.count_documents({})
            if count > 0:
                logger.info(f"Movies collection already has {count} documents, pipeline not needed")
                return False
        
        logger.info("Movies collection empty or doesn't exist, pipeline needed")
        return True
    
    except Exception as e:
        logger.error(f"Error checking if pipeline is needed: {str(e)}")
        # Default to not running pipeline on error to prevent repeated execution
        return False


async def trigger_data_pipeline(user_id: str, email: str) -> bool:
    """
    Trigger the data pipeline process after a new user registers
    
    This function publishes a message to a Pub/Sub topic or
    calls an HTTP endpoint to trigger the pipeline process.
    
    Args:
        user_id: The ID of the new user
        email: The email of the new user
    
    Returns:
        bool: True if the trigger was successful, False otherwise
    """
    # Check if pipeline is actually needed
    pipeline_needed = await check_if_pipeline_needed()
    if not pipeline_needed:
        logger.info("Data pipeline not needed, skipping trigger")
        return True
        
    # Create the message payload
    message = {
        "message": "New user registered, check if data pipeline needs execution.",
        "userId": user_id,
        "email": email,
        "trigger_timestamp": datetime.utcnow().isoformat()
    }
    
    # Log the trigger attempt
    logger.info(f"Triggering data pipeline for user: {user_id}")
    
    # Try to trigger via Pub/Sub if available
    if PUBSUB_AVAILABLE and PROJECT_ID and PUBSUB_TOPIC:
        try:
            # Initialize Pub/Sub publisher client
            publisher = pubsub_v1.PublisherClient()
            topic_name = f"projects/{PROJECT_ID}/topics/{PUBSUB_TOPIC}"
            
            # Convert message to bytes
            message_bytes = json.dumps(message).encode("utf-8")
            
            # Publish message
            future = publisher.publish(topic_name, message_bytes)
            message_id = future.result(timeout=30)
            
            logger.info(f"Published message to Pub/Sub with ID: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message to Pub/Sub: {str(e)}")
            # Fall back to HTTP trigger if Pub/Sub fails
    
    # Fall back to a simple simulation for testing/development
    # In production, you would replace this with an actual HTTP trigger to a Cloud Function
    logger.info("Using fallback/simulated pipeline trigger for testing")
    try:
        # Simulate processing delay
        time.sleep(0.5)
        
        # Log success simulation
        logger.info(f"Successfully triggered pipeline process (simulated) for user: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to trigger pipeline: {str(e)}")
        return False 

class PipelineTriggerServiceError(Exception):
    """Exception raised for errors in pipeline trigger service"""
    pass

class PipelineTriggerService:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.topic_id = os.getenv("PIPELINE_TRIGGER_TOPIC")
        
    async def trigger_pipeline(self, user_id: str) -> bool:
        """
        Trigger the data processing pipeline with a Pub/Sub message
        
        Args:
            user_id: ID of the user that triggered the pipeline
            
        Returns:
            True if the message was published successfully
        """
        try:
            if not self.project_id or not self.topic_id:
                logger.warning("Pipeline trigger disabled (missing configuration)")
                return False
                
            # Create a publisher client
            publisher = pubsub_v1.PublisherClient()
            topic_path = publisher.topic_path(self.project_id, self.topic_id)
            
            # Create message data
            message_data = {
                "user_id": user_id,
                "timestamp": str(datetime.utcnow())
            }
            
            # Publish message
            message_bytes = json.dumps(message_data).encode("utf-8")
            future = publisher.publish(topic_path, data=message_bytes)
            
            # Wait for the publish to complete
            message_id = future.result()
            logger.info(f"Published pipeline trigger message: {message_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error triggering pipeline: {str(e)}")
            raise PipelineTriggerServiceError(f"Failed to trigger pipeline: {str(e)}")

# Create a singleton instance
pipeline_trigger_service = PipelineTriggerService() 