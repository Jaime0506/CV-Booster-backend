import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from config.database import Base

class LLMUsage(Base):
    __tablename__ = "llm_usage"
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    request_id = sa.Column(UUID(as_uuid=True))
    model = sa.Column(sa.Text, nullable=False)
    endpoint = sa.Column(sa.Text, nullable=False)
    latency_ms = sa.Column(sa.Integer)
    result = sa.Column(sa.Text)  # Lo que generó la IA
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=func.now())