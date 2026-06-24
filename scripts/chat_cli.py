"""Chat com o agente IA direto no terminal (sem frontend).

Uso:
    python scripts/chat_cli.py
    python scripts/chat_cli.py --tenant 1
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.ai.agent import responder
from backend.core.database import SessionLocal, init_db
from backend.core.models import Tenant


def main():
    parser = argparse.ArgumentParser(description="Chat com o agente AssetIA (CLI)")
    parser.add_argument("--tenant", type=int, default=1, help="ID do tenant (padrao 1)")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    tenant = db.get(Tenant, args.tenant)
    if not tenant:
        print(f"[X] Tenant id={args.tenant} nao existe. Rode 'python scripts/seed_demo_data.py' primeiro.")
        sys.exit(1)

    print(f"AssetIA chat — tenant '{tenant.nome}'.  (Ctrl+C para sair)")
    print(f"Tente:  'quantos dispositivos eu tenho?'  /  'me da um resumo'  /  'apareceu algo novo?'")
    print()

    try:
        while True:
            try:
                pergunta = input("Voce> ").strip()
            except EOFError:
                break
            if not pergunta:
                continue
            try:
                resposta, audit = responder(db=db, tenant_id=tenant.id, pergunta=pergunta)
            except Exception as e:  # noqa: BLE001
                print(f"[X] Erro: {e}")
                continue
            print(f"AssetIA> {resposta}")
            if audit:
                tools_chamadas = ", ".join(a["tool"] for a in audit)
                print(f"        (tools: {tools_chamadas})")
            print()
    except KeyboardInterrupt:
        print("\nAte logo!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
