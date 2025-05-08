import os
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
    
    # CORS
    CORS_ORIGINS: List[str] = []
    
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Backwards compatibility for BACKEND_CORS_ORIGINS
    BACKEND_CORS_ORIGINS: Optional[str] = None
    
    @field_validator("CORS_ORIGINS", mode="before")
    def use_legacy_cors_if_present(cls, v, info: ValidationInfo):
        backend_cors = info.data.get("BACKEND_CORS_ORIGINS")
        if backend_cors and not v:
            return backend_cors
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
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


settings = Settings() 