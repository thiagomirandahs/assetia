"""Cria as regras padrao para um novo tenant."""
import json

from sqlalchemy.orm import Session

from ..core.models import AlertRule


REGRAS_PADRAO = [
    {
        "nome": "Dispositivo novo na rede",
        "descricao": "Alerta sempre que um dispositivo desconhecido aparece na rede pela primeira vez.",
        "tipo": "dispositivo_novo",
        "parametros": {"janela_dias": 7},
        "severidade": "info",
        "canais": "in_app",
    },
    {
        "nome": "Dispositivo offline ha muito tempo",
        "descricao": "Alerta para dispositivos offline por mais de 30 dias — pode indicar maquina abandonada ou problema tecnico.",
        "tipo": "offline_ha_muito_tempo",
        "parametros": {"dias": 30},
        "severidade": "info",
        "canais": "in_app",
    },
    {
        "nome": "Dispositivo desconhecido (sem fabricante)",
        "descricao": "Alerta para dispositivos online sem fabricante nem sistema operacional identificados — potencial intruso.",
        "tipo": "dispositivo_desconhecido",
        "parametros": {},
        "severidade": "warning",
        "canais": "in_app",
    },
    {
        "nome": "Possivel MAC spoofing",
        "descricao": "Detecta MACs que aparecem em multiplas VLANs (suspeita de spoofing ou misconfiguracao critica).",
        "tipo": "mac_duplicado",
        "parametros": {},
        "severidade": "critical",
        "canais": "in_app",
    },
]


def criar_regras_padrao(db: Session, tenant_id: int) -> int:
    """Cria as regras padrao para o tenant. Idempotente — nao duplica."""
    criadas = 0
    for r in REGRAS_PADRAO:
        existe = (
            db.query(AlertRule)
            .filter(AlertRule.tenant_id == tenant_id, AlertRule.nome == r["nome"])
            .first()
        )
        if existe:
            continue
        regra = AlertRule(
            tenant_id=tenant_id,
            nome=r["nome"],
            descricao=r["descricao"],
            tipo=r["tipo"],
            parametros=json.dumps(r["parametros"]),
            severidade=r["severidade"],
            canais=r["canais"],
            ativa=True,
        )
        db.add(regra)
        criadas += 1
    db.commit()
    return criadas
