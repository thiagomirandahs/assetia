"""Checagens ATIVAS de pentest: teste de CREDENCIAIS PADRAO em servicos.

⚠️  USO ESTRITAMENTE AUTORIZADO. Isto tenta autenticar em servicos — so rode contra
alvos que voce possui ou tem autorizacao formal para testar (labs, CTF, engajamento).

Conservador de proposito: testa apenas um punhado de credenciais PADRAO conhecidas e
para no primeiro sucesso. NAO e um brute-forcer / nao aceita wordlist.
"""
import logging
import socket
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Lista CURTA e curada de credenciais default classicas (nao e wordlist).
CREDS_PADRAO = [
    ("admin", "admin"), ("admin", "password"), ("admin", ""), ("admin", "1234"),
    ("root", "root"), ("root", "toor"), ("root", ""),
    ("user", "user"), ("guest", "guest"), ("tomcat", "tomcat"),
]
FTP_ANON = [("anonymous", "anonymous@test.com"), ("ftp", "ftp")]


@dataclass
class Achado:
    servico: str
    porta: int
    usuario: str
    senha: str
    detalhe: str

    def as_dict(self) -> dict:
        return {
            "servico": self.servico, "porta": self.porta,
            "usuario": self.usuario, "senha": self.senha or "(vazia)", "detalhe": self.detalhe,
        }


def checar_ftp(ip: str, porta: int = 21, timeout: float = 4.0) -> list[Achado]:
    import ftplib
    achados = []
    for user, pwd in FTP_ANON + CREDS_PADRAO:
        ftp = ftplib.FTP()
        try:
            ftp.connect(ip, porta, timeout=timeout)
            ftp.login(user, pwd)
            achados.append(Achado("ftp", porta, user, pwd, "login FTP aceito"))
            ftp.quit()
            break
        except ftplib.error_perm:
            pass  # credencial recusada — tenta a proxima
        except (OSError, EOFError, socket.timeout):
            break  # nao conecta — encerra
        finally:
            try:
                ftp.close()
            except Exception:  # noqa: BLE001
                pass
    return achados


def checar_ssh(ip: str, porta: int = 22, timeout: float = 4.0) -> list[Achado]:
    try:
        import paramiko
    except ImportError:
        logger.warning("paramiko ausente — checagem SSH pulada")
        return []

    achados = []
    for user, pwd in CREDS_PADRAO:
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            cli.connect(
                ip, port=porta, username=user, password=pwd, timeout=timeout,
                allow_agent=False, look_for_keys=False, banner_timeout=timeout, auth_timeout=timeout,
            )
            achados.append(Achado("ssh", porta, user, pwd, "login SSH aceito"))
            break
        except paramiko.AuthenticationException:
            pass
        except Exception:  # noqa: BLE001 (rede/timeout/protocolo) — encerra
            break
        finally:
            try:
                cli.close()
            except Exception:  # noqa: BLE001
                pass
    return achados


def checar_http_basic(ip: str, porta: int, timeout: float = 4.0, https: bool = False) -> list[Achado]:
    import httpx
    esquema = "https" if https else "http"
    url = f"{esquema}://{ip}:{porta}/"
    try:
        r = httpx.get(url, timeout=timeout, verify=False)
    except Exception:  # noqa: BLE001
        return []
    if r.status_code != 401:
        return []  # nao usa HTTP Basic Auth

    achados = []
    for user, pwd in CREDS_PADRAO:
        try:
            r = httpx.get(url, timeout=timeout, verify=False, auth=(user, pwd))
        except Exception:  # noqa: BLE001
            break
        if r.status_code not in (401, 403):
            achados.append(Achado("http-basic", porta, user, pwd, f"acesso liberado (HTTP {r.status_code})"))
            break
    return achados


def checar_credenciais(ip: str, portas_abertas: list[dict], *, timeout: float = 4.0) -> list[Achado]:
    """Roda as checagens ativas relevantes para as portas abertas do alvo."""
    abertas = {p["porta"] for p in portas_abertas}
    achados: list[Achado] = []
    if 21 in abertas:
        achados += checar_ftp(ip, 21, timeout)
    if 22 in abertas:
        achados += checar_ssh(ip, 22, timeout)
    for hp in (80, 8080, 8000, 8081, 8888):
        if hp in abertas:
            achados += checar_http_basic(ip, hp, timeout, https=False)
    for hp in (443, 8443):
        if hp in abertas:
            achados += checar_http_basic(ip, hp, timeout, https=True)
    logger.info("checagem ativa ip=%s -> %d credenciais default encontradas", ip, len(achados))
    return achados
