from fastapi import APIRouter, Request
from config.settings import settings
from models.session import Session
from schemes.schemes import RegisterIn, RegisterOut, LoginIn, TokenOut
from config.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException
from models.user import User
import sqlalchemy as sa
import bcrypt
from datetime import datetime, timedelta, timezone
from utils.jwt_utils import create_access_token
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login-user")

@router.post("/register-user", response_model=RegisterOut)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    # normaliza el email
    normalized = payload.email.strip().lower()

    # verifica si existe
    q = sa.select(User).where(User.email_normalized == normalized)
    existing = (await db.execute(q)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # hashear password
    hashed = bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode()

    # crear usuario (ya confirmado)
    user = User(
        email=payload.email,
        email_normalized=normalized,
        password_hash=hashed,
        is_active=True,
        is_email_confirmed=True,   # <-- aquí forzamos confirmado
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"id": str(user.id), "email": user.email}

@router.post("/logout-user")
async def logout(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # marca la sesión más reciente como revocada
    q = await db.execute(
        sa.select(Session).
        where(Session.user_id == user_id).
        where(Session.is_revoked == False).
        order_by(Session.created_at.desc()).
        limit(1)
    )
    session = q.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    session.is_revoked = True
    db.add(session)
    await db.commit()

    return {"ok": True, "message": "Logged out"}



@router.post("/login-user", response_model=TokenOut)
async def login(payload: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    normalized = payload.email.strip().lower()

    q = await db.execute(sa.select(User).where(User.email_normalized == normalized))
    user = q.scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # verifica password (passlib/bcrypt)
    if not bcrypt.checkpw(payload.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # token JWT
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"sub": str(user.id)}, expires_delta=expires)

    # crear sesión en BD (sys.sessions)
    from uuid import uuid4
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    expires_at = now + expires

    stmt = sa.insert(Session).values(
        id=session_id,
        user_id=user.id,
        created_at=now,
        last_accessed=now,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent"),
        ip_addr=request.client.host if request.client else None,
        is_revoked=False
    )
    await db.execute(stmt)
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer"}


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
