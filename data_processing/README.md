# MovieLens Data Processing

This directory contains scripts and utilities for downloading, processing, and loading MovieLens data into the recommender system.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure environment:
   - Copy `.env.sample` to `.env`
   - Fill in required environment variables

## Scripts

The scripts should be run in the following order:

1. `01_download_movielens.py`: Downloads MovieLens dataset from the web and uploads to GCS
2. `02_generate_embeddings.py`: Processes movie data and generates embeddings
3. `03_load_interactions.py`: Loads user interaction data (ratings)
4. `04_update_recommendations.py`: (Optional) Pre-computes recommendations

## Running Locally

```bash
# Run each script in sequence
python scripts/01_download_movielens.py
python scripts/02_generate_embeddings.py
python scripts/03_load_interactions.py
```

## Cloud Deployment

These scripts can be deployed as a Cloud Function triggered by Pub/Sub messages.
See the `cloud_function` directory for deployment details. 