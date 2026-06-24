"""Orquestrador do scanner: ping sweep + ARP + OUI + persistencia."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..core.models import Device
from .arp import ler_tabela_arp
from .network import ping_sweep_sync
from .oui import fabricante


def executar_scan(db: Session, *, tenant_id: int, rede: str) -> tuple[int, int]:
    """Faz a varredura completa e retorna (achados, novos).

    Pipeline:
      1. Ping sweep paralelo
      2. Le tabela ARP (so funciona em hosts que ja foram pingados)
      3. Para cada IP vivo, faz upsert no banco (insere novo ou atualiza ultima_visao)
      4. Marca offline quem nao apareceu
    """
    hosts_vivos = ping_sweep_sync(rede)
    arp = ler_tabela_arp()

    achados = 0
    novos = 0
    agora = datetime.now(timezone.utc)

    for host in hosts_vivos:
        achados += 1
        mac = arp.get(host.ip)
        vendor = fabricante(mac)

        dev = db.query(Device).filter(
            Device.tenant_id == tenant_id, Device.ip == host.ip
        ).first()

        if dev is None:
            dev = Device(
                tenant_id=tenant_id,
                ip=host.ip,
                mac=mac,
                fabricante=vendor,
                online=True,
                primeira_visao=agora,
                ultima_visao=agora,
            )
            db.add(dev)
            novos += 1
        else:
            if mac and not dev.mac:
                dev.mac = mac
            if vendor and not dev.fabricante:
                dev.fabricante = vendor
            dev.online = True
            dev.ultima_visao = agora

    db.commit()

    # Marca offline quem nao apareceu (apenas devices que estavam online)
    db.query(Device).filter(
        Device.tenant_id == tenant_id,
        Device.online.is_(True),
        Device.ultima_visao < agora,
    ).update({"online": False}, synchronize_session=False)
    db.commit()

    return achados, novos
