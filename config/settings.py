# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENROUTER_API_KEY: str
    OPENROUTER_API_BASE: str
    OPENROUTER_MODEL: str

    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    STORAGE_DIR: str
    MAX_UPLOAD_BYTES: int

    DATABASE_URL: str

    # --- SMTP & email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASS: str | None = None
    FROM_EMAIL: str | None = None

    # para HMAC de códigos u otros secrets
    SECRET_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
