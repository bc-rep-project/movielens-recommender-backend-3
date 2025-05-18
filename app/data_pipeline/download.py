#!/usr/bin/env python
"""
Script to download the MovieLens dataset and save it to GCS.
This script is intended to be run as part of the initial setup process.
This module can be imported and used by other scripts.
"""

import os
import sys
import requests
import zipfile
import io
import tempfile
import logging
import argparse
from pathlib import Path
import shutil
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
MOVIELENS_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
DATASET_PATH = "datasets/movielens"
USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "false").lower() == "true"
LOCAL_DATA_DIR = os.getenv("LOCAL_DATA_DIR", "./data")


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")


def download_movielens(url=MOVIELENS_URL):
    """
    Download the MovieLens dataset from the specified URL
    Returns the content as bytes
    """
    logger.info(f"Downloading MovieLens dataset from {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def save_to_gcs(content, bucket_name, destination_blob_name):
    """
    Save content to Google Cloud Storage
    """
    logger.info(f"Saving dataset to GCS bucket: {bucket_name}/{destination_blob_name}")
    
    try:
        # Import here to avoid errors if the package is not installed
        from google.cloud import storage
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        # Upload content
        blob.upload_from_string(content)
        
        logger.info(f"Dataset saved to {destination_blob_name}")
        return True
    except Exception as e:
        logger.error(f"Error saving to GCS: {e}")
        return False


def save_to_local(content, destination_path):
    """
    Save content to local filesystem
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        logger.info(f"Saving dataset to local path: {destination_path}")
        
        # Write the content to the file
        with open(destination_path, "wb") as f:
            f.write(content)
            
        logger.info(f"Dataset saved to {destination_path}")
        
        # Extract the zip file
        with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
            extract_path = os.path.join(os.path.dirname(destination_path), "ml-latest-small")
            logger.info(f"Extracting dataset to {extract_path}")
            zip_ref.extractall(extract_path)
            
        return True
    except Exception as e:
        logger.error(f"Error saving to local filesystem: {e}")
        return False


def check_if_exists_in_gcs(bucket_name, blob_name):
    """
    Check if a file already exists in GCS
    """
    try:
        from google.cloud import storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()
    except Exception as e:
        logger.error(f"Error checking GCS: {e}")
        return False


def check_if_exists_local(file_path):
    """
    Check if a file already exists locally
    """
    return os.path.exists(file_path)


def download_dataset(force=False, use_local_storage=USE_LOCAL_STORAGE):
    """
    Download the MovieLens dataset and save it to storage.
    
    Args:
        force: Force download even if the file exists
        use_local_storage: Whether to use local storage instead of GCS
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    if use_local_storage:
        # Use local filesystem
        destination_path = os.path.join(LOCAL_DATA_DIR, DATASET_PATH, "ml-latest-small.zip")
        
        # Check if the file already exists
        if not force and check_if_exists_local(destination_path):
            logger.info(f"Dataset already exists at {destination_path}")
            return True
        
        try:
            # Download the dataset
            content = download_movielens()
            
            # Save locally
            success = save_to_local(content, destination_path)
            
            if success:
                logger.info("MovieLens dataset successfully downloaded and saved locally")
                return True
            else:
                logger.error("Failed to save dataset locally")
                return False
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
    else:
        # Use Google Cloud Storage
        if not GCS_BUCKET_NAME:
            logger.error("GCS_BUCKET_NAME environment variable not set")
            return False
        
        destination_blob = f"{DATASET_PATH}/ml-latest-small.zip"
        
        # Check if the file already exists in GCS
        if not force and check_if_exists_in_gcs(GCS_BUCKET_NAME, destination_blob):
            logger.info(f"Dataset already exists at gs://{GCS_BUCKET_NAME}/{destination_blob}")
            return True
        
        try:
            # Download the dataset
            content = download_movielens()
            
            # Save to GCS
            success = save_to_gcs(content, GCS_BUCKET_NAME, destination_blob)
            
            if success:
                logger.info("MovieLens dataset successfully downloaded and saved to GCS")
                return True
            else:
                logger.error("Failed to save dataset to GCS")
                return False
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return False


def main():
    """Main function to download dataset and save to GCS or locally"""
    setup_logging()
    
    parser = argparse.ArgumentParser(description="Download MovieLens dataset and save to storage")
    parser.add_argument("--force", action="store_true", help="Force download even if the file exists")
    args = parser.parse_args()
    
    success = download_dataset(force=args.force)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main() 