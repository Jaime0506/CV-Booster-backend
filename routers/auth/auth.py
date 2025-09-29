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
from datetime import datetime, timedelta
from utils.jwt_utils import create_access_token
import jwt
from jwt.exceptions import JWTError
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

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

@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")

        session = db.query(Session).filter(
            Session.user_id == user_id,
            Session.is_revoked == False
        ).order_by(Session.created_at.desc()).first()

        if not session:
            raise HTTPException(status_code=404, detail="No active session found")

        session.is_revoked = True
        db.commit()

        return {"message": "Logged out successfully"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/login")
def login(login_data: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not bcrypt.verify(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Crear token JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    # Guardar sesión en DB
    session_entry = Session(
        user_id=user.id,
        expires_at=datetime.utcnow() + access_token_expires,
        ip_addr=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    db.add(session_entry)
    db.commit()

    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Validar sesión activa
        session = db.query(Session).filter(
            Session.user_id == user_id,
            Session.is_revoked == False,
            Session.expires_at > datetime.utcnow()
        ).order_by(Session.created_at.desc()).first()

        if not session:
            raise HTTPException(status_code=401, detail="Session expired or revoked")

        # Update last_accessed
        session.last_accessed = datetime.utcnow()
        db.commit()

        return db.query(User).filter(User.id == user_id).first()
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
