"""Detecta as redes IPv4 ativas da maquina (sem loopback / APIPA / docker).

Uso:
    python scripts/descobrir_redes.py
"""
import ipaddress
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psutil


def detectar_redes() -> list[dict]:
    redes = []
    for iface, addrs in psutil.net_if_addrs().items():
        nome_lower = iface.lower()
        # Pula loopback e interfaces virtuais comuns
        if "loopback" in nome_lower or "vethernet" in nome_lower or "docker" in nome_lower:
            continue
        for addr in addrs:
            if addr.family.name != "AF_INET":
                continue
            ip = addr.address
            mask = addr.netmask
            if not ip or not mask:
                continue
            if ip.startswith("127.") or ip.startswith("169.254."):
                continue
            try:
                rede = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
            except (ValueError, ipaddress.NetmaskValueError):
                continue
            if rede.num_addresses > 4096:
                continue  # ignora redes /20 ou maiores
            redes.append({
                "interface": iface,
                "ip_local": ip,
                "mascara": mask,
                "cidr": str(rede),
                "hosts": rede.num_addresses - 2 if rede.num_addresses > 2 else rede.num_addresses,
            })
    return redes


def main():
    redes = detectar_redes()
    if not redes:
        print("[X] Nenhuma rede IPv4 detectada.")
        sys.exit(1)
    print(f"\nRedes IPv4 ativas encontradas: {len(redes)}\n")
    for i, r in enumerate(redes, 1):
        print(f"  {i}. {r['cidr']:<22} ({r['hosts']} hosts)  via '{r['interface']}'  IP local: {r['ip_local']}")


if __name__ == "__main__":
    main()
