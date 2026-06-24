"""Descobre o fabricante de um MAC address via OUI (primeiros 3 octetos).

Usa a biblioteca `manuf` que mantem o banco da Wireshark embutido.
Fallback grosseiro embutido caso a lib nao esteja instalada.
"""
import logging

logger = logging.getLogger(__name__)

try:
    from manuf import manuf as _manuf
    _parser = _manuf.MacParser()
except ImportError:
    logger.warning("biblioteca 'manuf' nao instalada; fabricante sera 'desconhecido'")
    _parser = None


# Fallback minimo (caso manuf nao instale por algum motivo)
_FALLBACK = {
    "00:1B:21": "Intel",
    "00:50:56": "VMware",
    "08:00:27": "Oracle VirtualBox",
    "AC:DE:48": "Apple",
    "B8:27:EB": "Raspberry Pi",
    "DC:A6:32": "Raspberry Pi",
    "4C:5E:0C": "MikroTik",
    "E4:8D:8C": "Routerboard / MikroTik",
}


def fabricante(mac: str | None) -> str | None:
    if not mac:
        return None
    mac = mac.lower()
    if _parser is not None:
        try:
            v = _parser.get_manuf_long(mac) or _parser.get_manuf(mac)
            if v:
                return v
        except Exception:  # noqa: BLE001
            pass
    prefix = mac[:8].upper().replace(":", ":")
    return _FALLBACK.get(prefix)
