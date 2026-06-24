"""Motor de avaliacao de regras de alerta.

Cada regra eh um filtro sobre Devices. Quando casa, gera um Alert (se ja nao
existe um "nao lido" para a mesma combinacao rule_id + device_id, evitando
spam).
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.models import Alert, AlertRule, Device

logger = logging.getLogger(__name__)


def _aware(dt: datetime) -> datetime:
    """Garante que o datetime tenha timezone (UTC se nao tiver). SQLite perde tzinfo."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def avaliar_regras_para_tenant(db: Session, tenant_id: int) -> dict:
    """Avalia TODAS as regras ativas do tenant. Retorna estatisticas + lista de novos alertas."""
    regras = db.query(AlertRule).filter(
        AlertRule.tenant_id == tenant_id, AlertRule.ativa.is_(True)
    ).all()

    avaliadas = 0
    gerados: list[Alert] = []

    for regra in regras:
        avaliadas += 1
        try:
            novos = _avaliar_regra(db, regra)
            gerados.extend(novos)
        except Exception as e:  # noqa: BLE001
            logger.exception("falha ao avaliar regra id=%s: %s", regra.id, e)

    db.commit()
    return {"avaliadas": avaliadas, "gerados_total": len(gerados), "novos_alerts": gerados}


def _avaliar_regra(db: Session, regra: AlertRule) -> list[Alert]:
    """Despacha para o handler correto baseado no tipo da regra."""
    handlers: dict[str, Callable[[Session, AlertRule], list[Alert]]] = {
        "dispositivo_novo": _h_dispositivo_novo,
        "offline_ha_muito_tempo": _h_offline_antigo,
        "dispositivo_desconhecido": _h_desconhecido,
        "mac_duplicado": _h_mac_duplicado,
    }
    handler = handlers.get(regra.tipo)
    if not handler:
        logger.warning("tipo de regra desconhecido: %s", regra.tipo)
        return []
    return handler(db, regra)


def _parametros(regra: AlertRule) -> dict:
    if not regra.parametros:
        return {}
    try:
        return json.loads(regra.parametros)
    except json.JSONDecodeError:
        return {}


def _alerta_existente_nao_lido(db: Session, *, tenant_id: int, rule_id: int, device_id: int | None) -> bool:
    """Verifica se ja existe um alerta nao-lido para essa combinacao."""
    return (
        db.query(Alert.id)
        .filter(
            Alert.tenant_id == tenant_id,
            Alert.rule_id == rule_id,
            Alert.device_id == device_id,
            Alert.lido.is_(False),
        )
        .first()
        is not None
    )


def _criar_alerta(
    db: Session,
    *,
    regra: AlertRule,
    device: Device | None,
    titulo: str,
    mensagem: str,
) -> Alert | None:
    if _alerta_existente_nao_lido(
        db, tenant_id=regra.tenant_id, rule_id=regra.id, device_id=device.id if device else None
    ):
        return None
    alert = Alert(
        tenant_id=regra.tenant_id,
        rule_id=regra.id,
        device_id=device.id if device else None,
        severidade=regra.severidade,
        titulo=titulo,
        mensagem=mensagem,
    )
    db.add(alert)
    return alert


# ===== handlers =====

def _h_dispositivo_novo(db: Session, regra: AlertRule) -> list[Alert]:
    p = _parametros(regra)
    janela_dias = int(p.get("janela_dias", 7))
    limite = datetime.now(timezone.utc) - timedelta(days=janela_dias)
    devices = (
        db.query(Device)
        .filter(Device.tenant_id == regra.tenant_id, Device.primeira_visao >= limite)
        .all()
    )
    novos: list[Alert] = []
    for d in devices:
        titulo = f"Dispositivo novo na rede: {d.hostname or d.ip}"
        mensagem = (
            f"Detectamos um novo dispositivo na rede.\n"
            f"  • IP: {d.ip}\n"
            f"  • MAC: {d.mac or '—'}\n"
            f"  • Fabricante: {d.fabricante or 'desconhecido'}\n"
            f"  • Primeira aparição: {d.primeira_visao:%d/%m/%Y %H:%M}"
        )
        if (a := _criar_alerta(db, regra=regra, device=d, titulo=titulo, mensagem=mensagem)):
            novos.append(a)
    return novos


