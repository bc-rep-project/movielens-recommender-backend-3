import os
from google.cloud import storage
from loguru import logger
import tempfile
import requests
import zipfile
from typing import Optional, Tuple

def get_storage_client() -> storage.Client:
    """
    Get Google Cloud Storage client
    
    Returns:
        GCS client instance
    """
    try:
        return storage.Client()
    except Exception as e:
        logger.error(f"Failed to create GCS client: {e}")
        raise

def check_file_exists(bucket_name: str, file_path: str) -> bool:
    """
    Check if a file exists in the specified GCS bucket
    
    Args:
        bucket_name: Name of the GCS bucket
        file_path: Path to the file within the bucket
        
    Returns:
        True if the file exists, False otherwise
    """
    try:
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        return blob.exists()
    except Exception as e:
        logger.error(f"Error checking if file exists: {e}")
        return False

def download_file(bucket_name: str, file_path: str, local_path: str) -> bool:
    """
    Download a file from GCS to a local path
    
    Args:
        bucket_name: Name of the GCS bucket
        file_path: Path to the file within the bucket
        local_path: Local path to save the file to
        
    Returns:
        True if download succeeded, False otherwise
    """
    try:
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        blob.download_to_filename(local_path)
        logger.info(f"Downloaded {file_path} to {local_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading file from GCS: {e}")
        return False

def upload_file(bucket_name: str, file_path: str, local_path: str) -> bool:
    """
    Upload a file from a local path to GCS
    
    Args:
        bucket_name: Name of the GCS bucket
        file_path: Path where the file should be stored in the bucket
        local_path: Local path of the file to upload
        
    Returns:
        True if upload succeeded, False otherwise
    """
    try:
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        blob.upload_from_filename(local_path)
        logger.info(f"Uploaded {local_path} to gs://{bucket_name}/{file_path}")
        return True
    except Exception as e:
        logger.error(f"Error uploading file to GCS: {e}")
        return False

def download_and_upload_to_gcs(url: str, bucket_name: str, file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Download a file from a URL and upload it to GCS
    
    Args:
        url: URL to download from
        bucket_name: Name of the GCS bucket
        file_path: Path where the file should be stored in the bucket
        
    Returns:
        Tuple of (success, local_path if downloaded and successful)
    """
    try:
        # Create a temporary file to download to
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Download the file
        logger.info(f"Downloading {url}")
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download, status code: {response.status_code}")
            return False, None
            
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Upload to GCS
        success = upload_file(bucket_name, file_path, temp_path)
        
        # Return the temp path so caller can use it if needed
        if success:
            return True, temp_path
        else:
            # Clean up the temp file if upload failed
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False, None
            
    except Exception as e:
        logger.error(f"Error in download_and_upload_to_gcs: {e}")
        return False, None 