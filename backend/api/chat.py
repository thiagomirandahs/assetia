"""Endpoint de chat com o agente IA (Claude com tool use)."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai.agent import responder
from ..core.auth import CurrentUser
from ..core.database import get_db
from ..core.models import ChatMessage
from ..core.schemas import ChatIn, ChatMessageOut, ChatOut

router = APIRouter()


@router.post("", response_model=ChatOut)
def perguntar(
    dados: ChatIn,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """Envia uma pergunta ao agente IA. Persiste user + assistant no banco."""
    # 1) Salva a pergunta
    msg_user = ChatMessage(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role="user",
        conteudo=dados.pergunta,
    )
    db.add(msg_user)
    db.commit()

    # 2) Chama o agente
    try:
        resposta, tool_calls = responder(
            db=db,
            tenant_id=user.tenant_id,
            pergunta=dados.pergunta,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"falha no agente: {e}")

    # 3) Salva a resposta
    msg_bot = ChatMessage(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role="assistant",
        conteudo=resposta,
        tool_calls=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
    )
    db.add(msg_bot)
    db.commit()

    return ChatOut(resposta=resposta, tool_calls=tool_calls)


@router.get("/historico", response_model=list[ChatMessageOut])
def historico(user: CurrentUser, db: Annotated[Session, Depends(get_db)], limit: int = 50):
    """Retorna o historico de chat do usuario."""
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.tenant_id == user.tenant_id, ChatMessage.user_id == user.id)
        .order_by(ChatMessage.criado_em.desc())
        .limit(limit)
        .all()
    )
    return [ChatMessageOut.model_validate(r) for r in rows[::-1]]