def _h_offline_antigo(db: Session, regra: AlertRule) -> list[Alert]:
    p = _parametros(regra)
    dias = int(p.get("dias", 30))
    limite = datetime.now(timezone.utc) - timedelta(days=dias)
    devices = (
        db.query(Device)
        .filter(
            Device.tenant_id == regra.tenant_id,
            Device.online.is_(False),
            Device.ultima_visao <= limite,
        )
        .all()
    )
    novos: list[Alert] = []
    for d in devices:
        dias_offline = (datetime.now(timezone.utc) - _aware(d.ultima_visao)).days
        titulo = f"Offline há {dias_offline} dias: {d.hostname or d.ip}"
        mensagem = (
            f"Este dispositivo está offline há muito tempo. "
            f"Pode ter sido desativado, removido ou ter problema técnico.\n"
            f"  • Última aparição: {d.ultima_visao:%d/%m/%Y %H:%M}\n"
            f"  • Tipo: {d.tipo or 'desconhecido'}"
        )
        if (a := _criar_alerta(db, regra=regra, device=d, titulo=titulo, mensagem=mensagem)):
            novos.append(a)
    return novos


def _h_desconhecido(db: Session, regra: AlertRule) -> list[Alert]:
    devices = (
        db.query(Device)
        .filter(
            Device.tenant_id == regra.tenant_id,
            Device.online.is_(True),
            (Device.fabricante.is_(None)) | (Device.so.is_(None)),
        )
        .all()
    )
    novos: list[Alert] = []
    for d in devices:
        # Foca em casos realmente "obscuros" (sem fabricante E sem SO)
        if d.fabricante or d.so:
            continue
        titulo = f"⚠️ Dispositivo desconhecido: {d.hostname or d.ip}"
        mensagem = (
            f"Há um dispositivo online sem fabricante nem SO identificados — "
            f"pode ser um equipamento não autorizado na rede.\n"
            f"  • IP: {d.ip}\n"
            f"  • MAC: {d.mac or '—'}\n"
            f"  • VLAN: {d.vlan or '—'}"
        )
        if (a := _criar_alerta(db, regra=regra, device=d, titulo=titulo, mensagem=mensagem)):
            novos.append(a)
    return novos


def _h_mac_duplicado(db: Session, regra: AlertRule) -> list[Alert]:
    """Detecta MACs que aparecem em mais de uma VLAN — suspeita de spoofing."""
    rows = (
        db.query(Device.mac, func.count(func.distinct(Device.vlan)).label("vlans"))
        .filter(Device.tenant_id == regra.tenant_id, Device.mac.isnot(None), Device.vlan.isnot(None))
        .group_by(Device.mac)
        .having(func.count(func.distinct(Device.vlan)) > 1)
        .all()
    )
    novos: list[Alert] = []
    for row in rows:
        mac = row[0]
        devices = (
            db.query(Device)
            .filter(Device.tenant_id == regra.tenant_id, Device.mac == mac)
            .all()
        )
        vlans = ", ".join(sorted({d.vlan for d in devices if d.vlan}))
        titulo = f"🚨 Possível MAC spoofing: {mac}"
        mensagem = (
            f"O MAC {mac} aparece em múltiplas VLANs ({vlans}). "
            f"Isso pode indicar um ataque de MAC spoofing ou um dispositivo malconfigurado.\n"
            f"Dispositivos afetados: {', '.join(d.hostname or d.ip for d in devices)}"
        )
        # Sem device_id (aplica-se a varios)
        if (a := _criar_alerta(db, regra=regra, device=None, titulo=titulo, mensagem=mensagem)):
            novos.append(a)
    return novos
