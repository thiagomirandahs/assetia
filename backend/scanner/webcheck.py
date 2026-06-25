"""Checagens de seguranca web (recon de aplicacao) — passivo + leve.

Analisa headers de seguranca, caminhos sensiveis comuns e metodos HTTP perigosos.
USO AUTORIZADO apenas. Nao explora nada — so observa o que esta exposto.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

# Headers de seguranca esperados. (header, descricao se faltar, severidade)
HEADERS_SEGURANCA = [
    ("strict-transport-security", "Sem HSTS — conexao pode ser rebaixada p/ HTTP", "warning"),
    ("content-security-policy", "Sem CSP — maior risco de XSS/injecao", "warning"),
    ("x-frame-options", "Sem X-Frame-Options — vulneravel a clickjacking", "warning"),
    ("x-content-type-options", "Sem X-Content-Type-Options (nosniff)", "info"),
    ("referrer-policy", "Sem Referrer-Policy — pode vazar URLs", "info"),
]

# Caminhos sensiveis comuns. (path, descricao, severidade se existir)
CAMINHOS = [
    ("/.git/HEAD", "Repositorio .git exposto — vaza codigo-fonte", "critical"),
    ("/.env", "Arquivo .env exposto — pode vazar segredos/credenciais", "critical"),
    ("/.aws/credentials", "Credenciais AWS expostas", "critical"),
    ("/backup.zip", "Backup exposto", "warning"),
    ("/db.sql", "Dump de banco exposto", "warning"),
    ("/phpinfo.php", "phpinfo() exposto — vaza configuracao", "warning"),
    ("/server-status", "Apache server-status exposto", "warning"),
    ("/.well-known/security.txt", "security.txt presente (boa pratica)", "info"),
    ("/robots.txt", "robots.txt presente (util p/ recon)", "info"),
    ("/admin", "Painel /admin acessivel", "info"),
]

_METODOS_PERIGOSOS = {"TRACE", "TRACK", "PUT", "DELETE", "CONNECT"}


def _base_url(host: str, porta: int, https: bool) -> str:
    esquema = "https" if https else "http"
    porta_padrao = (https and porta == 443) or (not https and porta == 80)
    return f"{esquema}://{host}" + ("" if porta_padrao else f":{porta}")


def checar_web(host: str, porta: int, *, https: bool = False, timeout: float = 4.0) -> list[dict]:
    """Roda as checagens web contra host:porta. Retorna lista de achados."""
    base = _base_url(host, porta, https)
    achados: list[dict] = []

    with httpx.Client(verify=False, timeout=timeout, follow_redirects=True) as cli:
        # 1) headers de seguranca + disclosure de versao
        try:
            r = cli.get(base + "/")
        except Exception as e:  # noqa: BLE001
            return [{"tipo": "erro", "severidade": "info", "detalhe": f"sem resposta HTTP em {base}: {e}"}]

        headers = {k.lower(): v for k, v in r.headers.items()}
        for h, desc, sev in HEADERS_SEGURANCA:
            if h == "strict-transport-security" and not https:
                continue  # HSTS so faz sentido em HTTPS
            if h not in headers:
                achados.append({"tipo": "header", "severidade": sev, "detalhe": desc})

        if "server" in headers:
            achados.append({"tipo": "disclosure", "severidade": "info",
                            "detalhe": f"Server header expoe: {headers['server']}"})
        if "x-powered-by" in headers:
            achados.append({"tipo": "disclosure", "severidade": "info",
                            "detalhe": f"X-Powered-By expoe: {headers['x-powered-by']}"})

        # 2) listagem de diretorio
        corpo = (r.text or "")[:2000].lower()
        if "index of /" in corpo:
            achados.append({"tipo": "dir-listing", "severidade": "warning",
                            "detalhe": "Listagem de diretorio habilitada na raiz"})

        # 3) metodos HTTP perigosos
        try:
            opt = cli.request("OPTIONS", base + "/")
            allow = opt.headers.get("allow", "")
            perigosos = sorted(_METODOS_PERIGOSOS & {m.strip().upper() for m in allow.split(",")})
            if perigosos:
                achados.append({"tipo": "metodos", "severidade": "warning",
                                "detalhe": f"Metodos perigosos habilitados: {', '.join(perigosos)}"})
        except Exception:  # noqa: BLE001
            pass

        # 4) caminhos sensiveis
        for path, desc, sev in CAMINHOS:
            try:
                rr = cli.get(base + path)
            except Exception:  # noqa: BLE001
                continue
            if rr.status_code in (200, 401, 403):
                estado = "acessivel" if rr.status_code == 200 else f"existe (HTTP {rr.status_code})"
                achados.append({"tipo": "path", "severidade": sev, "detalhe": f"{path} — {desc} [{estado}]"})

    return achados
