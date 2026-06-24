"""Endpoints para iniciar e consultar scans de rede."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.auth import CurrentUser
from ..core.database import SessionLocal, get_db
from ..core.models import Scan
from ..core.schemas import ScanOut, ScanStartIn
from ..scanner.scanner import executar_scan

router = APIRouter()


def _rodar_scan_em_background(scan_id: int, tenant_id: int, rede: str):
    """Worker que roda o scan e atualiza o registro no banco."""
    db: Session = SessionLocal()
    try:
        scan = db.get(Scan, scan_id)
        if not scan:
            return
        try:
            achados, novos = executar_scan(db, tenant_id=tenant_id, rede=rede)
            scan.achados = achados
            scan.novos = novos
            scan.status = "concluido"
        except Exception as e:  # noqa: BLE001
            scan.status = "erro"
            scan.erro = str(e)
        finally:
            scan.finalizado_em = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/start", response_model=ScanOut, status_code=202)
def iniciar(
    dados: ScanStartIn,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    bg: BackgroundTasks,
):
    """Inicia um scan em background. Retorna o registro imediatamente."""
    scan = Scan(tenant_id=user.tenant_id, rede=dados.rede, status="rodando")
    db.add(scan)
    db.commit()
    db.refresh(scan)
    bg.add_task(_rodar_scan_em_background, scan.id, user.tenant_id, dados.rede)
    return ScanOut.model_validate(scan)


@router.get("", response_model=list[ScanOut])
def listar(user: CurrentUser, db: Annotated[Session, Depends(get_db)], limit: int = 20):
    rows = (
        db.query(Scan)
        .filter(Scan.tenant_id == user.tenant_id)
        .order_by(Scan.iniciado_em.desc())
        .limit(limit)
        .all()
    )
    return [ScanOut.model_validate(r) for r in rows]


@router.get("/{scan_id}", response_model=ScanOut)
def detalhe(scan_id: int, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    s = db.query(Scan).filter(Scan.id == scan_id, Scan.tenant_id == user.tenant_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="scan nao encontrado")
    return ScanOut.model_validate(s)
