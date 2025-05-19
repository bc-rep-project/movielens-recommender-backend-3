# MovieLens Direct Download Solution

This document explains the implementation of the direct download solution for the MovieLens recommender system, allowing it to work without Google Cloud Storage (GCS) dependencies.

## Solution Overview

Two complementary approaches have been implemented:

1. **Direct Download from MovieLens Website**: Added functionality to download the dataset directly from the MovieLens website when GCS is not available.

2. **Local Storage Configuration**: Configured the system to use local storage for datasets, making it independent of cloud storage.

## Implementation Details

### 1. Direct Download Function

A new function `download_from_movielens()` has been added to `backend/app/data_pipeline/process.py` that:

- Downloads the ML-latest-small dataset directly from the MovieLens website
- Saves the file to a local directory for future use
- Returns the content for immediate processing

### 2. Fallback Mechanism

The `process_movielens_data()` function has been updated to use a tiered approach:

1. First, it checks if the dataset is already extracted locally
2. If not, it checks for a local zip file
3. If no local file exists, it tries GCS (for backward compatibility)
4. If GCS fails, it downloads directly from MovieLens
5. If all attempts fail, it returns an error

### 3. Local Storage Configuration

The `.env` file has been updated with:

```
USE_LOCAL_STORAGE=true
LOCAL_DATA_DIR=./app/data
```

### 4. Directory Structure

The necessary directory structure has been created:

```
backend/app/data/datasets/movielens/
```

## Usage Instructions

### Deployment with Pre-downloaded Dataset

For the most reliable deployment (especially in environments with limited internet access):

1. **Pre-download the dataset**:
   ```bash
   mkdir -p backend/app/data/datasets/movielens
   cd backend/app/data/datasets/movielens
   curl -O https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
   ```

2. **Extract the dataset (optional)**:
   ```bash
   mkdir -p ml-latest-small
   unzip ml-latest-small.zip -d .
   ```

3. **Deploy your application**:
   Ensure the `backend/app/data` directory and its contents are included in your deployment package.

### Deployment with Automatic Download

If your deployment environment has internet access:

1. Simply ensure `.env` has the following settings:
   ```
   USE_LOCAL_STORAGE=true
   LOCAL_DATA_DIR=./app/data
   USE_FULL_DATASET=true
   ```

2. The first time the application starts, it will automatically download the dataset from MovieLens.

## Troubleshooting

### Network Issues

If you encounter network issues when downloading from MovieLens:

1. **Check Connectivity**:
   ```bash
   curl -I https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
   ```

2. **Check Proxy Settings**:
   If you're behind a proxy, set the appropriate environment variables:
   ```bash
   export HTTP_PROXY=http://your-proxy:port
   export HTTPS_PROXY=http://your-proxy:port
   ```

### Permission Issues

If you encounter permission issues:

1. **Check Directory Permissions**:
   ```bash
   ls -la backend/app/data
   ```

2. **Set Proper Permissions**:
   ```bash
   chmod -R 755 backend/app/data
   ```

## Maintenance

To update to a newer version of the MovieLens dataset:

1. Delete the existing dataset:
   ```bash
   rm -rf backend/app/data/datasets/movielens/ml-latest-small
   rm backend/app/data/datasets/movielens/ml-latest-small.zip
   ```

2. Restart the application to trigger a fresh download, or manually download the new version. 