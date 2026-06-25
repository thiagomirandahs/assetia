"""Threat Intelligence: reputacao de um IP.

Heuristica offline (classifica o IP) + consulta AbuseIPDB se ABUSEIPDB_KEY estiver no ambiente.
Respeite os termos de uso das APIs e consulte apenas IPs que voce tem motivo legitimo para checar.
"""
import ipaddress
import logging
import os

import httpx

logger = logging.getLogger(__name__)


def _classificar(ip: str) -> dict:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return {"tipo": "inválido"}
    if addr.is_private:
        return {"tipo": "privado (rede interna)"}
    if addr.is_loopback:
        return {"tipo": "loopback"}
    if addr.is_reserved or addr.is_link_local:
        return {"tipo": "reservado/especial"}
    if addr.is_global:
        return {"tipo": "público (internet)"}
    return {"tipo": "desconhecido"}


def reputacao_ip(ip: str, *, timeout: float = 6.0) -> dict:
    base = {"ip": ip, **_classificar(ip)}

    # IP privado: sem reputacao externa (e correto)
    if base.get("tipo", "").startswith(("privado", "loopback", "reservado")):
        base["fonte"] = "local"
        base["resumo"] = "IP interno/reservado — sem reputação pública aplicável."
        return base

    chave = os.environ.get("ABUSEIPDB_KEY", "").strip()
    if not chave:
        base["fonte"] = "heurística"
        base["resumo"] = "IP público. Defina ABUSEIPDB_KEY no ambiente para reputação real (denúncias, score)."
        return base

    try:
        r = httpx.get(
            "https://api.abuseipdb.com/api/v2/check",
            params={"ipAddress": ip, "maxAgeInDays": 90},
            headers={"Key": chave, "Accept": "application/json"},
            timeout=timeout,
        )
        d = r.json().get("data", {})
        base.update({
            "fonte": "AbuseIPDB",
            "abuse_score": d.get("abuseConfidenceScore"),
            "denuncias": d.get("totalReports"),
            "pais": d.get("countryCode"),
            "isp": d.get("isp"),
            "resumo": f"Score de abuso {d.get('abuseConfidenceScore')}% — {d.get('totalReports')} denúncias ({d.get('countryCode')}).",
        })
    except Exception as e:  # noqa: BLE001
        base["fonte"] = "AbuseIPDB"
        base["erro"] = str(e)
    return base
