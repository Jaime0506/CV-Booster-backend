# config/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL no está definido en .env")

# Crear engine async
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # pon False en producción si no quieres logs SQL
    future=True
)

# Session local async
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base para tus modelos
Base = declarative_base()

Base.metadata.schema = "sys"

# Dependency para FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
