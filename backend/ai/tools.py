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

    # ===== Ferramentas de PENTEST (varredura de portas / superficie de ataque) =====
    {
        "name": "escanear_portas",
        "description": (
            "Faz varredura de portas TCP (connect scan) em um alvo AUTORIZADO e identifica servicos, "
            "banners e exposicoes de risco. Use quando pedirem 'escaneie as portas de X', 'o que esta "
            "aberto em Y', 'mapeia a superficie de ataque do host Z'. Executa SINCRONO (~2-4s)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP do alvo. Ex: 192.168.1.10 (ou use device_id)"},
                "device_id": {"type": "integer", "description": "ID de um device ja conhecido (alternativa ao ip)"},
            },
        },
    },
    {
        "name": "superficie_de_ataque",
        "description": (
            "Resumo da superficie de ataque: hosts escaneados, total de portas abertas, contagem por "
            "severidade, servicos mais expostos e a lista de exposicoes criticas. Use para 'como esta "
            "minha superficie de ataque', 'quais os maiores riscos', 'o que esta exposto na rede'."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "portas_de_um_host",
        "description": "Lista as portas abertas ja descobertas de um host especifico (por device_id ou ip).",
        "input_schema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "ID do device"},
                "ip": {"type": "string", "description": "IP do host (alternativa ao device_id)"},
            },
        },
    },
    {
        "name": "descobrir_hosts_rede",
        "description": (
            "Faz ping sweep em uma rede (CIDR) e RETORNA a lista de IPs vivos (com MAC/fabricante). "
            "Use quando pedirem 'quais IPs estao na rede', 'descubra os hosts de X', 'me retorne os ips'. "
            "Funciona com qualquer alvo AUTORIZADO (LAN ou externo). Limite de /21."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cidr": {"type": "string", "description": "Rede em CIDR. Ex: 192.168.1.0/24 (ou host/32)"},
            },
            "required": ["cidr"],
        },
    },
    {
        "name": "checar_credenciais_default",
        "description": (
            "CHECAGEM ATIVA e intrusiva (autorizada): testa CREDENCIAIS PADRAO conhecidas "
            "(admin/admin, root/root, anonymous...) nos servicos abertos do alvo (FTP/SSH/HTTP). "
            "Use SOMENTE quando o usuario pedir EXPLICITAMENTE para testar credenciais default em um "
            "alvo autorizado. Requer que o host ja tenha sido escaneado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP do alvo"},
                "device_id": {"type": "integer", "description": "ID do device (alternativa ao ip)"},
            },
        },
    },
    {
        "name": "analisar_web",
        "description": (
            "Checagens de seguranca WEB num alvo: headers de seguranca ausentes, caminhos sensiveis "
            "expostos (.git, .env, /admin), metodos HTTP perigosos e analise TLS/SSL (protocolo fraco, "
            "certificado expirado/auto-assinado). Use para 'analise o site/web de X', 'esse host tem falha web?'. "
            "Requer que o host ja tenha sido escaneado (usa as portas HTTP/HTTPS descobertas)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP/host do alvo"},
                "device_id": {"type": "integer", "description": "ID do device (alternativa)"},
            },
        },
    },
    {
        "name": "diagnosticar_rede",
        "description": (
            "Diagnostico de rede: descobre o equipamento que esta causando problema. Testa gateway vs "
            "internet (problema interno x ISP), perda de pacote por host, e anomalias de ARP (spoofing, "
            "rogue device, IP duplicado, gateway personificado). Use para 'minha rede esta com problema', "
            "'o que esta derrubando/bagunçando a rede', 'tem algo estranho na rede', 'rede lenta/caindo'."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "explicar_achado",
        "description": (
            "MODO EDUCATIVO: explica um achado/serviço/conceito de pentest de forma didática (o que é, "
            "por que é risco, como costuma ser explorado para DEFESA/estudo, como mitigar, onde aprender). "
            "Use quando pedirem 'me explica X', 'o que é SMB/RDP', 'como funciona ARP spoofing', ou para "
            "ensinar sobre um achado. Temas: smb, rdp, telnet, ftp, ssh, redis, mongodb, snmp, default-creds, "
            "missing-headers, weak-tls, exposed-git, arp-spoofing, db-exposto, port-scan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"tema": {"type": "string", "description": "Serviço/conceito. Ex: smb, rdp, arp-spoofing"}},
            "required": ["tema"],
        },
    },
    {
        "name": "security_baseline",
        "description": (
            "Mede o HARDENING da maquina local (Firewall, Defender, BitLocker, UAC, SMBv1, Secure Boot, "
            "RDP-NLA...) e da um Security Score. Use para 'qual meu nivel de seguranca/baseline', 'a maquina "
            "esta endurecida', 'qual a nota de hardening'."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "attack_path",
        "description": (
            "Desenha o CAMINHO DE ATAQUE provavel a partir dos hosts ja escaneados (entrada -> foothold -> "
            "movimento lateral -> joia da coroa). Use para 'qual o caminho de ataque', 'como me invadiriam', "
            "'mostra o attack path'."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "compliance",
        "description": (
            "Avalia COMPLIANCE (CIS/NIST/LGPD) a partir dos achados + baseline e da % conforme. Use para "
            "'como esta minha conformidade', 'compliance', 'estou conforme LGPD/CIS/ISO'."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "patch_advisor",
        "description": (
            "Lista o que precisa ser ATUALIZADO (patches), priorizado pelos CVEs encontrados. Use para "
            "'o que preciso atualizar', 'quais patches', 'patch advisor'."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "reputacao_ip",
        "description": (
            "Consulta a REPUTACAO de um IP (interno/publico + AbuseIPDB se configurado: score, denuncias, pais). "
            "Use para 'esse IP e confiavel', 'reputacao do IP X', 'threat intel desse IP'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"ip": {"type": "string", "description": "IP a consultar"}},
            "required": ["ip"],
        },
    },
    {
        "name": "simular_ataque_bas",
        "description": (
            "BAS (Breach & Attack Simulation): roda testes ATÔMICOS SEGUROS e reversíveis (EICAR, recon, "
            "LOLBin, persistência reversível) na máquina LOCAL para testar se as defesas (AV/EDR) detectam — "
            "abordagem Purple Team. AÇÃO ATIVA: use SOMENTE quando o usuário pedir EXPLICITAMENTE para simular "
            "ataque / rodar BAS na própria máquina. Não executa ataque real."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "monitor_rede",
        "description": (
            "Mostra o THROUGHPUT de rede AGORA (upload e download em bytes/s) da máquina. Use para "
            "'como está a banda', 'qual o upload/download agora', 'velocidade/consumo da rede em tempo real'."
        ),
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
        # pentest
        "escanear_portas": _acao_escanear_portas,
        "superficie_de_ataque": _superficie_ataque,
        "portas_de_um_host": _portas_host,
        "descobrir_hosts_rede": _descobrir_hosts,
        "checar_credenciais_default": _checar_credenciais,
        "analisar_web": _analisar_web,
        "diagnosticar_rede": _diagnosticar_rede,
        "explicar_achado": _explicar_achado,
        "security_baseline": _security_baseline,
        "attack_path": _attack_path,
        "compliance": _compliance,
        "patch_advisor": _patch_advisor,
        "reputacao_ip": _reputacao_ip,
        "simular_ataque_bas": _simular_bas,
        "monitor_rede": _monitor_rede,
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


# ===== PENTEST =====

def _acao_escanear_portas(args: dict, *, db: Session, tenant_id: int) -> dict:
    """Roda um connect scan no alvo e persiste as portas abertas."""
    from ..scanner.pentest import escanear_portas_device, obter_ou_criar_device

    if args.get("device_id"):
        dev = db.query(Device).filter(
            Device.tenant_id == tenant_id, Device.id == int(args["device_id"])
        ).first()
        if not dev:
            return {"erro": "device nao encontrado"}
    elif args.get("ip"):
        dev = obter_ou_criar_device(db, tenant_id=tenant_id, ip=args["ip"])
    else:
        return {"erro": "informe ip ou device_id"}

    resultado = escanear_portas_device(db, tenant_id=tenant_id, device=dev)
    portas = resultado["portas"]
    criticas = [p for p in portas if p["severidade"] == "critical"]
    cves = [c["cve"] for p in portas for c in (p.get("cves") or [])]
    return {
        "sucesso": True,
        "ip": dev.ip,
        "device_id": dev.id,
        "so_detectado": resultado["so"],
        "risco_score": resultado["risco_score"],
        "risco_rotulo": resultado["risco_rotulo"],
        "total": len(portas),
        "criticas": len(criticas),
        "cves": cves,
        "portas": portas,
        "mensagem": (
            f"Scan de {dev.ip}: {len(portas)} portas, {len(criticas)} criticas, "
            f"SO={resultado['so'] or '?'}, risco={resultado['risco_rotulo']} ({resultado['risco_score']}/100)."
        ),
    }


def _superficie_ataque(_args, *, db: Session, tenant_id: int) -> dict:
    from ..scanner.pentest import resumo_superficie
    return resumo_superficie(db, tenant_id=tenant_id)


def _portas_host(args: dict, *, db: Session, tenant_id: int) -> dict:
    from ..scanner.pentest import portas_do_device
    did = args.get("device_id")
    if not did and args.get("ip"):
        dev = db.query(Device).filter(
            Device.tenant_id == tenant_id, Device.ip == args["ip"]
        ).first()
        if not dev:
            return {"erro": "host nao encontrado"}
        did = dev.id
    if not did:
        return {"erro": "informe device_id ou ip"}
    return {"device_id": int(did), "portas": portas_do_device(db, tenant_id=tenant_id, device_id=int(did))}


def _descobrir_hosts(args: dict, *, db: Session, tenant_id: int) -> dict:
    """Ping sweep num CIDR e retorna os IPs vivos (persiste como devices)."""
    from ..scanner.descoberta import descobrir_hosts
    from ..scanner.pentest import obter_ou_criar_device

    cidr = args.get("cidr")
    if not cidr:
        return {"erro": "informe cidr (ex: 192.168.1.0/24)"}
    try:
        hosts = descobrir_hosts(cidr)
    except ValueError as e:
        return {"erro": str(e)}

    for h in hosts:
        dev = obter_ou_criar_device(db, tenant_id=tenant_id, ip=h["ip"])
        if h["mac"] and not dev.mac:
            dev.mac = h["mac"]
        if h["fabricante"] and not dev.fabricante:
            dev.fabricante = h["fabricante"]
        dev.online = True
        h["device_id"] = dev.id
    db.commit()

    return {
        "cidr": cidr,
        "total": len(hosts),
        "ips": [h["ip"] for h in hosts],
        "hosts": hosts,
        "mensagem": f"Descoberta em {cidr}: {len(hosts)} hosts vivos.",
    }


def _checar_credenciais(args: dict, *, db: Session, tenant_id: int) -> dict:
    """Checagem ATIVA de credenciais default (FTP/SSH/HTTP) num alvo ja escaneado."""
    from ..scanner.pentest import checar_credenciais_device, obter_ou_criar_device

    if args.get("device_id"):
        dev = db.query(Device).filter(
            Device.tenant_id == tenant_id, Device.id == int(args["device_id"])
        ).first()
        if not dev:
            return {"erro": "device nao encontrado"}
    elif args.get("ip"):
        dev = obter_ou_criar_device(db, tenant_id=tenant_id, ip=args["ip"])
    else:
        return {"erro": "informe ip ou device_id"}

    res = checar_credenciais_device(db, tenant_id=tenant_id, device=dev)
    if res.get("total"):
        res["mensagem"] = f"⚠️ {res['total']} credencial(is) DEFAULT encontrada(s) em {dev.ip}!"
    elif res.get("aviso"):
        res["mensagem"] = res["aviso"]
    else:
        res["mensagem"] = f"Nenhuma credencial default encontrada em {dev.ip}."
    return res


def _analisar_web(args: dict, *, db: Session, tenant_id: int) -> dict:
    """Checagens web (headers/caminhos/metodos) + TLS num alvo ja escaneado."""
    from ..scanner.pentest import analise_web_device, obter_ou_criar_device

    if args.get("device_id"):
        dev = db.query(Device).filter(
            Device.tenant_id == tenant_id, Device.id == int(args["device_id"])
        ).first()
        if not dev:
            return {"erro": "device nao encontrado"}
    elif args.get("ip"):
        dev = obter_ou_criar_device(db, tenant_id=tenant_id, ip=args["ip"])
    else:
        return {"erro": "informe ip ou device_id"}

    res = analise_web_device(db, tenant_id=tenant_id, device=dev)
    if not res.get("tem_http"):
        res["mensagem"] = "nenhuma porta HTTP/HTTPS aberta nesse host (escaneie as portas primeiro)"
    else:
        n = len(res.get("web", []))
        res["mensagem"] = f"Análise web de {dev.ip}: {n} achado(s) web + {len(res.get('tls', []))} análise(s) TLS."
    return res


def _diagnosticar_rede(_args, *, db: Session, tenant_id: int) -> dict:
    """Diagnostico de rede (gateway/externo/perda/ARP) — acha o equipamento problematico."""
    from ..scanner.diagnostico import diagnosticar_sync
    res = diagnosticar_sync()
    res["mensagem"] = res.get("veredito")
    return res


def _explicar_achado(args: dict, *, db: Session, tenant_id: int) -> dict:
    """Modo educativo + remediação: explica um serviço/conceito/achado e como corrigir."""
    from ..scanner.edu import explicar, temas_disponiveis
    from ..scanner.remediacao import corrigir
    exp = explicar(args.get("tema", ""))
    if not exp:
        return {"erro": f"sem explicação para '{args.get('tema')}'", "temas_disponiveis": temas_disponiveis()}
    exp["correcao"] = corrigir(args.get("tema", ""))
    return exp


def _security_baseline(_args, *, db: Session, tenant_id: int) -> dict:
    from ..scanner.baseline import baseline
    r = baseline()
    r["mensagem"] = f"Security Score: {r['score']}/100 ({r['rotulo']}) — {r['ok']}/{r['conclusivos']} checks OK."
    return r


def _attack_path(_args, *, db: Session, tenant_id: int) -> dict:
    from ..scanner.attackpath import gerar_attack_path
    return gerar_attack_path(db, tenant_id=tenant_id)


def _compliance(_args, *, db: Session, tenant_id: int) -> dict:
    from ..scanner.baseline import baseline
    from ..scanner.compliance import avaliar_compliance
    r = avaliar_compliance(db, tenant_id=tenant_id, baseline=baseline())
    r["mensagem"] = f"Compliance: {r['percentual']}% conforme ({r['conformes']}/{r['avaliados']}, {r['pendentes']} pendentes)."
    return r


def _patch_advisor(_args, *, db: Session, tenant_id: int) -> dict:
    from ..scanner.patchadvisor import aconselhar_patches
    return aconselhar_patches(db, tenant_id=tenant_id)


def _reputacao_ip(args: dict, *, db: Session, tenant_id: int) -> dict:
    from ..scanner.threatintel import reputacao_ip
    ip = args.get("ip")
    if not ip:
        return {"erro": "informe o ip"}
    return reputacao_ip(ip)


def _simular_bas(_args, *, db: Session, tenant_id: int) -> dict:
    """BAS — testes atômicos seguros na máquina local (Purple Team)."""
    from ..scanner.bas import simular
    r = simular()
    r["mensagem"] = f"BAS: {r['total']} testes rodados, {r['detectados_bloqueados']} detectado(s)/bloqueado(s). {r['aviso']}"
    return r


def _monitor_rede(_args, *, db: Session, tenant_id: int) -> dict:
    """Throughput de rede agora (upload/download)."""
    from ..scanner.netmon import amostra
    a = amostra(1.0)
    a["mensagem"] = f"Agora: ↑ {a['upload_bps'] / 1024:.1f} KB/s · ↓ {a['download_bps'] / 1024:.1f} KB/s"
    return a
