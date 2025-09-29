# utils/llm_tracker.py
import time
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from models.llmUsage import LLMUsage
from config.settings import settings

class LLMTracker:
    def __init__(self):
        self.start_time = None
        self.request_id = None
    
    def start_tracking(self) -> str:
        """Inicia el tracking de una petición a IA"""
        self.start_time = time.time()
        self.request_id = str(uuid.uuid4())
        return self.request_id
    
    def calculate_latency(self) -> Optional[int]:
        """Calcula la latencia en milisegundos"""
        if self.start_time is None:
            return None
        return int((time.time() - self.start_time) * 1000)
    
    async def log_usage(
        self, 
        db: AsyncSession, 
        user_id: str, 
        model: str, 
        endpoint: str, 
        result: str
    ) -> None:
        """Registra el uso de IA en la base de datos"""
        latency_ms = self.calculate_latency()
        
        stmt = insert(LLMUsage).values(
            user_id=user_id,
            request_id=self.request_id,
            model=model,
            endpoint=endpoint,
            latency_ms=latency_ms,
            result=result
        )
        
        await db.execute(stmt)
        await db.commit()

# Función helper para crear un tracker
def create_tracker() -> LLMTracker:
    return LLMTracker()
