import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from config.database import Base

class EmailConfirmation(Base):
    __tablename__ = "email_confirmations"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False)
    consumed = sa.Column(sa.Boolean, nullable=False, default=False)