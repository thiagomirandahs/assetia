"""Analise de TLS/SSL: protocolo negociado, cipher, certificado e validade.

Passivo: so faz um handshake e inspeciona. USO AUTORIZADO.
"""
import logging
import socket
import ssl
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_PROTO_FRACOS = {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}


def _expiracao(cert) -> datetime | None:
    """not_valid_after compativel entre versoes do cryptography."""
    na = getattr(cert, "not_valid_after_utc", None)
    if na is not None:
        return na
    na = getattr(cert, "not_valid_after", None)
    if na is not None and na.tzinfo is None:
        return na.replace(tzinfo=timezone.utc)
    return na


def checar_tls(host: str, porta: int = 443, *, timeout: float = 4.0) -> dict:
    """Handshake TLS + inspecao do certificado. Retorna info + lista de achados."""
    info: dict = {"host": host, "porta": porta, "achados": []}

    try:
        ctx = ssl._create_unverified_context()
        with socket.create_connection((host, porta), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                info["protocolo"] = ss.version()
                ci = ss.cipher()
                info["cipher"] = ci[0] if ci else None
                der = ss.getpeercert(binary_form=True)
    except Exception as e:  # noqa: BLE001
        return {"host": host, "porta": porta, "erro": f"sem TLS: {e}", "achados": []}

    try:
        from cryptography import x509
        cert = x509.load_der_x509_certificate(der)
        info["assunto"] = cert.subject.rfc4514_string()
        info["emissor"] = cert.issuer.rfc4514_string()
        info["self_signed"] = cert.issuer == cert.subject
        na = _expiracao(cert)
        if na:
            info["expira_em"] = na.isoformat()
            dias = (na - datetime.now(timezone.utc)).days
            info["dias_para_expirar"] = dias
    except Exception as e:  # noqa: BLE001
        logger.warning("falha ao parsear cert: %s", e)

    # achados
    ach = info["achados"]
    proto = info.get("protocolo")
    if proto in _PROTO_FRACOS:
        ach.append({"severidade": "warning", "detalhe": f"Protocolo TLS obsoleto: {proto}"})
    if info.get("self_signed"):
        ach.append({"severidade": "info", "detalhe": "Certificado auto-assinado"})
    dias = info.get("dias_para_expirar")
    if dias is not None and dias < 0:
        ach.append({"severidade": "warning", "detalhe": f"Certificado EXPIRADO há {-dias} dias"})
    elif dias is not None and dias < 15:
        ach.append({"severidade": "info", "detalhe": f"Certificado expira em {dias} dias"})

    return info
