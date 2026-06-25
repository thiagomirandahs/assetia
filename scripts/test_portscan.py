"""Teste rápido do scanner de portas contra um alvo (default: localhost)."""
import asyncio
import sys

sys.path.insert(0, ".")
from backend.scanner.ports import scan_portas


async def main(alvo: str):
    print(f"== scan de portas em {alvo} ==")
    r = await scan_portas(alvo, timeout=1.0)
    for p in r:
        flag = f"  !! RISCO({p.severidade}): {p.risco}" if p.risco else ""
        banner = (p.banner or "")[:55]
        print(f"  {p.porta:>5}/{p.servico:<14} banner={banner!r}{flag}")
    print(f"== {len(r)} portas abertas ==")


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    asyncio.run(main(alvo))
