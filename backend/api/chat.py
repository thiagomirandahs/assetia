"""Endpoint de chat com o agente IA (tool use). Suporta resposta unica e streaming (SSE)."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..ai.agent import responder, responder_stream
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


@router.post("/stream")
def perguntar_stream(
    dados: ChatIn,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """Igual ao /chat, mas transmite a resposta via SSE (Server-Sent Events).

    Cada frame e uma linha `data: {json}\\n\\n`, onde o JSON tem um campo `tipo`:
      - "tool"  -> {"tipo":"tool","tool":nome,"input":{...}}
      - "token" -> {"tipo":"token","texto":"..."}
      - "fim"   -> {"tipo":"fim","resposta":"...","tool_calls":[...]}
      - "erro"  -> {"tipo":"erro","detail":"..."}
    """
    # 1) Salva a pergunta
    msg_user = ChatMessage(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role="user",
        conteudo=dados.pergunta,
    )
    db.add(msg_user)
    db.commit()

    def gerar():
        resposta_final = ""
        tool_calls_final: list = []
        try:
            for ev in responder_stream(db=db, tenant_id=user.tenant_id, pergunta=dados.pergunta):
                if ev.get("tipo") == "fim":
                    resposta_final = ev.get("resposta", "")
                    tool_calls_final = ev.get("tool_calls", [])
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001
            resposta_final = resposta_final or f"[erro: {e}]"
            yield f"data: {json.dumps({'tipo': 'erro', 'detail': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            # 3) Persiste a resposta do assistente (mesmo em caso de erro parcial)
            msg_bot = ChatMessage(
                tenant_id=user.tenant_id,
                user_id=user.id,
                role="assistant",
                conteudo=resposta_final or "(sem resposta)",
                tool_calls=json.dumps(tool_calls_final, ensure_ascii=False) if tool_calls_final else None,
            )
            db.add(msg_bot)
            db.commit()

    return StreamingResponse(
        gerar(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # desliga buffering em nginx
        },
    )


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
