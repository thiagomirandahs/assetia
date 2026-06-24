"""Endpoints para gestao de regras de alerta e visualizacao de alertas."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..alerts.channels import notificar
from ..alerts.engine import avaliar_regras_para_tenant
from ..core.auth import CurrentUser
from ..core.database import get_db
from ..core.models import Alert, AlertRule
from ..core.schemas import (
    AlertListOut,
    AlertOut,
    AlertRuleOut,
    AlertRuleToggleIn,
    AvaliarAlertasOut,
)

router = APIRouter()


# ===== Regras =====

@router.get("/regras", response_model=list[AlertRuleOut])
def listar_regras(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    rows = (
        db.query(AlertRule)
        .filter(AlertRule.tenant_id == user.tenant_id)
        .order_by(AlertRule.id)
        .all()
    )
    return [AlertRuleOut.model_validate(r) for r in rows]


@router.patch("/regras/{regra_id}", response_model=AlertRuleOut)
def alternar_regra(
    regra_id: int,
    dados: AlertRuleToggleIn,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    r = db.query(AlertRule).filter(
        AlertRule.id == regra_id, AlertRule.tenant_id == user.tenant_id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="regra nao encontrada")
    r.ativa = dados.ativa
    db.commit()
    db.refresh(r)
    return AlertRuleOut.model_validate(r)


# ===== Avaliacao manual =====

@router.post("/avaliar", response_model=AvaliarAlertasOut)
def avaliar_agora(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    """Roda todas as regras agora e notifica os canais configurados."""
    res = avaliar_regras_para_tenant(db, user.tenant_id)
    notificados_email = 0
    notificados_telegram = 0
    for a in res["novos_alerts"]:
        regra = db.get(AlertRule, a.rule_id)
        if not regra:
            continue
        canais = [c.strip() for c in (regra.canais or "").split(",")]
        resultado = notificar(a, canais)
        if resultado.get("email"): notificados_email += 1
        if resultado.get("telegram"): notificados_telegram += 1
    return AvaliarAlertasOut(
        avaliadas=res["avaliadas"],
        gerados=res["gerados_total"],
        notificados_email=notificados_email,
        notificados_telegram=notificados_telegram,
    )


# ===== Alertas =====

@router.get("", response_model=AlertListOut)
def listar(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    apenas_nao_lidos: bool = False,
    limit: int = 50,
):
    q = db.query(Alert).filter(Alert.tenant_id == user.tenant_id)
    if apenas_nao_lidos:
        q = q.filter(Alert.lido.is_(False))
    total = q.count()
    nao_lidos = q.filter(Alert.lido.is_(False)).count()
    rows = q.order_by(Alert.criado_em.desc()).limit(limit).all()
    return AlertListOut(
        total=total,
        nao_lidos=nao_lidos,
        alerts=[AlertOut.model_validate(r) for r in rows],
    )


@router.post("/{alert_id}/marcar_lido", response_model=AlertOut)
def marcar_lido(alert_id: int, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    a = db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == user.tenant_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="alerta nao encontrado")
    a.lido = True
    db.commit()
    db.refresh(a)
    return AlertOut.model_validate(a)


@router.post("/marcar_todos_lidos")
def marcar_todos_lidos(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    db.query(Alert).filter(
        Alert.tenant_id == user.tenant_id, Alert.lido.is_(False)
    ).update({"lido": True}, synchronize_session=False)
    db.commit()
    return {"status": "ok"}
