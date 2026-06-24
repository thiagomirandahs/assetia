"""Roda um scan na rede direto do CLI, sem precisar do servidor HTTP.

Uso:
    python scripts/run_scan.py 192.168.0.0/24
    python scripts/run_scan.py 192.168.0.0/24 --tenant 1
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.database import SessionLocal, init_db
from backend.core.models import Tenant
from backend.scanner.scanner import executar_scan


def main():
    parser = argparse.ArgumentParser(description="Scanner de rede AssetIA (CLI)")
    parser.add_argument("rede", help="Rede em CIDR (ex: 192.168.0.0/24)")
    parser.add_argument("--tenant", type=int, default=1, help="ID do tenant (padrao 1)")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        tenant = db.get(Tenant, args.tenant)
        if not tenant:
            print(f"[X] Tenant id={args.tenant} nao existe. Rode 'python scripts/seed_demo_data.py' primeiro.")
            sys.exit(1)

        print(f"[*] Iniciando scan em {args.rede} (tenant={tenant.nome})...")
        achados, novos = executar_scan(db, tenant_id=tenant.id, rede=args.rede)
        print(f"[OK] Achados:   {achados} dispositivos online")
        print(f"[OK] Novos:     {novos} (descobertos pela primeira vez)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
