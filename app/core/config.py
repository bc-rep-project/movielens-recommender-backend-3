import os
import json
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator, Field, ValidationInfo
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API configuration
    API_PREFIX: str = "/api"
    API_VERSION: str = "v1"
    PROJECT_NAME: str = "MovieLens Recommender API"
    PROJECT_DESCRIPTION: str = "API for movie recommendations based on MovieLens dataset"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET", "your-secret-key-for-development"))
    JWT_SECRET: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS - Adding default value for production failsafe
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://movielens-recommender-frontend.onrender.com", "https://movielens-recommender-frontend-3.vercel.app"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        # If empty value, return default CORS
        if not v:
            return ["http://localhost:3000", "https://movielens-recommender-frontend.onrender.com"]
            
        # Try to parse as JSON first
        if isinstance(v, str):
            try:
                # If string starts with [ and ends with ], try to parse as JSON
                if v.startswith("[") and v.endswith("]"):
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return parsed
            except json.JSONDecodeError:
                # If JSON parsing fails, fall back to comma-separated
                pass
                
            # If not a JSON array, treat as comma-separated
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        # Failsafe return if all parsing fails
        return ["http://localhost:3000", "https://movielens-recommender-frontend.onrender.com"]
    
    # Backwards compatibility for BACKEND_CORS_ORIGINS
    BACKEND_CORS_ORIGINS: Optional[str] = None
    
    @field_validator("CORS_ORIGINS", mode="after")
    def use_legacy_cors_if_present(cls, v, info: ValidationInfo):
        # If CORS_ORIGINS is empty but we have BACKEND_CORS_ORIGINS
        if not v or len(v) == 0:
            backend_cors = info.data.get("BACKEND_CORS_ORIGINS")
            if backend_cors:
                # Process backend_cors if it's not empty
                if isinstance(backend_cors, str):
                    try:
                        # Try to parse as JSON
                        if backend_cors.startswith("[") and backend_cors.endswith("]"):
                            parsed = json.loads(backend_cors)
                            if isinstance(parsed, list):
                                return parsed
                    except json.JSONDecodeError:
                        # If JSON parsing fails, fall back to comma-separated
                        pass
                    
                    # If not a JSON array, treat as comma-separated
                    return [i.strip() for i in backend_cors.split(",")]
                elif isinstance(backend_cors, list):
                    return backend_cors
                    
        # Extra failsafe: if we somehow still have an empty list, provide defaults
        if not v or len(v) == 0:
            return ["http://localhost:3000", "https://movielens-recommender-frontend.onrender.com"]
            
        return v
    
    # Caching
    RECOMMENDATIONS_CACHE_TTL: int = 60 * 60 * 24  # 24 hours
    MOVIE_CACHE_TTL: int = 60 * 60 * 24 * 7  # 7 days
    
    # Recommendation settings
    RECOMMENDATIONS_LIMIT: int = 10
    
    # MongoDB settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "movielens")
    
    # Redis settings
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # Legacy Redis URL - will be parsed if individual settings aren't provided
    REDIS_URL: Optional[str] = None
    
    @field_validator("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", mode="before")
    def parse_redis_url_if_needed(cls, v, info: ValidationInfo):
        # Return the value if already set
        if v:
            return v
            
        # Get Redis URL from the data
        redis_url = info.data.get("REDIS_URL")
        if not redis_url:
            # Return defaults if no Redis URL
            if info.field_name == "REDIS_PASSWORD":
                return None
            elif info.field_name == "REDIS_PORT":
                return 6379
            else:  # REDIS_HOST
                return "localhost"
            
        # Simple parsing of redis://user:password@host:port
        try:
            if "://" in redis_url:
                auth_part = redis_url.split("@")[0].split("://")[1]
                host_part = redis_url.split("@")[1].split(":")[0]
                port_part = redis_url.split(":")[-1]
                
                if info.field_name == "REDIS_HOST":
                    return host_part
                elif info.field_name == "REDIS_PORT":
                    return int(port_part)
                elif info.field_name == "REDIS_PASSWORD":
                    # Format is usually username:password, so get the password part
                    return auth_part.split(":")[1] if ":" in auth_part else auth_part
        except Exception:
            # Fall back to defaults if parsing fails
            if info.field_name == "REDIS_PASSWORD":
                return None
            elif info.field_name == "REDIS_PORT":
                return 6379
            else:  # REDIS_HOST
                return "localhost"
            
        return v
    
    # Supabase settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = Field(default="")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    # Legacy Supabase keys
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    @field_validator("SUPABASE_KEY", mode="before")
    def use_legacy_supabase_key(cls, v, info: ValidationInfo):
        if v:
            return v
        # Try to use anon key if available
        return info.data.get("SUPABASE_ANON_KEY", "")
    
    # Add a field validator to use SUPABASE_KEY as a fallback for service role key
    @field_validator("SUPABASE_SERVICE_ROLE_KEY", mode="before")
    def use_supabase_key_as_service_role(cls, v, info: ValidationInfo):
        if v:
            return v
        # If no service role key is provided, use the regular SUPABASE_KEY
        return info.data.get("SUPABASE_KEY", "")
    
    # Environment
    ENV: str = os.getenv("ENV", "development")
    
    # Hugging Face
    HF_MODEL_NAME: str = os.getenv("HF_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Google Cloud Storage
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # TMDB API Configuration - Add these fields to fix the validation errors
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    TMDB_BASE_URL: str = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3")
    TMDB_IMAGE_BASE_URL: str = os.getenv("TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p/w500")
    
    # Data directories
    LOCAL_DATA_DIR: str = os.getenv("LOCAL_DATA_DIR", "./data")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


settings = Settings() 