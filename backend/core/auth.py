"""Autenticacao: hash de senha (bcrypt) + JWT (HS256) + dependencia FastAPI."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_senha(senha: str) -> str:
    return pwd_ctx.hash(senha)


def verificar_senha(senha: str, hash_: str) -> bool:
    return pwd_ctx.verify(senha, hash_)


def criar_token(*, user_id: int, tenant_id: int, role: str) -> str:
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expire_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decodificar_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"token invalido: {e}")


def current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Dependency: extrai o usuario logado do JWT."""
    payload = decodificar_token(token)
    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if not user or not user.ativo:
        raise HTTPException(status_code=401, detail="usuario nao encontrado ou inativo")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
