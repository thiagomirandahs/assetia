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
    {
        "name": "listar_alertas_recentes",
        "description": "Lista os alertas mais recentes do sistema. Use para perguntas como 'tem algum alerta?' ou 'o que esta acontecendo de errado?'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "apenas_nao_lidos": {"type": "boolean", "description": "Se true, so retorna alertas nao lidos (padrao false)"},
                "limit": {"type": "integer", "description": "Maximo de alertas (padrao 20)"},
            },
        },
    },

    # ===== Ferramentas de ACAO (modificam estado) =====
    {
        "name": "iniciar_scan_rede",
        "description": (
            "Inicia um scan na rede informada (em CIDR). Use quando o usuario pedir 'escaneie a rede', "
            "'rode um scan agora' ou 'procure novos dispositivos'. Executa SINCRONO (~5-15s para /24)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "rede": {"type": "string", "description": "Rede em CIDR. Ex: 192.168.1.0/24"},
            },
            "required": ["rede"],
        },
    },
    {
        "name": "marcar_dispositivo_autorizado",
        "description": (
            "Marca um dispositivo como AUTORIZADO (adiciona a tag 'autorizado' e identifica o tipo). "
            "Use quando o usuario disser 'esse dispositivo eh meu', 'autoriza esse', 'reconhece esse IP'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "ID do dispositivo (ou use 'ip' como alternativa)"},
                "ip": {"type": "string", "description": "IP do dispositivo (alternativa ao device_id)"},
                "tipo": {"type": "string", "description": "Tipo: servidor/estacao/impressora/ap/iot/etc"},
                "hostname": {"type": "string", "description": "Nome amigavel pra dar ao dispositivo"},
            },
        },
    },
    {
        "name": "marcar_alertas_como_lidos",
        "description": (
            "Marca alertas como lidos em massa. Use quando o usuario disser 'limpar alertas', "
            "'marcar tudo como lido' ou similar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "severidade": {"type": "string", "description": "Filtra por severidade (info|warning|critical). Vazio = todos"},
                "apenas_recentes_dias": {"type": "integer", "description": "Se informado, so marca alertas dos ultimos N dias"},
            },
        },
    },
    {
        "name": "alterar_regra_alerta",
        "description": (
            "Ativa ou desativa uma regra de alerta. Use quando o usuario disser "
            "'desativa o alerta de X', 'para de me avisar sobre Y'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "regra_id": {"type": "integer", "description": "ID da regra"},
                "ativa": {"type": "boolean", "description": "true para ativar, false para desativar"},
            },
            "required": ["regra_id", "ativa"],
        },
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
        # consultas
        "buscar_dispositivos": _buscar,
        "contar_dispositivos_por_fabricante": _contar_fabricante,
        "contar_dispositivos_por_so": _contar_so,
        "dispositivos_novos": _novos,
        "dispositivos_offline_ha_muito_tempo": _offline_antigos,
        "resumo_inventario": _resumo,
        "listar_alertas_recentes": _listar_alertas,
        # acoes
        "iniciar_scan_rede": _acao_iniciar_scan,
        "marcar_dispositivo_autorizado": _acao_marcar_autorizado,
        "marcar_alertas_como_lidos": _acao_marcar_alertas_lidos,
        "alterar_regra_alerta": _acao_alterar_regra,
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
    from ..core.models import Alert
    alertas_nao_lidos = db.query(Alert).filter(
        Alert.tenant_id == tenant_id, Alert.lido.is_(False)
    ).count()
    return {
        "total": total,
        "online": online,
        "offline": total - online,
        "alertas_nao_lidos": alertas_nao_lidos,
        "top_fabricantes": top_fab,
        "top_sistemas_operacionais": top_so,
    }


def _listar_alertas(args: dict, *, db: Session, tenant_id: int) -> dict:
    from ..core.models import Alert
    q = db.query(Alert).filter(Alert.tenant_id == tenant_id)
    if args.get("apenas_nao_lidos"):
        q = q.filter(Alert.lido.is_(False))
    limit = int(args.get("limit", 20))
    items = q.order_by(Alert.criado_em.desc()).limit(limit).all()
    return {
        "total": q.count(),
        "alertas": [
            {
                "id": a.id,
                "severidade": a.severidade,
                "titulo": a.titulo,
                "mensagem": a.mensagem,
                "lido": a.lido,
                "criado_em": a.criado_em.isoformat() if a.criado_em else None,
            }
            for a in items
        ],
    }


