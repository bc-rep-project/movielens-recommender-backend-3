"""
Module to check if movies exist in the MongoDB database.
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB_NAME", "movielens")

def check_movies_exist(mongodb_uri=MONGODB_URI, db_name=DB_NAME, min_count=10):
    """
    Check if movies exist in the database.
    
    Args:
        mongodb_uri: MongoDB connection string
        db_name: Database name
        min_count: Minimum number of movies to consider the database populated
        
    Returns:
        bool: True if movies exist, False otherwise
    """
    try:
        client = MongoClient(mongodb_uri)
        db = client[db_name]
        movie_count = db.movies.count_documents({})
        client.close()
        return movie_count >= min_count
    except Exception as e:
        print(f"Error checking movies in database: {e}")
        return False

def main():
    """
    Command-line interface for checking movies.
    """
    if check_movies_exist():
        print("Movies found in the database.")
        return 0
    else:
        print("Not enough movies found in the database.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())