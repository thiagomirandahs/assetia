"""Descobre o fabricante de um MAC address via OUI (primeiros 3 octetos).

Pipeline com 3 niveis de fallback:
  1. biblioteca `manuf` (banco local da Wireshark, instantaneo)
  2. fallback embutido (10 fabricantes comuns)
  3. API publica https://api.macvendors.com (1000 req/dia gratis, com cache em memoria)
"""
import logging
import time

import httpx

logger = logging.getLogger(__name__)

# Cache em memoria para evitar HTTP repetido (chave: prefixo de 8 chars do MAC)
_CACHE: dict[str, tuple[float, str | None]] = {}
_CACHE_TTL = 60 * 60 * 24 * 7  # 7 dias

try:
    from manuf import manuf as _manuf
    _parser = _manuf.MacParser()
except ImportError:
    logger.warning("biblioteca 'manuf' nao instalada")
    _parser = None


_FALLBACK = {
    "00:1B:21": "Intel",
    "00:50:56": "VMware",
    "08:00:27": "Oracle VirtualBox",
    "AC:DE:48": "Apple",
    "B8:27:EB": "Raspberry Pi",
    "DC:A6:32": "Raspberry Pi",
    "4C:5E:0C": "MikroTik",
    "E4:8D:8C": "MikroTik (Routerboard)",
    "00:25:B3": "HP",
    "F4:30:B9": "HP",
}


def _lookup_online(mac: str) -> str | None:
    """Consulta api.macvendors.com. Retorna o nome do fabricante ou None."""
    prefix = mac.upper()[:8]
    agora = time.time()

    # cache hit
    entry = _CACHE.get(prefix)
    if entry and (agora - entry[0]) < _CACHE_TTL:
        return entry[1]

    try:
        r = httpx.get(f"https://api.macvendors.com/{mac}", timeout=3)
        if r.status_code == 200:
            nome = r.text.strip()
            _CACHE[prefix] = (agora, nome)
            return nome
        if r.status_code == 404:
            _CACHE[prefix] = (agora, None)
            return None
    except Exception as e:  # noqa: BLE001
        logger.debug("oui online falhou para %s: %s", mac, e)
    return None


def fabricante(mac: str | None) -> str | None:
    """Retorna o fabricante do MAC, ou None se nao encontrado."""
    if not mac:
        return None
    mac = mac.lower()

    # 1) manuf local (instantaneo)
    if _parser is not None:
        try:
            v = _parser.get_manuf_long(mac) or _parser.get_manuf(mac)
            if v:
                return v
        except Exception:  # noqa: BLE001
            pass

    # 2) fallback embutido (prefixo case-insensitive)
    prefix_upper = mac.upper()[:8]
    if prefix_upper in _FALLBACK:
        return _FALLBACK[prefix_upper]

    # 3) API publica com cache
    return _lookup_online(mac)
