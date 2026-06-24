"""Ping sweep paralelo com asyncio.

Usa o comando `ping` do sistema operacional (multiplataforma) ao inves de
levantar socket raw, evitando exigir CAP_NET_RAW na maquina onde roda.
"""
import asyncio
import ipaddress
import platform
import re
from dataclasses import dataclass


@dataclass
class HostVivo:
    ip: str
    latencia_ms: float | None


def _flags_do_ping() -> list[str]:
    """Flags do ping conforme o SO: 1 pacote, timeout curto."""
    if platform.system().lower() == "windows":
        return ["-n", "1", "-w", "1500"]  # -w em ms
    return ["-c", "1", "-W", "2"]  # -W em segundos (Linux/Mac)


async def _ping_um(ip: str) -> HostVivo | None:
    """Retorna HostVivo se respondeu, None se nao."""
    cmd = ["ping", *_flags_do_ping(), ip]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
    except (asyncio.TimeoutError, FileNotFoundError):
        return None

    if proc.returncode != 0:
        return None

    saida = stdout.decode(errors="ignore")
    latencia = _extrair_latencia(saida)
    return HostVivo(ip=ip, latencia_ms=latencia)


def _extrair_latencia(saida_ping: str) -> float | None:
    """Tenta extrair a latencia em ms da saida do ping."""
    # Linux/Mac: "time=1.23 ms"
    # Windows:   "Tempo=1ms" ou "time=1ms" ou "tempo<1ms"
    m = re.search(r"(?:time|tempo)[=<]\s*([\d.]+)\s*ms", saida_ping, re.IGNORECASE)
    return float(m.group(1)) if m else None


async def ping_sweep(rede: str, *, max_paralelo: int = 64) -> list[HostVivo]:
    """Faz ping em todos os hosts de uma rede CIDR. Retorna so os que responderam."""
    try:
        net = ipaddress.ip_network(rede, strict=False)
    except ValueError as e:
        raise ValueError(f"rede CIDR invalida: {rede}") from e

    hosts = [str(h) for h in net.hosts()]
    if len(hosts) > 2048:
        raise ValueError(f"rede muito grande ({len(hosts)} hosts). Limite: /21 (2046 hosts).")

    sem = asyncio.Semaphore(max_paralelo)

    async def _wrap(ip: str):
        async with sem:
            return await _ping_um(ip)

    resultados = await asyncio.gather(*[_wrap(ip) for ip in hosts])
    return [r for r in resultados if r is not None]


def ping_sweep_sync(rede: str, *, max_paralelo: int = 64) -> list[HostVivo]:
    """Wrapper sincrono para usar fora de contextos async (ex: workers)."""
    return asyncio.run(ping_sweep(rede, max_paralelo=max_paralelo))
