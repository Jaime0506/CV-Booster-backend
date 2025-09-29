import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from config.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    last_accessed = sa.Column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = sa.Column(sa.TIMESTAMP(timezone=True))
    user_agent = sa.Column(sa.Text)
    ip_addr = sa.Column(sa.String)
    is_revoked = sa.Column(sa.Boolean, server_default=sa.text("false"), nullable=False)

    user = sa.relationship("User", back_populates="sessions")


    