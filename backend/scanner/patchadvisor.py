"""Patch Advisor: a partir dos CVEs/serviços encontrados, sugere o que atualizar/corrigir.

Agrega os CVEs casados em todos os hosts e prioriza por severidade.
"""
import json
from collections import defaultdict

from sqlalchemy.orm import Session

from ..core.models import Device, Porta

_PESO = {"critical": 3, "warning": 2, "info": 1, None: 0}

# acao de patch por servico (generico)
_ACAO = {
    "smb": "Aplicar patches do Windows e desativar SMBv1",
    "rdp": "Atualizar Windows (BlueKeep) e exigir NLA",
    "ssh": "Atualizar o OpenSSH para a versão estável",
    "ftp": "Atualizar o servidor FTP / migrar para SFTP",
    "http": "Atualizar o servidor web e o app",
    "https": "Atualizar o servidor web; renovar TLS",
    "redis": "Atualizar e exigir autenticação",
    "elasticsearch": "Atualizar e habilitar segurança",
}


def aconselhar_patches(db: Session, *, tenant_id: int) -> dict:
    rows = (
        db.query(Porta.servico, Porta.cves, Porta.banner, Device.ip)
        .join(Device, Device.id == Porta.device_id)
        .filter(Porta.tenant_id == tenant_id)
        .all()
    )

    por_cve = defaultdict(lambda: {"cve": "", "descricao": "", "severidade": None, "hosts": set()})
    por_servico = defaultdict(set)
    for servico, cves_json, banner, ip in rows:
        if servico in _ACAO:
            por_servico[servico].add(ip)
        try:
            for c in (json.loads(cves_json) if cves_json else []):
                e = por_cve[c["cve"]]
                e["cve"] = c["cve"]
                e["descricao"] = c.get("descricao", "")
                e["severidade"] = c.get("severidade")
                e["hosts"].add(ip)
        except Exception:  # noqa: BLE001
            pass

    cves = sorted(
        ({**v, "hosts": sorted(v["hosts"])} for v in por_cve.values()),
        key=lambda x: -_PESO.get(x["severidade"], 0),
    )
    acoes = [{"servico": s, "acao": _ACAO[s], "hosts": sorted(h)} for s, h in sorted(por_servico.items())]

    return {
        "total_cves": len(cves),
        "criticos": sum(1 for c in cves if c["severidade"] == "critical"),
        "cves": cves,
        "acoes_por_servico": acoes,
    }
