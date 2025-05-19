#!/usr/bin/env python
"""
Script to process the MovieLens dataset, generate embeddings, and load data into MongoDB.
This script should be run after download.py has successfully downloaded the dataset to GCS.
"""

import os
import sys
import zipfile
import io
import tempfile
import pandas as pd
import numpy as np
import json
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm
import re
import httpx
import asyncio
import time
from tqdm.asyncio import tqdm as async_tqdm


# Load environment variables
load_dotenv()

# Constants
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
DATASET_PATH = "datasets/movielens"
MONGODB_URI = os.getenv("MONGODB_URI")
HF_MODEL_NAME = os.getenv("HF_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "false").lower() == "true"
LOCAL_DATA_DIR = os.getenv("LOCAL_DATA_DIR", "./data")


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")


def download_from_gcs(bucket_name, source_blob_name):
    """
    Download a file from Google Cloud Storage
    """
    logger.info(f"Downloading from GCS: {bucket_name}/{source_blob_name}")
    
    try:
        # Import here to avoid errors if the package is not installed
        from google.cloud import storage
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        
        content = blob.download_as_bytes()
        logger.info(f"Successfully downloaded {source_blob_name}")
        return content
    except Exception as e:
        logger.error(f"Error downloading from GCS: {e}")
        return None


def read_from_local(file_path):
    """
    Read a file from local filesystem
    """
    logger.info(f"Reading from local file: {file_path}")
    
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        logger.info(f"Successfully read {file_path}")
        return content
    except Exception as e:
        logger.error(f"Error reading local file: {e}")
        return None


def extract_movielens_data(content):
    """
    Extract MovieLens zip file and return DataFrames
    """
    logger.info("Extracting MovieLens dataset")
    
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_ref.extractall(tmp_dir)
                
                # Read the CSV files
                movies_df = pd.read_csv(f"{tmp_dir}/ml-latest-small/movies.csv")
                ratings_df = pd.read_csv(f"{tmp_dir}/ml-latest-small/ratings.csv")
                
                logger.info(f"Extracted {len(movies_df)} movies and {len(ratings_df)} ratings")
                return movies_df, ratings_df
    except Exception as e:
        logger.error(f"Error extracting dataset: {e}")
        return None, None


def extract_from_directory(directory_path):
    """
    Extract MovieLens data from an already extracted directory
    """
    logger.info(f"Reading MovieLens data from directory: {directory_path}")
    
    try:
        # Read the CSV files
        movies_df = pd.read_csv(f"{directory_path}/movies.csv")
        ratings_df = pd.read_csv(f"{directory_path}/ratings.csv")
        
        logger.info(f"Read {len(movies_df)} movies and {len(ratings_df)} ratings")
        return movies_df, ratings_df
    except Exception as e:
        logger.error(f"Error reading dataset from directory: {e}")
        return None, None


def preprocess_movies(movies_df):
    """
    Preprocess movies data
    """
    logger.info("Preprocessing movies data")
    
    # Convert 'genres' from string to list
    movies_df['genres'] = movies_df['genres'].apply(lambda x: x.split('|') if x != '(no genres listed)' else [])
    
    # Create text representation for embedding generation
    movies_df['text_for_embedding'] = movies_df.apply(
        lambda row: f"{row['title']} {' '.join(row['genres'])}", 
        axis=1
    )
    
    return movies_df


def generate_embeddings(movies_df, model_name=HF_MODEL_NAME, batch_size=32):
    """
    Generate embeddings for movies using Hugging Face model
    """
    logger.info(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Get text representations
    texts = movies_df['text_for_embedding'].tolist()
    
    logger.info(f"Generating embeddings for {len(texts)} movies")
    
    # Process in batches to manage memory
    embeddings = []
    for i in tqdm(range(0, len(texts), batch_size)):
        batch_texts = texts[i:i+batch_size]
        batch_embeddings = model.encode(batch_texts, show_progress_bar=False)
        embeddings.extend(batch_embeddings.tolist())
    
    # Add embeddings to DataFrame
    movies_df['embedding'] = embeddings
    
    logger.info(f"Generated {len(embeddings)} embeddings")
    return movies_df


async def fetch_movie_poster(movie_title, movie_year=None, api_key=None):
    """
    Fetch movie poster from TMDB API
    
    Args:
        movie_title: Title of the movie
        movie_year: Optional release year
        api_key: TMDB API key
        
    Returns:
        Tuple of (poster_path, backdrop_path, tmdb_id)
    """
    if not api_key:
        return None, None, None
        
    # Extract year from title if not provided
    if movie_year is None and re.search(r"\((\d{4})\)$", movie_title):
        year_match = re.search(r"\((\d{4})\)$", movie_title)
        movie_year = int(year_match.group(1))
        # Clean title
        clean_title = re.sub(r"\s*\(\d{4}\)$", "", movie_title)
    else:
        clean_title = movie_title
    
    # Prepare API request
    base_url = "https://api.themoviedb.org/3"
    params = {
        "api_key": api_key,
        "query": clean_title,
        "language": "en-US",
        "include_adult": "false",
        "page": "1"
    }
    
    if movie_year:
        params["year"] = str(movie_year)
    
    try:
        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/search/movie",
                params=params,
                timeout=10.0
            )
            
            if response.status_code != 200:
                logger.error(f"TMDB API error: {response.status_code}")
                return None, None, None
                
            data = response.json()
            
            # Check if we have results
            if not data.get("results") or len(data["results"]) == 0:
                return None, None, None
                
            # Get first result
            movie = data["results"][0]
            
            return movie.get("poster_path"), movie.get("backdrop_path"), movie.get("id")
            
    except Exception as e:
        logger.error(f"Error fetching poster for {movie_title}: {e}")
        return None, None, None


async def prepare_movies_with_posters(movies_df, tmdb_api_key=None):
    """
    Prepare movies with poster data from TMDB
    """
    logger.info("Enriching movies with poster data from TMDB")
    
    if not tmdb_api_key:
        logger.warning("TMDB_API_KEY not provided, skipping poster fetching")
        movies_df['poster_path'] = None
        movies_df['backdrop_path'] = None
        movies_df['tmdb_id'] = None
        return movies_df
    
    # Create columns for poster data
    movies_df['poster_path'] = None
    movies_df['backdrop_path'] = None  
    movies_df['tmdb_id'] = None
    
    # Extract year from title if available
    movies_df['year'] = movies_df['title'].str.extract(r'\((\d{4})\)$').astype('float').astype('Int64')
    
    # Process in batches with rate limiting
    batch_size = 5  # Process 5 movies at a time
    rate_limit = 0.5  # Wait 0.5 seconds between batches
    movies_processed = 0
    
    for i in range(0, len(movies_df), batch_size):
        batch = movies_df.iloc[i:i+batch_size]
        tasks = []
        
        for idx, row in batch.iterrows():
            task = fetch_movie_poster(row['title'], row.get('year'), tmdb_api_key)
            tasks.append(task)
        
        # Run batch of tasks
        results = await asyncio.gather(*tasks)
        
        # Update dataframe with results
        for j, (poster_path, backdrop_path, tmdb_id) in enumerate(results):
            if i+j < len(movies_df):
                movies_df.at[i+j, 'poster_path'] = poster_path
                movies_df.at[i+j, 'backdrop_path'] = backdrop_path
                movies_df.at[i+j, 'tmdb_id'] = tmdb_id
        
        movies_processed += len(batch)
        logger.info(f"Processed {movies_processed}/{len(movies_df)} movies")
        
        # Rate limiting
        await asyncio.sleep(rate_limit)
    
    # Log results
    poster_count = movies_df['poster_path'].notna().sum()
    logger.info(f"Found posters for {poster_count} out of {len(movies_df)} movies")
    
    return movies_df


def prepare_movies_for_mongodb(movies_df):
    """
    Prepare movies data for loading into MongoDB
    """
    movies = []
    for _, row in movies_df.iterrows():
        movie = {
            "movieId_ml": int(row['movieId']),  # Original MovieLens ID
            "title": row['title'],
            "genres": row['genres'],
            "embedding": row['embedding'],
            "created_at": pd.Timestamp.now(),
            "updated_at": pd.Timestamp.now(),
            "poster_path": row.get('poster_path'),
            "backdrop_path": row.get('backdrop_path'),
            "tmdb_id": row.get('tmdb_id'),
            "year": row.get('year')
        }
        movies.append(movie)
    
    return movies


def prepare_ratings_for_mongodb(ratings_df):
    """
    Prepare ratings data for loading into MongoDB as interactions
    """
    interactions = []
    for _, row in ratings_df.iterrows():
        interaction = {
            "userId": str(int(row['userId'])),  # Convert to string for consistent ID format
            "movieId_ml": int(row['movieId']),  # We'll need to map this to MongoDB _id later
            "type": "rate",
            "value": float(row['rating']),
            "timestamp": pd.Timestamp.fromtimestamp(row['timestamp'])
        }
        interactions.append(interaction)
    
    return interactions


def load_to_mongodb(movies, interactions, mongodb_uri=MONGODB_URI):
    """
    Load data into MongoDB
    """
    if not mongodb_uri:
        logger.error("MONGODB_URI environment variable not set")
        return False
    
    try:
        client = MongoClient(mongodb_uri)
        db = client.get_database()
        
        # Clear existing collections (optional, be careful in production)
        db.movies.delete_many({})
        db.interactions.delete_many({})
        
        # Insert movies
        logger.info(f"Inserting {len(movies)} movies into MongoDB")
        result = db.movies.insert_many(movies)
        logger.info(f"Inserted {len(result.inserted_ids)} movies")
        
        # Create a map of MovieLens IDs to MongoDB _ids
        movie_id_map = {}
        cursor = db.movies.find({}, {"_id": 1, "movieId_ml": 1})
        for doc in cursor:
            movie_id_map[doc["movieId_ml"]] = doc["_id"]
        
        # Update interactions with MongoDB movie _ids
        valid_interactions = []
        for interaction in interactions:
            movieId_ml = interaction.pop("movieId_ml")
            if movieId_ml in movie_id_map:
                interaction["movieId"] = str(movie_id_map[movieId_ml])
                valid_interactions.append(interaction)
        
        # Insert interactions
        logger.info(f"Inserting {len(valid_interactions)} interactions into MongoDB")
        result = db.interactions.insert_many(valid_interactions)
        logger.info(f"Inserted {len(result.inserted_ids)} interactions")
        
        # Create indexes
        logger.info("Creating indexes")
        db.movies.create_index("movieId_ml")
        db.movies.create_index("title")
        db.movies.create_index([("title", "text")])
        db.interactions.create_index("userId")
        db.interactions.create_index("movieId")
        db.interactions.create_index([("userId", 1), ("movieId", 1)])
        
        return True
    except Exception as e:
        logger.error(f"Error loading to MongoDB: {e}")
        return False


async def main_async():
    """Async main function to process dataset"""
    setup_logging()
    
    parser = argparse.ArgumentParser(description="Process MovieLens dataset and generate embeddings")
    parser.add_argument("--force", action="store_true", help="Force processing even if data exists in MongoDB")
    args = parser.parse_args()
    
    if not MONGODB_URI:
        logger.error("MONGODB_URI environment variable not set")
        sys.exit(1)
    
    if USE_LOCAL_STORAGE:
        # Use local filesystem
        extract_dir = os.path.join(LOCAL_DATA_DIR, DATASET_PATH, "ml-latest-small")
        zip_path = os.path.join(LOCAL_DATA_DIR, DATASET_PATH, "ml-latest-small.zip")
        
        if os.path.exists(extract_dir):
            # Use already extracted directory
            movies_df, ratings_df = extract_from_directory(extract_dir)
        elif os.path.exists(zip_path):
            # Use the zip file
            content = read_from_local(zip_path)
            if not content:
                logger.error(f"Failed to read dataset from {zip_path}")
                sys.exit(1)
            movies_df, ratings_df = extract_movielens_data(content)
        else:
            logger.error(f"MovieLens dataset not found at {extract_dir} or {zip_path}")
            logger.info("Please run download.py first to download the dataset")
            sys.exit(1)
    else:
        # Use Google Cloud Storage
        if not GCS_BUCKET_NAME:
            logger.error("GCS_BUCKET_NAME environment variable not set")
            sys.exit(1)
        
        source_blob = f"{DATASET_PATH}/ml-latest-small.zip"
        
        # Download dataset from GCS
        content = download_from_gcs(GCS_BUCKET_NAME, source_blob)
        if not content:
            logger.error(f"Failed to download dataset from gs://{GCS_BUCKET_NAME}/{source_blob}")
            sys.exit(1)
        
        # Extract data
        movies_df, ratings_df = extract_movielens_data(content)
    
    if movies_df is None or ratings_df is None:
        logger.error("Failed to extract dataset")
        sys.exit(1)
    
    # Preprocess movies data
    movies_df = preprocess_movies(movies_df)
    
    # Get TMDB API key
    tmdb_api_key = os.getenv("TMDB_API_KEY")
    
    # Enrich movies with poster data
    movies_df = await prepare_movies_with_posters(movies_df, tmdb_api_key)
    
    # Generate embeddings
    movies_df = generate_embeddings(movies_df)
    
    # Prepare data for MongoDB
    movies = prepare_movies_for_mongodb(movies_df)
    interactions = prepare_ratings_for_mongodb(ratings_df)
    
    # Load data into MongoDB
    success = load_to_mongodb(movies, interactions)
    
    if success:
        logger.info("Successfully processed MovieLens dataset and loaded into MongoDB")
    else:
        logger.error("Failed to load data into MongoDB")
        sys.exit(1)


def main():
    """Main function to process the MovieLens dataset"""
    # Use asyncio to run the main_async function
    asyncio.run(main_async())


def process_movielens_data():
    """
    Process the MovieLens dataset and load it into MongoDB.
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Set up logging
        setup_logging()
        
        # Extract data paths
        movielens_dir = os.getenv("MOVIELENS_DATA_DIR", "ml-latest-small")
        
        # Extract data from MovieLens dataset
        logger.info(f"Extracting data from {movielens_dir}...")
        if os.path.isdir(movielens_dir):
            movies_df, ratings_df = extract_from_directory(movielens_dir)
        else:
            # Try to download if directory doesn't exist
            logger.warning(f"Directory {movielens_dir} not found, attempting to download dataset...")
            if USE_LOCAL_STORAGE:
                zip_path = os.path.join(LOCAL_DATA_DIR, DATASET_PATH, "ml-latest-small.zip")
                if os.path.exists(zip_path):
                    content = read_from_local(zip_path)
                else:
                    logger.error(f"ZIP file not found at {zip_path}")
                    return False
            else:
                content = download_from_gcs(GCS_BUCKET_NAME, f"{DATASET_PATH}/ml-latest-small.zip")
            
            if not content:
                logger.error("Failed to obtain dataset content")
                return False
                
            movies_df, ratings_df = extract_movielens_data(content)
            
        if movies_df is None or ratings_df is None:
            logger.error("Failed to extract MovieLens data")
            return False
            
        # Preprocess movies
        movies_df = preprocess_movies(movies_df)
        
        # Generate embeddings
        movies_df = generate_embeddings(movies_df)
        
        # Prepare movies with posters if TMDB API key is available
        tmdb_api_key = os.getenv("TMDB_API_KEY")
        if tmdb_api_key:
            logger.info("Enriching movies with poster data from TMDB...")
            # Run the async function in the event loop
            loop = asyncio.get_event_loop()
            movies_df = loop.run_until_complete(prepare_movies_with_posters(movies_df, tmdb_api_key))
        else:
            logger.warning("TMDB_API_KEY not set. Posters will not be fetched.")
        
        # Process data for MongoDB
        logger.info("Preparing data for MongoDB...")
        movies = prepare_movies_for_mongodb(movies_df)
        interactions = prepare_ratings_for_mongodb(ratings_df)
        
        # Load data into MongoDB
        logger.info("Loading data into MongoDB...")
        load_to_mongodb(movies, interactions)
        
        logger.info("MovieLens data processing completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error processing MovieLens data: {e}")
        return False


if __name__ == "__main__":
    main() 