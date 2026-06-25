"""Fingerprint de SO (heuristica por portas + banners) e score de risco do host."""
import re

# pesos para o score de risco
_PESO_SEV = {"critical": 25, "warning": 8, "info": 2}
_PESO_CVE = {"critical": 30, "warning": 12, "info": 4}


def adivinhar_so(portas: list[dict]) -> str | None:
    """Heuristica de SO a partir das portas abertas + banners.

    `portas`: lista de dicts com ao menos 'porta', 'servico', 'banner'.
    """
    abertas = {p["porta"] for p in portas}
    banners = " ".join((p.get("banner") or "") for p in portas).lower()

    if re.search(r"mikrotik|routeros", banners):
        return "MikroTik RouterOS"
    if "ubuntu" in banners:
        return "Linux (Ubuntu)"
    if "debian" in banners:
        return "Linux (Debian)"
    if re.search(r"centos|red ?hat|rhel", banners):
        return "Linux (RHEL/CentOS)"
    if re.search(r"windows|microsoft-iis|win32|win64", banners):
        return "Windows"

    # heuristica por conjunto de portas
    if 3389 in abertas or {135, 445}.issubset(abertas):
        return "Windows (provável)"
    if 22 in abertas:
        return "Linux/Unix (provável)"
    if 161 in abertas:
        return "Dispositivo de rede (provável)"
    return None


def calcular_score(portas: list[dict]) -> tuple[int, str]:
    """Score de risco 0-100 + rótulo, a partir das portas (severidade + CVEs casados).

    Cada porta pode ter 'severidade' e uma lista 'cves' (cada um com 'severidade').
    """
    score = 0
    for p in portas:
        score += _PESO_SEV.get(p.get("severidade"), 0)
        for c in p.get("cves") or []:
            score += _PESO_CVE.get(c.get("severidade"), 0)
    score = min(score, 100)

    if score == 0:
        rotulo = "nenhum"
    elif score < 20:
        rotulo = "baixo"
    elif score < 50:
        rotulo = "médio"
    elif score < 80:
        rotulo = "alto"
    else:
        rotulo = "crítico"
    return score, rotulo
