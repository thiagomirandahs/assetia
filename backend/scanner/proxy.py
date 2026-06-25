"""Suporte a proxy SOCKS5 (privacidade / OSINT autorizado) — ex: Tor em 127.0.0.1:9050.

Roteia as conexoes do scanner por um proxy. USO LEGITIMO: sua privacidade, OSINT, ou
red team com escopo autorizado. NAO use pra ocultar ataque a alvo nao autorizado —
isso e o oposto de pentest etico.
"""
import logging

from ..core.config import get_settings

logger = logging.getLogger(__name__)

_runtime_proxy: str | None = None  # override em memoria (settavel via API, sem restart)


def proxy_atual() -> str:
    """Proxy SOCKS em uso: override de runtime tem prioridade; senao o do .env."""
    if _runtime_proxy is not None:
        return _runtime_proxy
    return get_settings().socks_proxy


def set_proxy(url: str | None) -> None:
    global _runtime_proxy
    _runtime_proxy = url or None
    logger.info("socks_proxy runtime=%s", _runtime_proxy)


def status_proxy(timeout: float = 8.0) -> dict:
    """Testa o proxy buscando o IP de saida (prova que o trafego sai mascarado)."""
    url = proxy_atual()
    if not url:
        return {"configurado": False, "proxy": None}
    try:
        import httpx
        r = httpx.get("https://api.ipify.org?format=json", proxy=url, timeout=timeout)
        return {"configurado": True, "proxy": url, "exit_ip": r.json().get("ip")}
    except Exception as e:  # noqa: BLE001
        return {"configurado": True, "proxy": url, "erro": str(e)}