# ===== ACOES =====

def _acao_iniciar_scan(args: dict, *, db: Session, tenant_id: int) -> dict:
    """Roda um scan AGORA (sincrono). Pode demorar ate ~15s para /24."""
    from ..scanner.scanner import executar_scan
    from ..core.models import Scan
    from datetime import datetime, timezone

    rede = args.get("rede")
    if not rede:
        return {"erro": "campo 'rede' obrigatorio (ex: 192.168.1.0/24)"}

    scan = Scan(tenant_id=tenant_id, rede=rede, status="rodando")
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        achados, novos = executar_scan(db, tenant_id=tenant_id, rede=rede)
        scan.achados = achados
        scan.novos = novos
        scan.status = "concluido"
        scan.finalizado_em = datetime.now(timezone.utc)
        db.commit()
        return {
            "sucesso": True,
            "scan_id": scan.id,
            "rede": rede,
            "dispositivos_encontrados": achados,
            "dispositivos_novos": novos,
            "mensagem": f"Scan concluido. Encontrei {achados} dispositivos online ({novos} sao novos).",
        }
    except Exception as e:  # noqa: BLE001
        scan.status = "erro"
        scan.erro = str(e)
        db.commit()
        return {"sucesso": False, "erro": str(e)}


def _acao_marcar_autorizado(args: dict, *, db: Session, tenant_id: int) -> dict:
    """Adiciona tag 'autorizado' e opcionalmente atualiza tipo/hostname."""
    q = db.query(Device).filter(Device.tenant_id == tenant_id)
    if args.get("device_id"):
        d = q.filter(Device.id == int(args["device_id"])).first()
    elif args.get("ip"):
        d = q.filter(Device.ip == args["ip"]).first()
    else:
        return {"erro": "informe device_id ou ip"}

    if not d:
        return {"erro": "dispositivo nao encontrado"}

    # Adiciona tag 'autorizado' (sem duplicar)
    tags = set((d.tags or "").split(",")) - {""}
    tags.add("autorizado")
    d.tags = ",".join(sorted(tags))

    alteracoes = []
    if args.get("tipo"):
        d.tipo = args["tipo"]
        alteracoes.append(f"tipo={args['tipo']}")
    if args.get("hostname"):
        d.hostname = args["hostname"]
        alteracoes.append(f"hostname={args['hostname']}")

    db.commit()
    return {
        "sucesso": True,
        "device_id": d.id,
        "ip": d.ip,
        "hostname": d.hostname,
        "tags": d.tags,
        "alteracoes": alteracoes,
        "mensagem": f"Dispositivo {d.hostname or d.ip} marcado como autorizado.",
    }


def _acao_marcar_alertas_lidos(args: dict, *, db: Session, tenant_id: int) -> dict:
    """Marca alertas como lidos em massa, com filtros opcionais."""
    from ..core.models import Alert
    from datetime import datetime, timedelta, timezone

    q = db.query(Alert).filter(Alert.tenant_id == tenant_id, Alert.lido.is_(False))
    if args.get("severidade"):
        q = q.filter(Alert.severidade == args["severidade"])
    if args.get("apenas_recentes_dias"):
        limite = datetime.now(timezone.utc) - timedelta(days=int(args["apenas_recentes_dias"]))
        q = q.filter(Alert.criado_em >= limite)

    total = q.count()
    q.update({"lido": True}, synchronize_session=False)
    db.commit()
    return {"sucesso": True, "alertas_marcados": total, "mensagem": f"{total} alertas marcados como lidos."}


def _acao_alterar_regra(args: dict, *, db: Session, tenant_id: int) -> dict:
    """Ativa ou desativa uma regra de alerta."""
    from ..core.models import AlertRule

    regra = db.query(AlertRule).filter(
        AlertRule.id == int(args["regra_id"]),
        AlertRule.tenant_id == tenant_id,
    ).first()
    if not regra:
        return {"erro": "regra nao encontrada"}

    regra.ativa = bool(args["ativa"])
    db.commit()
    status = "ativada" if regra.ativa else "desativada"
    return {
        "sucesso": True,
        "regra_id": regra.id,
        "nome": regra.nome,
        "ativa": regra.ativa,
        "mensagem": f"Regra '{regra.nome}' foi {status}.",
    }
