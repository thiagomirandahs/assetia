"""Reset o inventario para dados REAIS:
  1. Apaga todos os Device, Alert, ChatMessage, Scan (mantem Tenant, User, AlertRule)
  2. Detecta a rede ativa
  3. Roda scan real
  4. Reavalia regras de alerta

Uso:
    python scripts/reset_e_scan_real.py
    python scripts/reset_e_scan_real.py --rede 192.168.1.0/24
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.alerts.engine import avaliar_regras_para_tenant
from backend.core.database import SessionLocal, init_db
from backend.core.models import Alert, ChatMessage, Device, Scan, Tenant
from backend.scanner.scanner import executar_scan
from scripts.descobrir_redes import detectar_redes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rede", help="CIDR (ex: 192.168.1.0/24). Se nao informar, detecta automaticamente.")
    parser.add_argument("--tenant", type=int, default=1)
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        tenant = db.get(Tenant, args.tenant)
        if not tenant:
            sys.exit(f"[X] Tenant id={args.tenant} nao existe.")

        # 1) Limpa dados ficticios
        print(">>> Limpando dados ficticios...")
        ndev = db.query(Device).filter(Device.tenant_id == tenant.id).delete(synchronize_session=False)
        nalt = db.query(Alert).filter(Alert.tenant_id == tenant.id).delete(synchronize_session=False)
        nmsg = db.query(ChatMessage).filter(ChatMessage.tenant_id == tenant.id).delete(synchronize_session=False)
        nscn = db.query(Scan).filter(Scan.tenant_id == tenant.id).delete(synchronize_session=False)
        db.commit()
        print(f"    apagados: {ndev} devices, {nalt} alertas, {nmsg} mensagens, {nscn} scans")

        # 2) Detecta rede se nao informada
        if args.rede:
            rede = args.rede
        else:
            redes = detectar_redes()
            if not redes:
                sys.exit("[X] Nenhuma rede IPv4 detectada. Use --rede X.X.X.0/24")
            rede = redes[0]["cidr"]
            print(f"\n>>> Rede detectada: {rede} (via {redes[0]['interface']})")

        # 3) Scan real
        print(f"\n>>> Rodando scan real em {rede}... (pode levar 30-60s para /24)")
        achados, novos = executar_scan(db, tenant_id=tenant.id, rede=rede)
        print(f"    [OK] {achados} dispositivos descobertos ({novos} novos)")

        # 4) Reavalia regras
        print("\n>>> Reavaliando regras de alerta...")
        res = avaliar_regras_para_tenant(db, tenant.id)
        print(f"    [OK] {res['gerados_total']} alertas gerados")

        # 5) Mostra resumo
        print("\n=== RESUMO ===")
        total = db.query(Device).filter(Device.tenant_id == tenant.id).count()
        online = db.query(Device).filter(Device.tenant_id == tenant.id, Device.online.is_(True)).count()
        com_mac = db.query(Device).filter(Device.tenant_id == tenant.id, Device.mac.isnot(None)).count()
        print(f"  Total de dispositivos:    {total}")
        print(f"  Online:                   {online}")
        print(f"  Com MAC identificado:     {com_mac}")
        print(f"  Alertas gerados:          {res['gerados_total']}")
        print()
        print("Veja no dashboard: http://localhost:5173")
    finally:
        db.close()


if __name__ == "__main__":
    main()
