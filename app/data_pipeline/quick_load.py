#!/usr/bin/env python
"""
A minimal script to load sample movies directly into MongoDB
without requiring additional libraries or generating embeddings.
"""

import os
import json
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import sys
import random

# Load environment variables
load_dotenv()

# Constants
MONGODB_URI = os.getenv("MONGODB_URI")
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Function to create dummy embedding vector
def create_dummy_embedding(seed=None):
    """Create a dummy embedding vector of 384 dimensions"""
    if seed is not None:
        random.seed(seed)
    return [random.uniform(-0.1, 0.1) for _ in range(384)]

# Sample posters for popular movies (from TMDB)
MOVIE_POSTERS = {
    "Toy Story (1995)": {
        "poster_path": "/uXDfjJbdP4ijW5hWSBrPrlKpxab.jpg",
        "backdrop_path": "/dji4Fm0gCDVb9DQQMRvAI8YNnTz.jpg",
        "tmdb_id": 862
    },
    "Jumanji (1995)": {
        "poster_path": "/vgpXmVaVyUL7GGiDeiK1mKEKzcX.jpg",
        "backdrop_path": "/zFs9jos52rYDpQd1c1KP6gRnqCR.jpg",
        "tmdb_id": 8844
    },
    "Grumpier Old Men (1995)": {
        "poster_path": "/1FSXpj5e8l4KH6nVFO5SPUeraOt.jpg",
        "backdrop_path": "/6xrZ4l8UlcuRQK9K5WdTAQ9HW4P.jpg",
        "tmdb_id": 15602
    },
    "Waiting to Exhale (1995)": {
        "poster_path": "/4wjGMwPHKfsvRrQq8rEsRnyFKBx.jpg",
        "backdrop_path": "/19b9UMFyw7MStEUUcZz2UzR4gLi.jpg",
        "tmdb_id": 31357
    },
    "Father of the Bride Part II (1995)": {
        "poster_path": "/rGnhqVy2hk9Hy1YRx8nkORT9YCl.jpg", 
        "backdrop_path": "/9Bwfi8KrnNmHgT7oz6VLgn68aKL.jpg",
        "tmdb_id": 11862
    },
    "Heat (1995)": {
        "poster_path": "/rrBuGu0Pjq7Y2BWSI6teGfZzviY.jpg",
        "backdrop_path": "/rfElr8bIOQlDXKCM2rnTTHSDgzU.jpg",
        "tmdb_id": 949
    },
    "Sabrina (1995)": {
        "poster_path": "/jTAVoSxKbybQ1qbEc4Swbj6A1lC.jpg",
        "backdrop_path": "/nMrMmLvq8jyGgWFiy8F8YAwmMSI.jpg",
        "tmdb_id": 9600
    },
    "Tom and Huck (1995)": {
        "poster_path": "/lZd7Ssf39Y2vRNQhUSwQYVKsOJy.jpg",
        "backdrop_path": "/mQJ3a0IQxFLsv5uhR1zxTkfULfz.jpg",
        "tmdb_id": 45325
    },
    "Sudden Death (1995)": {
        "poster_path": "/s8pQxeBaCiOQIvXVJhDKw2wCVGO.jpg",
        "backdrop_path": "/aEDvRs3rrJU1qOtlXfS5JNwF1Л.jpg",
        "tmdb_id": 9091
    },
    "GoldenEye (1995)": {
        "poster_path": "/5c0ovjfmNnmYTdIhHYr2kmrKFz0.jpg",
        "backdrop_path": "/4XtKUUdaUe476MXjGBIwFHZbKNi.jpg",
        "tmdb_id": 710
    }
}

