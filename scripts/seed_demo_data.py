"""Popula o banco com dados ficticios para demonstracao.

Cria:
  - 1 tenant 'Demo'
  - 1 usuario admin (admin@example.com / demo123)
  - 25 dispositivos variados (servidores, estacoes, impressoras, IoT, switches)

Uso:
    python scripts/seed_demo_data.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import random

from backend.core.auth import hash_senha
from backend.core.database import SessionLocal, init_db
from backend.core.models import Device, Tenant, User


def main():
    init_db()
    db = SessionLocal()
    try:
        if db.query(Tenant).count() > 0:
            print("[!] Ja existem dados no banco. Apague assetia.sqlite para re-seedar.")
            return

        tenant = Tenant(nome="Demo")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        admin = User(
            tenant_id=tenant.id,
            email="admin@example.com",
            senha_hash=hash_senha("demo123"),
            nome="Administrador Demo",
            role="admin",
        )
        db.add(admin)

        devices_seed = [
            ("srv-app-01",       "10.10.10.5",  "00:50:56:a1:b2:c3", "VMware",     "Ubuntu",  "servidor",  "10"),
            ("srv-db-01",        "10.10.10.7",  "00:50:56:a1:b2:c4", "VMware",     "Debian",  "servidor",  "10"),
            ("srv-app-02",       "10.10.10.8",  "00:50:56:a1:b2:c5", "VMware",     "Ubuntu",  "servidor",  "10"),
            ("dc-01",            "10.10.10.10", "ac:1f:6b:11:22:33", "Dell",       "Windows", "servidor",  "10"),
            ("dc-02",            "10.10.10.11", "ac:1f:6b:11:22:34", "Dell",       "Windows", "servidor",  "10"),
            ("estacao-rh-01",    "10.10.20.21", "f4:30:b9:aa:bb:01", "HP",         "Windows", "estacao",   "20"),
            ("estacao-rh-02",    "10.10.20.22", "f4:30:b9:aa:bb:02", "HP",         "Windows", "estacao",   "20"),
            ("estacao-financ-01","10.10.20.31", "00:1b:21:dd:ee:01", "Intel",      "Windows", "estacao",   "20"),
            ("notebook-ceo",     "10.10.20.45", "ac:de:48:ff:ff:01", "Apple",      "macOS",   "estacao",   "20"),
            ("notebook-cto",     "10.10.20.46", "ac:de:48:ff:ff:02", "Apple",      "macOS",   "estacao",   "20"),
            ("notebook-thiago",  "10.10.20.50", "08:00:27:de:ad:01", "Oracle VBox","Ubuntu",  "estacao",   "20"),
            ("imp-recepcao",     "10.10.30.10", "00:25:b3:11:22:33", "HP",         None,      "impressora","30"),
            ("imp-financ",       "10.10.30.11", "00:25:b3:11:22:34", "HP",         None,      "impressora","30"),
            ("imp-rh",           "10.10.30.12", "00:80:77:aa:bb:cc", "Brother",    None,      "impressora","30"),
            ("rb-core-01",       "10.10.0.1",   "4c:5e:0c:00:11:22", "MikroTik",   "RouterOS","switch",    None),
            ("rb-edge-01",       "10.10.0.2",   "4c:5e:0c:00:11:23", "MikroTik",   "RouterOS","switch",    None),
            ("rb-acesso-01",     "10.10.0.3",   "4c:5e:0c:00:11:24", "MikroTik",   "RouterOS","switch",    None),
            ("ap-andar1",        "10.10.40.10", "e4:8d:8c:11:22:33", "MikroTik",   "RouterOS","ap",        "40"),
            ("ap-andar2",        "10.10.40.11", "e4:8d:8c:11:22:34", "MikroTik",   "RouterOS","ap",        "40"),
            ("camera-rec",       "10.10.50.10", "00:1b:21:cam:01:00", "Intel",     None,      "iot",       "50"),
            ("camera-corredor",  "10.10.50.11", "00:1b:21:cam:02:00", "Intel",     None,      "iot",       "50"),
            ("ponto-rep-rh",     "10.10.50.20", "b8:27:eb:11:22:33",  "Raspberry Pi", "Linux", "iot",      "50"),
            ("nas-backup",       "10.10.10.50", "00:11:32:bb:cc:dd",  "Synology",   "Linux",  "servidor",  "10"),
            ("?-dispositivo-novo","10.10.20.99","aa:bb:cc:dd:ee:ff",  None,         None,     None,        "20"),
            ("?-iot-suspeito",   "10.10.50.99", "11:22:33:44:55:66",  None,         None,     None,        "50"),
        ]

        agora = datetime.now(timezone.utc)
        for i, (hostname, ip, mac, vendor, so, tipo, vlan) in enumerate(devices_seed):
            # Variacao realista de "primeira_visao" e "ultima_visao"
            primeira = agora - timedelta(days=random.randint(1, 200))
            ultima_offset = random.choice([
                timedelta(minutes=random.randint(0, 30)),   # online recente
                timedelta(minutes=random.randint(0, 30)),
                timedelta(minutes=random.randint(0, 30)),
                timedelta(days=random.randint(2, 60)),       # offline ha um tempo
            ])
            ultima = agora - ultima_offset
            online = ultima_offset.total_seconds() < 3600  # online se visto na ultima hora

            # Os ultimos 2 "?-..." sao recentes (descoberta nova)
            if hostname.startswith("?"):
                primeira = agora - timedelta(days=random.randint(0, 3))
                ultima = agora - timedelta(minutes=random.randint(0, 60))
                online = True

            d = Device(
                tenant_id=tenant.id, hostname=hostname, ip=ip, mac=mac,
                fabricante=vendor, so=so, tipo=tipo, vlan=vlan,
                online=online, primeira_visao=primeira, ultima_visao=ultima,
            )
            db.add(d)

        db.commit()
        print(f"[OK] Tenant criado:   {tenant.nome} (id={tenant.id})")
        print(f"[OK] Admin criado:    admin@example.com / demo123")
        print(f"[OK] Dispositivos:    {len(devices_seed)} inseridos")
        print()
        print("Para subir o servidor:  uvicorn backend.main:app --reload")
        print("Para abrir as docs:     http://localhost:8000/docs")
    finally:
        db.close()


if __name__ == "__main__":
    main()
