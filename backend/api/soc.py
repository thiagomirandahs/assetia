"""SOC Mode — ingestão e feed de eventos de log (defensivo).

USO: seus próprios logs (Windows Event, syslog de firewall/switch, etc.).
Fase 1: receber + armazenar + feed ao vivo. Correlação por IA via o agente (tool eventos_recentes).
"""
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.auth import CurrentUser
from ..core.database import SessionLocal, get_db
from ..core.models import EventoLog

router = APIRouter()

_SEV = ("info", "warning", "critical")


class EventoIn(BaseModel):
    fonte: str
    mensagem: str
    host: str | None = None
    severidade: str = "info"
    raw: str | None = None
    ts: datetime | None = None


def _ev(r: EventoLog) -> dict:
    return {
        "id": r.id,
        "ts": r.ts.isoformat() if r.ts else None,
        "fonte": r.fonte,
        "host": r.host,
        "severidade": r.severidade,
        "mensagem": r.mensagem,
    }


@router.post("/ingest")
def ingest(eventos: list[EventoIn], user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    """Recebe um lote de eventos de log e grava."""
    n = 0
    for e in eventos:
        db.add(EventoLog(
            tenant_id=user.tenant_id,
            fonte=e.fonte[:60],
            host=e.host or None,
            severidade=e.severidade if e.severidade in _SEV else "info",
            mensagem=e.mensagem,
            raw=e.raw,
            ts=e.ts or datetime.now(timezone.utc),
        ))
        n += 1
    db.commit()
    return {"ingeridos": n}


@router.get("/eventos")
def eventos(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = 100,
    severidade: str | None = None,
    fonte: str | None = None,
):
    q = db.query(EventoLog).filter(EventoLog.tenant_id == user.tenant_id)
    if severidade:
        q = q.filter(EventoLog.severidade == severidade)
    if fonte:
        q = q.filter(EventoLog.fonte == fonte)
    rows = q.order_by(EventoLog.id.desc()).limit(limit).all()
    return {"total": q.count(), "eventos": [_ev(r) for r in rows]}


@router.get("/stream")
def stream(user: CurrentUser):
    """Feed AO VIVO (SSE): emite eventos novos conforme chegam."""
    tid = user.tenant_id

    def gerar():
        db = SessionLocal()
        try:
            ult = db.query(EventoLog.id).filter(EventoLog.tenant_id == tid).order_by(EventoLog.id.desc()).first()
            ultimo_id = ult[0] if ult else 0
            while True:
                db.rollback()  # nova transação -> enxerga commits de outras sessões
                novos = (
                    db.query(EventoLog)
                    .filter(EventoLog.tenant_id == tid, EventoLog.id > ultimo_id)
                    .order_by(EventoLog.id.asc())
                    .limit(50)
                    .all()
                )
                for r in novos:
                    ultimo_id = r.id
                    yield f"data: {json.dumps(_ev(r), ensure_ascii=False)}\n\n"
                time.sleep(1.5)
        except (GeneratorExit, Exception):  # noqa: BLE001 — cliente desconectou
            return
        finally:
            db.close()

    return StreamingResponse(
        gerar(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# Cadeia de ataque fictícia para demonstrar a correlação (login → scan → PS → dump → lateral).
_DEMO = [
    ("windows", "WS-FINANCE", "warning", "Falha de logon (4625) usuário 'admin' de 10.10.20.55"),
    ("windows", "WS-FINANCE", "warning", "Falha de logon (4625) usuário 'admin' de 10.10.20.55"),
    ("windows", "WS-FINANCE", "warning", "Falha de logon (4625) usuário 'admin' de 10.10.20.55 (5x em 1 min)"),
    ("firewall", "FW-EDGE", "warning", "Port scan detectado de 10.10.20.55 para 10.10.10.0/24 (1024 portas)"),
    ("windows", "WS-FINANCE", "critical", "PowerShell com -enc (comando codificado) iniciado por processo incomum"),
    ("windows", "SRV-DC01", "critical", "Acesso ao LSASS (possível dump de credenciais) por processo não assinado"),
    ("windows", "SRV-FILE", "critical", "Logon remoto (tipo 3) com hash NTLM reutilizado — possível pass-the-hash"),
]


@router.post("/seed-demo")
def seed_demo(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    """Injeta uma cadeia de ataque fictícia para testar o feed e a correlação por IA."""
    agora = datetime.now(timezone.utc)
    for i, (fonte, host, sev, msg) in enumerate(_DEMO):
        db.add(EventoLog(
            tenant_id=user.tenant_id, fonte=fonte, host=host, severidade=sev,
            mensagem=msg, ts=agora - timedelta(minutes=(len(_DEMO) - i)),
        ))
    db.commit()
    return {"ingeridos": len(_DEMO), "mensagem": "Cadeia de ataque demo injetada."}
