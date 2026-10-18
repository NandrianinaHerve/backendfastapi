from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/sante_fianarantsoa"
    POSTGIS_URL: str = "postgresql://postgres:password@localhost:5432/sante_fianarantsoa"
    SECRET_KEY: str = "your-super-secret-key-sante-fianarantsoa-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_URL: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_MODEL: str = "gemini-3.1-flash-lite"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
