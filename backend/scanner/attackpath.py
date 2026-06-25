"""Attack Path: a partir dos hosts ja escaneados, desenha o caminho PROVAVEL de ataque.

Heuristica (nao executa nada): elege um ponto de entrada (host mais exposto com serviço
crítico), uma 'joia da coroa' (banco/AD), e monta a cadeia Internet -> entrada -> foothold
-> movimento lateral -> alvo. Serve para priorizar defesa e impressionar em relatorios.
"""
import json

from sqlalchemy.orm import Session

from ..core.models import Device, Porta

# servicos que costumam ser ponto de ENTRADA (expostos/exploraveis)
_ENTRADA = {"http", "https", "http-alt", "http-proxy", "rdp", "smb", "ssh", "ftp", "vnc", "telnet"}
# servicos de ALVO (dados/identidade = joia da coroa)
_ALVO = {"mssql", "mysql", "postgres", "oracle", "mongodb", "redis", "ldap", "smb", "kerberos", "globalcat"}


def _portas(db, tenant_id, device_id):
    return db.query(Porta).filter(Porta.tenant_id == tenant_id, Porta.device_id == device_id).all()


def gerar_attack_path(db: Session, *, tenant_id: int) -> dict:
    devices = (
        db.query(Device)
        .filter(Device.tenant_id == tenant_id, Device.risco_score.isnot(None))
        .order_by(Device.risco_score.desc())
        .all()
    )
    if not devices:
        return {"ok": False, "motivo": "Escaneie alguns hosts primeiro (precisa de portas/risco)."}

    # ponto de entrada: maior risco com porta de entrada aberta
    entrada = None
    entrada_porta = None
    for d in devices:
        ports = _portas(db, tenant_id, d.id)
        cand = sorted(
            [p for p in ports if (p.servico in _ENTRADA)],
            key=lambda p: (p.severidade == "critical", bool(p.cves)), reverse=True,
        )
        if cand:
            entrada, entrada_porta = d, cand[0]
            break
    if not entrada:
        return {"ok": False, "motivo": "Nenhum serviço de entrada típico aberto nos hosts escaneados."}

    # alvo (joia da coroa): host com serviço de dados/identidade, diferente da entrada se possível
    alvo = None
    alvo_porta = None
    for d in devices:
        ports = _portas(db, tenant_id, d.id)
        cand = [p for p in ports if p.servico in _ALVO]
        if cand and (d.id != entrada.id or alvo is None):
            alvo, alvo_porta = d, cand[0]
            if d.id != entrada.id:
                break
    if not alvo:
        alvo, alvo_porta = entrada, entrada_porta

    cve_ent = ""
    try:
        cves = json.loads(entrada_porta.cves) if entrada_porta.cves else []
        cve_ent = cves[0]["cve"] if cves else ""
    except Exception:  # noqa: BLE001
        pass

    passos = [
        {"de": "Internet/Atacante", "para": entrada.ip,
         "tecnica": f"Acesso ao serviço {entrada_porta.servico} (:{entrada_porta.porta})",
         "detalhe": (entrada_porta.risco or "serviço exposto") + (f" — {cve_ent}" if cve_ent else "")},
        {"de": entrada.ip, "para": entrada.ip,
         "tecnica": "Obter foothold",
         "detalhe": "Exploração da vuln/credencial fraca → execução de comando (shell)."},
    ]
    if alvo.id != entrada.id:
        passos.append({"de": entrada.ip, "para": alvo.ip,
                       "tecnica": "Movimento lateral",
                       "detalhe": "Reuso de credenciais / pivot pela rede interna."})
    passos.append({"de": alvo.ip, "para": f"{alvo.ip}:{alvo_porta.porta}",
                   "tecnica": f"Comprometer o alvo ({alvo_porta.servico})",
                   "detalhe": "Acesso aos dados/identidade (joia da coroa)."})

    return {
        "ok": True,
        "entrada": {"ip": entrada.ip, "servico": entrada_porta.servico, "porta": entrada_porta.porta,
                    "risco": entrada.risco_score, "cve": cve_ent},
        "alvo": {"ip": alvo.ip, "servico": alvo_porta.servico, "porta": alvo_porta.porta},
        "passos": passos,
        "recomendacao": f"Quebre a cadeia no ponto de entrada: corrija {entrada_porta.servico} em {entrada.ip}.",
    }
