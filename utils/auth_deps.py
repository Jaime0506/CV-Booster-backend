from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from models.session import Session
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
from datetime import datetime, timezone
from config.settings import settings
from config.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login-user")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Buscar sesión activa más reciente
    q = await db.execute(
        sa.select(Session).
        where(Session.user_id == user_id).
        where(Session.is_revoked == False).
        where(Session.expires_at > datetime.now(timezone.utc)).
        order_by(Session.created_at.desc()).
        limit(1)
    )
    session = q.scalars().first()
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    # Actualizar last_accessed (no bloqueante)
    session.last_accessed = datetime.now(timezone.utc)
    db.add(session)
    await db.commit()

    # Obtener user
    q2 = await db.execute(sa.select(User).where(User.id == user_id))
    user = q2.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