# Sample movies data
SAMPLE_MOVIES = [
    {
        "movieId_ml": 1,
        "title": "Toy Story (1995)",
        "genres": ["Adventure", "Animation", "Children", "Comedy", "Fantasy"],
        "embedding": create_dummy_embedding(1),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["Toy Story (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["Toy Story (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["Toy Story (1995)"]["tmdb_id"],
        "year": 1995
    },
    {
        "movieId_ml": 2,
        "title": "Jumanji (1995)",
        "genres": ["Adventure", "Children", "Fantasy"],
        "embedding": create_dummy_embedding(2),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["Jumanji (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["Jumanji (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["Jumanji (1995)"]["tmdb_id"],
        "year": 1995
    },
    {
        "movieId_ml": 3,
        "title": "Grumpier Old Men (1995)",
        "genres": ["Comedy", "Romance"],
        "embedding": create_dummy_embedding(3),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["Grumpier Old Men (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["Grumpier Old Men (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["Grumpier Old Men (1995)"]["tmdb_id"],
        "year": 1995
    },
    {
        "movieId_ml": 4,
        "title": "Waiting to Exhale (1995)",
        "genres": ["Comedy", "Drama", "Romance"],
        "embedding": create_dummy_embedding(4),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["Waiting to Exhale (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["Waiting to Exhale (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["Waiting to Exhale (1995)"]["tmdb_id"],
        "year": 1995
    },
    {
        "movieId_ml": 5,
        "title": "Father of the Bride Part II (1995)",
        "genres": ["Comedy"],
        "embedding": create_dummy_embedding(5),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["Father of the Bride Part II (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["Father of the Bride Part II (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["Father of the Bride Part II (1995)"]["tmdb_id"],
        "year": 1995
    },
    {
        "movieId_ml": 6,
        "title": "Heat (1995)",
        "genres": ["Action", "Crime", "Thriller"],
        "embedding": create_dummy_embedding(6),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["Heat (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["Heat (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["Heat (1995)"]["tmdb_id"],
        "year": 1995
    },
    {
        "movieId_ml": 7,
        "title": "Sabrina (1995)",
        "genres": ["Comedy", "Romance"],
        "embedding": create_dummy_embedding(7),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["Sabrina (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["Sabrina (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["Sabrina (1995)"]["tmdb_id"],
        "year": 1995
    },
    {
        "movieId_ml": 8,
        "title": "Tom and Huck (1995)",
        "genres": ["Adventure", "Children"],
        "embedding": create_dummy_embedding(8),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["Tom and Huck (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["Tom and Huck (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["Tom and Huck (1995)"]["tmdb_id"],
        "year": 1995
    },
    {
        "movieId_ml": 9,
        "title": "Sudden Death (1995)",
        "genres": ["Action"],
        "embedding": create_dummy_embedding(9),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["Sudden Death (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["Sudden Death (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["Sudden Death (1995)"]["tmdb_id"],
        "year": 1995
    },
    {
        "movieId_ml": 10,
        "title": "GoldenEye (1995)",
        "genres": ["Action", "Adventure", "Thriller"],
        "embedding": create_dummy_embedding(10),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "poster_path": MOVIE_POSTERS["GoldenEye (1995)"]["poster_path"],
        "backdrop_path": MOVIE_POSTERS["GoldenEye (1995)"]["backdrop_path"],
        "tmdb_id": MOVIE_POSTERS["GoldenEye (1995)"]["tmdb_id"],
        "year": 1995
    }
]

# Sample ratings/interactions
SAMPLE_INTERACTIONS = [
    {
        "userId": "1",
        "movieId_ml": 1,
        "type": "rate",
        "value": 5.0,
        "timestamp": datetime.now()
    },
    {
        "userId": "1",
        "movieId_ml": 3,
        "type": "rate",
        "value": 4.0,
        "timestamp": datetime.now()
    },
    {
        "userId": "2",
        "movieId_ml": 1,
        "type": "rate",
        "value": 3.0,
        "timestamp": datetime.now()
    },
    {
        "userId": "2",
        "movieId_ml": 2,
        "type": "rate",
        "value": 4.0,
        "timestamp": datetime.now()
    },
    {
        "userId": "3",
        "movieId_ml": 5,
        "type": "rate",
        "value": 5.0,
        "timestamp": datetime.now()
    },
    {
        "userId": "3",
        "movieId_ml": 6,
        "type": "rate",
        "value": 4.5,
        "timestamp": datetime.now()
    }
]


def load_to_mongodb(movies, interactions, mongodb_uri=MONGODB_URI):
    """
    Load sample data into MongoDB
    """
    if not mongodb_uri:
        print("MONGODB_URI environment variable not set")
        return False
    
    try:
        client = MongoClient(mongodb_uri)
        db = client.get_database()
        
        # Clear existing collections
        db.movies.delete_many({})
        db.interactions.delete_many({})
        
        # Insert movies
        print(f"Inserting {len(movies)} movies into MongoDB")
        result = db.movies.insert_many(movies)
        print(f"Inserted {len(result.inserted_ids)} movies")
        
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
        print(f"Inserting {len(valid_interactions)} interactions into MongoDB")
        result = db.interactions.insert_many(valid_interactions)
        print(f"Inserted {len(result.inserted_ids)} interactions")
        
        # Create indexes
        print("Creating indexes")
        db.movies.create_index("movieId_ml")
        db.movies.create_index("title")
        db.movies.create_index([("title", "text")])
        db.interactions.create_index("userId")
        db.interactions.create_index("movieId")
        db.interactions.create_index([("userId", 1), ("movieId", 1)])
        
        return True
    except Exception as e:
        print(f"Error loading to MongoDB: {e}")
        return False


def load_sample_data(mongodb_uri=MONGODB_URI):
    """
    Load sample movie data into MongoDB.
    
    Args:
        mongodb_uri: MongoDB connection string
        
    Returns:
        bool: True if successful, False otherwise
    """
    return load_to_mongodb(SAMPLE_MOVIES, SAMPLE_INTERACTIONS, mongodb_uri)

def main():
    """
    Main function to load sample data into MongoDB.
    """
    if not MONGODB_URI:
        print("MONGODB_URI environment variable not set")
        return False
    
    # Load data into MongoDB
    success = load_sample_data()
    
    if success:
        print("Successfully loaded sample movies into MongoDB")
        return True
    else:
        print("Failed to load data into MongoDB")
        return False

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)