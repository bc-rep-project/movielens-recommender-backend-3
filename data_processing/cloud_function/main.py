import functions_framework
from loguru import logger
import json
import os
import sys
import importlib.util
import base64
from datetime import datetime

# Add the project root directory to the path so we can import from common
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
from common.db_connect import get_mongodb_client, get_database

@functions_framework.cloud_event
def process_pipeline_trigger(cloud_event):
    """
    Cloud Function triggered by a Pub/Sub event to run the data pipeline
    
    Args:
        cloud_event: CloudEvent containing the Pub/Sub message
    """
    logger.info("Received pipeline trigger request")
    
    # Decode the Pub/Sub message
    try:
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message_data = json.loads(pubsub_message)
        
        user_id = message_data.get("user_id")
        logger.info(f"Processing pipeline for user: {user_id}")
        
    except Exception as e:
        logger.error(f"Error decoding message: {e}")
        pubsub_message = None
        message_data = {}
    
    # Check if we need to run the pipeline
    try:
        db = get_database()
        
        # Check if we already have movies in the database
        movie_count = db.movies.count_documents({})
        logger.info(f"Found {movie_count} movies in database")
        
        if movie_count > 0:
            logger.info("Movies already loaded, skipping initial data load")
            return "Pipeline not needed, data already exists"
        
        # We need to run the pipeline
        logger.info("Running data pipeline")
        
        # Run the scripts in order
        run_script("01_download_movielens.py")
        run_script("02_generate_embeddings.py")
        run_script("03_load_interactions.py")
        
        logger.info("Pipeline completed successfully")
        return "Pipeline completed successfully"
        
    except Exception as e:
        logger.error(f"Error in pipeline: {e}")
        raise

def run_script(script_name):
    """
    Run a script from the scripts directory
    
    Args:
        script_name: Name of the script file
    """
    logger.info(f"Running script: {script_name}")
    
    # Path to the script
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts",
        script_name
    )
    
    # Check if the script exists
    if not os.path.exists(script_path):
        logger.error(f"Script not found: {script_path}")
        raise FileNotFoundError(f"Script not found: {script_path}")
    
    # Import the script as a module
    spec = importlib.util.spec_from_file_location("script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Run the main function if it exists
    if hasattr(module, "main"):
        module.main()
    else:
        logger.warning(f"Script {script_name} has no main() function") 