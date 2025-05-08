import base64
import json
import functions_framework
import os
import sys
import subprocess
import logging
from google.cloud import storage
from pymongo import MongoClient
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection info
MONGODB_URI = os.environ.get("MONGODB_URI")

# GCS bucket for storing dataset
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

# MovieLens dataset URL
MOVIELENS_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"


@functions_framework.cloud_event
def process_data_pipeline(cloud_event):
    """
    Cloud Function triggered by Pub/Sub that checks if data pipeline needs to be run
    and executes it if necessary.
    
    Args:
        cloud_event: The Cloud Event that triggered the function
    
    Returns:
        str: A message indicating success or failure
    """
    # Log the event receipt
    logger.info(f"Received event with ID: {cloud_event['id']}")
    
    # Extract Pub/Sub message from cloud event
    if 'data' in cloud_event:
        try:
            pubsub_message = cloud_event['data']['message']
            
            # Decode base64-encoded message data
            if 'data' in pubsub_message:
                message_data = base64.b64decode(pubsub_message['data']).decode('utf-8')
                message_json = json.loads(message_data)
                
                logger.info(f"Decoded message: {message_json}")
                
                # Extract user info
                user_id = message_json.get('userId', 'unknown')
                user_email = message_json.get('email', 'unknown')
                
                # Check if pipeline is needed
                if not check_if_pipeline_needed():
                    logger.info("Data already exists in MongoDB, skipping pipeline.")
                    return "Pipeline not needed, data already exists"
                
                # Run the pipeline
                logger.info("Starting data pipeline process...")
                
                # Step 1: Download MovieLens dataset
                dataset_path = download_movielens_dataset()
                if not dataset_path:
                    logger.error("Failed to download dataset")
                    return "Pipeline failed at dataset download stage"
                
                # Step 2: Process the dataset and generate embeddings
                if not process_dataset(dataset_path):
                    logger.error("Failed to process dataset")
                    return "Pipeline failed at dataset processing stage"
                
                # Step 3: Load data into MongoDB
                if not load_to_mongodb(dataset_path):
                    logger.error("Failed to load data into MongoDB")
                    return "Pipeline failed at MongoDB loading stage"
                
                logger.info("Data pipeline completed successfully!")
                return "Pipeline executed successfully"
                
            else:
                logger.warning("No data field in Pub/Sub message")
                return "No data in message"
        except Exception as e:
            logger.error(f"Error processing Pub/Sub message: {str(e)}")
            return f"Error: {str(e)}"
    
    logger.warning("No data in cloud event")
    return "No data in event"


def check_if_pipeline_needed():
    """
    Check if the data pipeline needs to be executed by checking if movies collection exists and has data
    
    Returns:
        bool: True if pipeline needs to be run, False otherwise
    """
    if not MONGODB_URI:
        logger.error("MONGODB_URI environment variable not set")
        return False
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI)
        db = client.get_database()
        
        # Check if movies collection exists and has documents
        collections = db.list_collection_names()
        if "movies" in collections:
            # Check if the collection has documents
            count = db.movies.count_documents({})
            if count > 0:
                logger.info(f"Movies collection already has {count} documents, pipeline not needed")
                return False
        
        logger.info("Movies collection empty or doesn't exist, pipeline needed")
        return True
    
    except Exception as e:
        logger.error(f"Error checking if pipeline is needed: {str(e)}")
        # Default to not running pipeline on error to prevent repeated execution
        return False


def download_movielens_dataset():
    """
    Download MovieLens dataset from the URL
    
    Returns:
        str: Path to the downloaded and extracted dataset or None if failed
    """
    try:
        # Create a temporary directory for the dataset
        temp_dir = "/tmp/movielens"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download the dataset using curl
        zip_path = f"{temp_dir}/ml-latest-small.zip"
        download_cmd = f"curl -o {zip_path} {MOVIELENS_URL}"
        
        logger.info(f"Downloading dataset with command: {download_cmd}")
        subprocess.run(download_cmd, shell=True, check=True)
        
        # Extract the zip file
        extract_cmd = f"unzip -o {zip_path} -d {temp_dir}"
        logger.info(f"Extracting dataset with command: {extract_cmd}")
        subprocess.run(extract_cmd, shell=True, check=True)
        
        # Return the path to the extracted directory
        return f"{temp_dir}/ml-latest-small"
    
    except Exception as e:
        logger.error(f"Error downloading MovieLens dataset: {str(e)}")
        return None


def process_dataset(dataset_path):
    """
    Process the dataset and generate embeddings
    
    Args:
        dataset_path: Path to the extracted dataset
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # TODO: Implement embedding generation here
        # This would typically involve:
        # 1. Reading movies.csv
        # 2. Loading a Hugging Face model
        # 3. Generating embeddings for each movie
        # 4. Saving the results
        
        logger.info("Processing dataset (placeholder for actual implementation)")
        
        # For this demo, we'll just return True
        # In a real implementation, you would process the data here
        return True
    
    except Exception as e:
        logger.error(f"Error processing dataset: {str(e)}")
        return False


def load_to_mongodb(dataset_path):
    """
    Load the processed data into MongoDB
    
    Args:
        dataset_path: Path to the extracted dataset
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not MONGODB_URI:
        logger.error("MONGODB_URI environment variable not set")
        return False
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI)
        db = client.get_database()
        
        # Read movies.csv (simplified for demo)
        movies_file = f"{dataset_path}/movies.csv"
        
        # In a real implementation, you would:
        # 1. Read the CSV file
        # 2. Process each row
        # 3. Create movie documents with embeddings
        # 4. Insert them into MongoDB
        
        # For this demo, let's just insert a placeholder document
        db.movies.insert_one({
            "title": "Example Movie",
            "genres": ["Example"],
            "movieId_ml": 1,
            "embedding": [0.1, 0.2, 0.3],  # Placeholder embedding
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        logger.info("Inserted example movie into MongoDB")
        
        # Add a ratings example too
        db.interactions.insert_one({
            "userId": "example-user",
            "movieId": "example-movie-id",
            "type": "rate",
            "value": 5,
            "timestamp": datetime.utcnow()
        })
        
        logger.info("Inserted example interaction into MongoDB")
        
        return True
    
    except Exception as e:
        logger.error(f"Error loading data to MongoDB: {str(e)}")
        return False


# For local testing (won't be used in Cloud Functions)
if __name__ == "__main__":
    print("Testing Cloud Function locally...")
    # Simulate a Cloud Event
    example_event = {
        "id": "test-id",
        "data": {
            "message": {
                "data": base64.b64encode(json.dumps({
                    "message": "New user registered, check if data pipeline needs execution.",
                    "userId": "test-user-id",
                    "email": "test@example.com",
                    "trigger_timestamp": datetime.utcnow().isoformat()
                }).encode("utf-8")).decode("utf-8")
            }
        }
    }
    
    result = process_data_pipeline(example_event)
    print(f"Result: {result}") 