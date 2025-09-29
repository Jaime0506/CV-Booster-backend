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
    endpoint = sa.Column(sa.Text)
    prompt_tokens = sa.Column(sa.Integer, nullable=False, default=0)
    completion_tokens = sa.Column(sa.Integer, nullable=False, default=0)
    total_tokens = sa.Column(sa.Integer, nullable=False)
    n_requests = sa.Column(sa.Integer, nullable=False, default=1)
    cost_estimate = sa.Column(sa.Numeric(18,8), default=0)
    latency_ms = sa.Column(sa.Integer)
    status = sa.Column(sa.Text)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    meta = sa.Column(sa.JSON)