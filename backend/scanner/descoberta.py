"""Descoberta de hosts: detecta redes locais e faz ping sweep retornando os IPs vivos.

USO AUTORIZADO: descubra apenas redes que voce administra.
"""
import ipaddress

import psutil

from .arp import ler_tabela_arp
from .network import ping_sweep_sync
from .oui import fabricante


def detectar_redes() -> list[dict]:
    """Redes IPv4 ativas da maquina (sem loopback / APIPA / docker / virtuais)."""
    redes = []
    for iface, addrs in psutil.net_if_addrs().items():
        nome = iface.lower()
        if "loopback" in nome or "vethernet" in nome or "docker" in nome or "vmware" in nome:
            continue
        for addr in addrs:
            if addr.family.name != "AF_INET":
                continue
            ip, mask = addr.address, addr.netmask
            if not ip or not mask or ip.startswith("127.") or ip.startswith("169.254."):
                continue
            try:
                rede = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
            except (ValueError, ipaddress.NetmaskValueError):
                continue
            if rede.num_addresses > 4096:
                continue
            redes.append({
                "interface": iface,
                "ip_local": ip,
                "cidr": str(rede),
                "hosts": rede.num_addresses - 2 if rede.num_addresses > 2 else rede.num_addresses,
            })
    return redes


def descobrir_hosts(cidr: str) -> list[dict]:
    """Ping sweep no CIDR. Retorna os hosts vivos com MAC/fabricante, ordenados por IP."""
    vivos = ping_sweep_sync(cidr)
    arp = ler_tabela_arp()
    out = []
    for h in vivos:
        mac = arp.get(h.ip)
        out.append({
            "ip": h.ip,
            "mac": mac,
            "fabricante": fabricante(mac),
            "latencia_ms": h.latencia_ms,
        })
    out.sort(key=lambda d: tuple(int(x) for x in d["ip"].split(".")))
    return out
