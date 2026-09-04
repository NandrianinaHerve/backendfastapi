from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/sante_fianarantsoa"
    POSTGIS_URL: str = "postgresql://postgres:password@localhost:5432/sante_fianarantsoa"
    SECRET_KEY: str = "your-super-secret-key-sante-fianarantsoa-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()