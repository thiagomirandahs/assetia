"""Leitura da tabela ARP do SO para mapear IP -> MAC.

Estrategia: roda `arp -a` (Windows/Linux/Mac) e parseia a saida.
Nao requer privilegios elevados na maioria dos SOs.
"""
import re
import subprocess


def ler_tabela_arp() -> dict[str, str]:
    """Retorna {ip: mac_normalizado} a partir do `arp -a`."""
    try:
        saida = subprocess.run(
            ["arp", "-a"], capture_output=True, text=True, timeout=10, check=False
        ).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    return _parse(saida)


# Aceita 00-11-22-33-44-55 (Windows) ou 00:11:22:33:44:55 (Linux/Mac)
_RX_LINHA = re.compile(
    r"(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+"
    r"(?:at\s+)?"
    r"(?P<mac>[0-9a-fA-F]{2}(?:[:\-][0-9a-fA-F]{2}){5})",
    re.IGNORECASE,
)


def _parse(saida: str) -> dict[str, str]:
    mapeamento: dict[str, str] = {}
    for linha in saida.splitlines():
        m = _RX_LINHA.search(linha)
        if not m:
            continue
        mac = m.group("mac").lower().replace("-", ":")
        if mac in ("ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00"):
            continue
        mapeamento[m.group("ip")] = mac
    return mapeamento
