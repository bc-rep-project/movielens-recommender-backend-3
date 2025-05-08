import os
import sys
import uvicorn
from fastapi import FastAPI

# Print debug info at startup
print(f"Starting application!")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")
print(f"PYTHONPATH: {sys.path}")
print(f"Environment variables: PORT={os.environ.get('PORT', 'not set')}")

# Create app
app = FastAPI(title="MovieLens Recommender API (Simple Version)")

@app.get("/")
def read_root():
    return {
        "status": "ok", 
        "message": "MovieLens Recommender API is running in direct mode!",
        "environment": {
            "PORT": os.environ.get("PORT", "Not set"),
            "PWD": os.environ.get("PWD", "Not set"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", "Not set"),
        }
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

# This will be executed when the file is run directly
if __name__ == "__main__":
    # Get the PORT from environment variable or default to 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting uvicorn server on port {port}")
    
    # Start Uvicorn directly
    uvicorn.run(app, host="0.0.0.0", port=port) 