"""Ferramentas que o agente IA pode chamar para consultar o banco.

Cada tool tem:
  - schema JSON Schema (formato Anthropic tool use)
  - funcao Python que executa a consulta no banco e devolve dict
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.models import Device


# ===== Schemas (formato Anthropic) =====

TOOL_SCHEMAS = [
    {
        "name": "buscar_dispositivos",
        "description": (
            "Busca dispositivos no inventario. Use para perguntas sobre quais "
            "dispositivos existem, com filtros opcionais por fabricante, SO, status online, "
            "ou texto livre que casa com hostname/IP/MAC."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "busca": {"type": "string", "description": "Texto livre para hostname/IP/MAC/fabricante"},
                "fabricante": {"type": "string", "description": "Filtra por fabricante (ex: Dell, HP, Apple)"},
                "so": {"type": "string", "description": "Filtra por sistema operacional (ex: Windows, Linux)"},
                "online": {"type": "boolean", "description": "Se true, so retorna online; se false, so offline"},
                "limit": {"type": "integer", "description": "Maximo de resultados (padrao 20)"},
            },
        },
    },
    {
        "name": "contar_dispositivos_por_fabricante",
        "description": "Agrupa e conta dispositivos por fabricante. Bom para perguntas tipo 'quantos dispositivos Dell tenho'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "contar_dispositivos_por_so",
        "description": "Agrupa e conta dispositivos por sistema operacional.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "dispositivos_novos",
        "description": "Lista dispositivos descobertos nos ultimos N dias (primeira_visao). Use para 'o que apareceu de novo'.",
        "input_schema": {
            "type": "object",
            "properties": {"dias": {"type": "integer", "description": "Janela em dias (padrao 7)"}},
        },
    },
    {
        "name": "dispositivos_offline_ha_muito_tempo",
        "description": "Dispositivos que estao offline ha mais de N dias. Ajuda a detectar maquinas abandonadas.",
        "input_schema": {
            "type": "object",
            "properties": {"dias": {"type": "integer", "description": "Padrao 30"}},
        },
    },
    {
        "name": "resumo_inventario",
        "description": "Estatisticas gerais: total de dispositivos, online vs offline, top fabricantes, top SOs.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ===== Implementacao =====

def _device_para_dict(d: Device) -> dict:
    return {
        "id": d.id,
        "ip": d.ip,
        "mac": d.mac,
        "hostname": d.hostname,
        "fabricante": d.fabricante,
        "so": d.so,
        "tipo": d.tipo,
        "vlan": d.vlan,
        "online": d.online,
        "primeira_visao": d.primeira_visao.isoformat() if d.primeira_visao else None,
        "ultima_visao": d.ultima_visao.isoformat() if d.ultima_visao else None,
    }


def _agora():
    return datetime.now(timezone.utc)


def executar_tool(nome: str, args: dict, *, db: Session, tenant_id: int) -> dict:
    """Despacha a chamada de uma tool. Sempre filtra por tenant_id."""
    handlers = {
        "buscar_dispositivos": _buscar,
        "contar_dispositivos_por_fabricante": _contar_fabricante,
        "contar_dispositivos_por_so": _contar_so,
        "dispositivos_novos": _novos,
        "dispositivos_offline_ha_muito_tempo": _offline_antigos,
        "resumo_inventario": _resumo,
    }
    h = handlers.get(nome)
    if not h:
        return {"erro": f"tool desconhecida: {nome}"}
    return h(args, db=db, tenant_id=tenant_id)


def _buscar(args: dict, *, db: Session, tenant_id: int) -> dict:
    q = db.query(Device).filter(Device.tenant_id == tenant_id)
    if (b := args.get("busca")):
        like = f"%{b}%"
        from sqlalchemy import or_
        q = q.filter(or_(Device.hostname.like(like), Device.ip.like(like), Device.mac.like(like), Device.fabricante.like(like)))
    if (f := args.get("fabricante")):
        q = q.filter(Device.fabricante.like(f"%{f}%"))
    if (s := args.get("so")):
        q = q.filter(Device.so.like(f"%{s}%"))
    if "online" in args and args["online"] is not None:
        q = q.filter(Device.online == bool(args["online"]))
    limit = int(args.get("limit", 20))
    items = q.order_by(Device.ultima_visao.desc()).limit(limit).all()
    return {"total": q.count(), "exibidos": len(items), "dispositivos": [_device_para_dict(d) for d in items]}


def _contar_fabricante(_args, *, db: Session, tenant_id: int) -> dict:
    rows = (
        db.query(Device.fabricante, func.count(Device.id))
        .filter(Device.tenant_id == tenant_id)
        .group_by(Device.fabricante)
        .order_by(func.count(Device.id).desc())
        .all()
    )
    return {"por_fabricante": [{"fabricante": r[0] or "desconhecido", "quantidade": r[1]} for r in rows]}


def _contar_so(_args, *, db: Session, tenant_id: int) -> dict:
    rows = (
        db.query(Device.so, func.count(Device.id))
        .filter(Device.tenant_id == tenant_id)
        .group_by(Device.so)
        .order_by(func.count(Device.id).desc())
        .all()
    )
    return {"por_so": [{"so": r[0] or "desconhecido", "quantidade": r[1]} for r in rows]}


def _novos(args: dict, *, db: Session, tenant_id: int) -> dict:
    dias = int(args.get("dias", 7))
    limite = _agora() - timedelta(days=dias)
    items = (
        db.query(Device)
        .filter(Device.tenant_id == tenant_id, Device.primeira_visao >= limite)
        .order_by(Device.primeira_visao.desc())
        .limit(50)
        .all()
    )
    return {"janela_dias": dias, "total": len(items), "dispositivos": [_device_para_dict(d) for d in items]}


def _offline_antigos(args: dict, *, db: Session, tenant_id: int) -> dict:
    dias = int(args.get("dias", 30))
    limite = _agora() - timedelta(days=dias)
    items = (
        db.query(Device)
        .filter(Device.tenant_id == tenant_id, Device.online.is_(False), Device.ultima_visao <= limite)
        .order_by(Device.ultima_visao.asc())
        .limit(50)
        .all()
    )
    return {"limite_dias": dias, "total": len(items), "dispositivos": [_device_para_dict(d) for d in items]}


def _resumo(_args, *, db: Session, tenant_id: int) -> dict:
    base = db.query(Device).filter(Device.tenant_id == tenant_id)
    total = base.count()
    online = base.filter(Device.online.is_(True)).count()
    top_fab = _contar_fabricante(None, db=db, tenant_id=tenant_id)["por_fabricante"][:5]
    top_so = _contar_so(None, db=db, tenant_id=tenant_id)["por_so"][:5]
    return {
        "total": total,
        "online": online,
        "offline": total - online,
        "top_fabricantes": top_fab,
        "top_sistemas_operacionais": top_so,
    }
