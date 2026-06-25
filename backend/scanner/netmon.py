"""Monitor de rede em tempo real: throughput (upload/download) das interfaces locais.

Usa psutil.net_io_counters() amostrado no tempo para calcular a TAXA (bytes/s) de
upload e download da máquina — a visão de banda da rede a partir deste host.
(Banda por host remoto exigiria SNMP no switch ou captura de pacotes — fora deste módulo.)
"""
import time

import psutil


def _agregado() -> tuple[int, int]:
    c = psutil.net_io_counters(pernic=False)
    return c.bytes_sent, c.bytes_recv


def amostra(intervalo: float = 1.0) -> dict:
    """Uma leitura: mede a taxa de up/down ao longo de `intervalo` segundos."""
    s0, r0 = _agregado()
    time.sleep(intervalo)
    s1, r1 = _agregado()
    return {
        "upload_bps": max(0.0, (s1 - s0) / intervalo),
        "download_bps": max(0.0, (r1 - r0) / intervalo),
        "upload_total": s1,
        "download_total": r1,
    }


def stream(intervalo: float = 1.0):
    """Gerador infinito de amostras (para SSE). O cliente fecha ao sair."""
    s_prev, r_prev = _agregado()
    while True:
        time.sleep(intervalo)
        s, r = _agregado()
        yield {
            "upload_bps": max(0.0, (s - s_prev) / intervalo),
            "download_bps": max(0.0, (r - r_prev) / intervalo),
            "upload_total": s,
            "download_total": r,
        }
        s_prev, r_prev = s, r


def por_interface() -> list[dict]:
    """Totais acumulados por interface (sem loopback/virtuais)."""
    out = []
    for nome, c in psutil.net_io_counters(pernic=True).items():
        low = nome.lower()
        if low.startswith("lo") or "loopback" in low:
            continue
        out.append({
            "interface": nome,
            "upload_total": c.bytes_sent,
            "download_total": c.bytes_recv,
        })
    return out
