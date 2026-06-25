"""Compliance: mapeia os achados + baseline para controles (CIS/NIST/LGPD) e calcula % conforme.

Heuristico e pragmatico — nao substitui auditoria formal, mas da um retrato rapido.
"""
from sqlalchemy.orm import Session

from ..core.models import Device, Porta


def _tem_servico(db, tenant_id, servicos: set[str], so_critico=False) -> bool:
    q = db.query(Porta).filter(Porta.tenant_id == tenant_id, Porta.servico.in_(servicos))
    if so_critico:
        q = q.filter(Porta.severidade == "critical")
    return db.query(q.exists()).scalar()


def avaliar_compliance(db: Session, *, tenant_id: int, baseline: dict | None = None) -> dict:
    b = {c["chave"]: c["estado"] for c in (baseline or {}).get("checks", [])}

    def base_ok(chave):  # baseline conforme? (None se desconhecido/ausente)
        e = b.get(chave)
        return True if e == "ok" else (False if e == "falha" else None)

    cred_default = db.query(
        db.query(Device).filter(Device.tenant_id == tenant_id, Device.tags.like("%credencial-default%")).exists()
    ).scalar()

    # (controle, frameworks, conforme: True/False/None)
    controles = [
        ("Sem SMB/SMBv1 exposto", "CIS 4 · NIST PR.PT", not _tem_servico(db, tenant_id, {"smb", "netbios-ssn"}, True)),
        ("Sem serviços legados em texto claro (Telnet/FTP)", "CIS 4 · ISO A.13", not _tem_servico(db, tenant_id, {"telnet", "ftp"})),
        ("Sem banco de dados exposto à rede", "CIS 3 · LGPD Art.46", not _tem_servico(db, tenant_id, {"mysql", "postgres", "mssql", "oracle", "mongodb", "redis"})),
        ("Sem RDP/VNC crítico exposto", "CIS 4 · NIST PR.AC", not _tem_servico(db, tenant_id, {"rdp", "vnc"}, True)),
        ("Sem credenciais padrão em uso", "CIS 5 · NIST PR.AC", not cred_default),
        ("Firewall ativo", "CIS 4 · NIST PR.PT", base_ok("firewall") if _WIN_KEY(b) else base_ok("firewall_linux")),
        ("Disco cifrado", "CIS 3 · LGPD Art.46", base_ok("bitlocker")),
        ("Antivírus/EDR ativo", "CIS 10 · NIST DE.CM", base_ok("defender_realtime")),
        ("SMBv1 desativado (host local)", "CIS 4", base_ok("smb1_desativado")),
    ]

    itens = []
    conformes = total = 0
    for nome, frameworks, ok in controles:
        if ok is None:
            estado = "n/a"
        elif ok:
            estado = "conforme"
            conformes += 1
            total += 1
        else:
            estado = "não conforme"
            total += 1
        itens.append({"controle": nome, "frameworks": frameworks, "estado": estado})

    pct = round(100 * conformes / total) if total else 0
    return {
        "percentual": pct,
        "conformes": conformes,
        "avaliados": total,
        "pendentes": total - conformes,
        "itens": itens,
    }


def _WIN_KEY(b: dict) -> bool:
    return "firewall" in b or "bitlocker" in b
