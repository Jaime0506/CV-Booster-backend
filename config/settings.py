# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENROUTER_API_KEY: str
    OPENROUTER_API_BASE: str
    OPENROUTER_MODEL: str

    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    DATABASE_URL: str

    STORAGE_DIR: str
    MAX_UPLOAD_BYTES: int

    class Config:
        env_file = ".env"

settings = Settings()
