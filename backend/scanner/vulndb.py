"""Base curada de assinaturas de vulnerabilidade (banner/versao -> CVE).

Heuristica OFFLINE e conservadora: casa padroes de banner com CVEs publicas conhecidas.
Nao substitui um scanner de vuln completo (Nessus/OpenVAS) — serve de correlacao rapida
durante o recon, pra apontar "onde olhar".
"""
import re

# (regex no banner, cve, descricao curta, severidade)
ASSINATURAS: list[tuple[str, str, str, str]] = [
    (r"vsftpd\s*2\.3\.4", "CVE-2011-2523", "vsftpd 2.3.4 traz backdoor (shell na porta 6200)", "critical"),
    (r"ProFTPD\s*1\.3\.5\b", "CVE-2015-3306", "ProFTPD 1.3.5 mod_copy permite RCE remoto", "critical"),
    (r"OpenSSH_(?:[0-6]\.|7\.[0-6])", "CVE-2018-15473", "OpenSSH < 7.7 permite enumeracao de usuarios", "warning"),
    (r"Apache/2\.4\.49\b", "CVE-2021-41773", "Apache 2.4.49: path traversal + RCE", "critical"),
    (r"Apache/2\.4\.50\b", "CVE-2021-42013", "Apache 2.4.50: path traversal + RCE", "critical"),
    (r"nginx/1\.(?:[0-9]|1[0-9]|20\.0)\b", "CVE-2021-23017", "nginx < 1.20.1: off-by-one no resolver", "warning"),
    (r"Microsoft-IIS/6\.0", "CVE-2017-7269", "IIS 6.0 WebDAV: buffer overflow (RCE)", "critical"),
    (r"Exim\s*4\.(?:[0-8]?[0-9]|9[0-1])\b", "CVE-2019-10149", "Exim 'Return of the WIZard': RCE", "critical"),
    (r"OpenSSL/1\.0\.1[a-f]", "CVE-2014-0160", "OpenSSL 1.0.1a-f: 'Heartbleed' (vaza memoria)", "critical"),
    (r"PHP/(?:5\.|7\.0)", "CVE-2019-11043", "PHP-FPM antigo: possivel RCE (underflow)", "warning"),
    (r"Jenkins", "CVE-2024-23897", "Jenkins CLI: leitura arbitraria de arquivos (confira a versao)", "warning"),
]

# Servicos que, mesmo SEM versao no banner, tem exposicao classica associada a uma CVE/tecnica.
EXPOSICAO_SERVICO: dict[str, tuple[str, str, str]] = {
    "telnet": ("CWE-319", "Credenciais trafegam em texto claro (sem criptografia)", "critical"),
    "smb": ("CVE-2017-0144", "SMB exposto — alvo de EternalBlue/WannaCry se SMBv1 ativo", "critical"),
    "rdp": ("CVE-2019-0708", "RDP exposto — 'BlueKeep' (RCE pre-auth) em versoes antigas", "critical"),
    "redis": ("CWE-306", "Redis sem autenticacao permite RCE (via modulo/cron)", "critical"),
    "docker-api": ("CWE-306", "Docker API sem TLS = executar container como root (RCE)", "critical"),
    "elasticsearch": ("CWE-306", "Elasticsearch sem auth: leitura/alteracao dos indices", "critical"),
    "mongodb": ("CWE-306", "MongoDB sem auth: leitura/escrita total dos dados", "critical"),
    "memcached": ("CVE-2016-8704", "Memcached exposto: amplificacao DDoS e vazamento", "warning"),
    "vnc": ("CWE-306", "VNC frequentemente sem senha — controle total da tela", "critical"),
}


def casar_cves(servico: str | None, banner: str | None) -> list[dict]:
    """Retorna matches [{cve, descricao, severidade}] para um servico/banner."""
    achados: list[dict] = []
    vistos: set[str] = set()

    if banner:
        for regex, cve, desc, sev in ASSINATURAS:
            if re.search(regex, banner, re.IGNORECASE) and cve not in vistos:
                achados.append({"cve": cve, "descricao": desc, "severidade": sev})
                vistos.add(cve)

    if servico:
        exp = EXPOSICAO_SERVICO.get(servico)
        if exp and exp[0] not in vistos:
            achados.append({"cve": exp[0], "descricao": exp[1], "severidade": exp[2]})
            vistos.add(exp[0])

    return achados
