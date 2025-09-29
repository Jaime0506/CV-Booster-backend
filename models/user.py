import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from config.database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    email = sa.Column(sa.Text, nullable=False, unique=True)
    email_normalized = sa.Column(sa.Text, nullable=False, index=True)
    password_hash = sa.Column(sa.Text, nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False, default=True)
    is_email_confirmed = sa.Column(sa.Boolean, nullable=False, default=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    sessions = relationship("Session", back_populates="user", cascade="all, delete")