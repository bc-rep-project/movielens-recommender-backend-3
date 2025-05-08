# MovieLens Recommender API Backend

A FastAPI backend for a movie recommendation system using the MovieLens dataset.

## Features

- RESTful API for movies, user interactions, and personalized recommendations
- Authentication using JWT tokens
- Caching for improved performance
- Repository pattern for data access
- Content-based recommendations using movie embeddings

## Architecture

This project follows a layered architecture:

1. **API Layer** (`app/api/endpoints`): Handles HTTP requests and responses
2. **Service Layer** (`app/services`): Contains business logic and coordinates between repositories
3. **Data Access Layer** (`app/data_access`): Abstracts database and cache interactions
4. **Core** (`app/core`): Central components like configuration and security
5. **Models** (`app/models`): Pydantic models for data validation

## Getting Started

### Prerequisites

- Python 3.8+
- MongoDB
- Redis (optional but recommended for caching)
- Supabase account (for authentication)

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file based on `.env.example`
4. Start the server: `uvicorn app.main:app --reload`

### Environment Variables

Key environment variables include:

- `MONGODB_URI`: MongoDB connection string
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`: Redis connection details
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET`: Supabase configuration

## API Documentation

When the server is running, visit `/api/docs` for the Swagger UI documentation.

### Key Endpoints

- `/api/health`: System health check
- `/api/auth/register`, `/api/auth/login`: Authentication endpoints
- `/api/movies`: Movie browsing and details
- `/api/interactions`: User interactions (ratings, views)
- `/api/recommendations`: Personalized movie recommendations

## Data Processing

The system includes data processing scripts to:

1. Download the MovieLens dataset
2. Generate embeddings for movies
3. Load interactions data

To run the full pipeline: `python -m data_processing.scripts.01_download_movielens`

## Testing

Run tests with pytest: `pytest`

## Deployment

This project is designed to be deployed on Google Cloud:

- API: Google Cloud Run
- Data Processing: Google Cloud Functions
- Storage: Cloud Storage + MongoDB Atlas
- Caching: Redis Cloud

See `cloudbuild.yaml` for CI/CD configuration.

## License

MIT 