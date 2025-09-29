from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from config.settings import settings
from config.database import get_db
from models.user import User
from models.session import Session as SessionModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login-user")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    # 1) decode JWT
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # 2) buscar sesión activa para ese user_id
    now = datetime.now(timezone.utc)
    q = await db.execute(
        select(SessionModel).
        where(SessionModel.user_id == user_id).
        where(SessionModel.is_revoked == False).
        where(or_(SessionModel.expires_at == None, SessionModel.expires_at > now)).
        order_by(SessionModel.created_at.desc()).
        limit(1)
    )
    session = q.scalars().first()
    if not session:
        # no hay sesión activa → token inválido por revocación / expiración
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or revoked")

    # 3) actualizar last_accessed
    session.last_accessed = now
    db.add(session)
    await db.commit()

    # 4) devolver user
    q2 = await db.execute(select(User).where(User.id == user_id))
    user = q2.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user