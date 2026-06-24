"""Endpoints de autenticacao: login e dados do usuario logado."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.auth import CurrentUser, criar_token, verificar_senha
from ..core.database import get_db
from ..core.models import User
from ..core.schemas import LoginIn, TokenOut, UserOut

router = APIRouter()


@router.post("/login", response_model=TokenOut)
def login(dados: LoginIn, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.email == dados.email).first()
    if not user or not user.ativo or not verificar_senha(dados.senha, user.senha_hash):
        raise HTTPException(status_code=401, detail="credenciais invalidas")
    token = criar_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/eu", response_model=UserOut)
def quem_sou_eu(user: CurrentUser):
    """Retorna o usuario logado (dados do JWT validados)."""
    return UserOut.model_validate(user)
