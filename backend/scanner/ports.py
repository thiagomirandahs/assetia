"""Scanner de portas TCP (connect scan) + identificacao de servico/banner + flag de risco.

Connect scan = handshake TCP completo. Nao exige privilegio/raw socket e e multiplataforma.

USO AUTORIZADO: escaneie apenas alvos que voce possui ou tem autorizacao para testar
(seus labs, redes que voce administra, ambientes de CTF).
"""
import asyncio
from dataclasses import dataclass

# Mapa porta -> servico (tambem define quais portas o scanner cobre).
SERVICOS = {
    7: "echo", 9: "discard", 13: "daytime", 19: "chargen", 21: "ftp", 22: "ssh",
    23: "telnet", 25: "smtp", 37: "time", 43: "whois", 53: "dns", 79: "finger",
    80: "http", 88: "kerberos", 110: "pop3", 111: "rpcbind", 113: "ident",
    119: "nntp", 123: "ntp", 135: "msrpc", 137: "netbios-ns", 139: "netbios-ssn",
    143: "imap", 161: "snmp", 179: "bgp", 389: "ldap", 427: "slp", 443: "https",
    445: "smb", 465: "smtps", 500: "ike", 502: "modbus", 512: "exec", 513: "login",
    514: "syslog", 515: "printer", 520: "rip", 523: "db2", 540: "uucp", 548: "afp",
    554: "rtsp", 587: "smtp-sub", 623: "ipmi", 631: "ipp", 636: "ldaps",
    873: "rsync", 902: "vmware", 989: "ftps", 990: "ftps", 993: "imaps",
    995: "pop3s", 1025: "msrpc", 1080: "socks", 1099: "java-rmi", 1194: "openvpn",
    1433: "mssql", 1521: "oracle", 1604: "citrix", 1723: "pptp", 1883: "mqtt",
    1900: "upnp", 2049: "nfs", 2082: "cpanel", 2083: "cpanel-ssl", 2121: "ftp-alt",
    2181: "zookeeper", 2222: "ssh-alt", 2375: "docker-api", 2376: "docker-tls",
    2483: "oracle", 3000: "http-alt", 3128: "squid-proxy", 3268: "globalcat",
    3306: "mysql", 3389: "rdp", 3690: "svn", 4444: "metasploit", 4786: "cisco-smi",
    4848: "glassfish", 5000: "http-alt", 5060: "sip", 5222: "xmpp", 5353: "mdns",
    5432: "postgres", 5555: "adb", 5601: "kibana", 5666: "nrpe", 5672: "amqp",
    5800: "vnc-http", 5900: "vnc", 5938: "teamviewer", 5984: "couchdb",
    5985: "winrm", 5986: "winrm-ssl", 6000: "x11", 6379: "redis", 6443: "kube-api",
    6660: "irc", 7001: "weblogic", 7070: "realserver", 7474: "neo4j",
    7547: "cwmp", 8000: "http-alt", 8008: "http-alt", 8009: "ajp", 8010: "http-alt",
    8080: "http-proxy", 8081: "http-alt", 8086: "influxdb", 8088: "http-alt",
    8089: "splunk", 8090: "http-alt", 8161: "activemq", 8181: "http-alt",
    8333: "bitcoin", 8443: "https-alt", 8500: "consul", 8530: "wsus",
    8686: "jmx", 8888: "http-alt", 9000: "http-alt", 9042: "cassandra",
    9092: "kafka", 9100: "printer-raw", 9200: "elasticsearch", 9300: "elasticsearch",
    9418: "git", 9600: "logstash", 9999: "http-alt", 10000: "webmin",
    11211: "memcached", 15672: "rabbitmq-mgmt", 27017: "mongodb", 27018: "mongodb",
    28017: "mongodb-web", 50000: "sap", 50070: "hadoop",
}

# Portas que o scanner cobre (todas do mapa acima).
PORTAS_COMUNS = sorted(SERVICOS.keys())

# Serviços que, EXPOSTOS, representam risco. (descricao, severidade)
RISCO = {
    23: ("Telnet em texto claro — credenciais trafegam sem criptografia", "critical"),
    21: ("FTP pode permitir login anônimo e trafega credenciais em claro", "warning"),
    445: ("SMB exposto — superfície clássica de ransomware/EternalBlue", "critical"),
    139: ("NetBIOS/SMB legado exposto à rede", "warning"),
    135: ("MSRPC exposto — usado em movimentação lateral no Windows", "warning"),
    3389: ("RDP exposto — alvo nº1 de brute force e ransomware", "critical"),
    5900: ("VNC frequentemente sem senha ou sem criptografia", "critical"),
    6379: ("Redis normalmente sobe SEM autenticação", "critical"),
    11211: ("Memcached sem auth — vazamento de dados e amplificação DDoS", "warning"),
    27017: ("MongoDB historicamente exposto sem autenticação", "critical"),
    9200: ("Elasticsearch sem auth expõe todos os índices", "critical"),
    3306: ("Banco MySQL exposto diretamente à rede", "warning"),
    5432: ("Banco PostgreSQL exposto diretamente à rede", "warning"),
    1433: ("Banco MSSQL exposto diretamente à rede", "warning"),
    1521: ("Banco Oracle exposto diretamente à rede", "warning"),
    2375: ("Docker API sem TLS = execução remota de código trivial", "critical"),
    161: ("SNMP pode vazar informação com community pública (public)", "warning"),
    2049: ("NFS exportando sistemas de arquivos pela rede", "warning"),
    5985: ("WinRM exposto — execução remota se credenciais vazarem", "warning"),
    5555: ("ADB (Android Debug Bridge) exposto — controle total do dispositivo sem senha", "critical"),
    623: ("IPMI/BMC exposto — histórico de bypass de autenticação (Supermicro/HP)", "critical"),
    6443: ("API do Kubernetes exposta — controle do cluster se sem RBAC/auth", "critical"),
    502: ("Modbus (ICS/SCADA) exposto — controle de equipamento industrial sem auth", "critical"),
    1883: ("MQTT frequentemente sem autenticação — vazamento/controle de IoT", "warning"),
    8009: ("AJP (Tomcat) exposto — 'Ghostcat' (CVE-2020-1938), leitura de arquivos/RCE", "warning"),
    9100: ("Impressora (RAW/JetDirect) exposta — abuso/extração de documentos", "warning"),
    4444: ("Porta padrão de Metasploit/shell reverso — investigar se é legítimo", "warning"),
    512: ("rexec — execução remota legada sem criptografia", "warning"),
    513: ("rlogin — login remoto legado sem criptografia", "warning"),
}

_PORTAS_HTTP = {80, 3000, 8000, 8001, 8080, 8081, 8888, 9000, 5601, 9200}


@dataclass
class PortaAberta:
    porta: int
    servico: str
    banner: str | None
    risco: str | None       # descrição do risco (None = sem risco conhecido)
    severidade: str | None  # info | warning | critical


async def _grab_banner(ip: str, porta: int, reader, writer, timeout: float) -> str | None:
    """Tenta capturar um banner. HTTP recebe um HEAD; serviços como ssh/ftp/smtp
    mandam o banner sozinhos ao conectar."""
    try:
        if porta in _PORTAS_HTTP:
            writer.write(b"HEAD / HTTP/1.0\r\nHost: " + ip.encode() + b"\r\n\r\n")
            await writer.drain()
        data = await asyncio.wait_for(reader.read(512), timeout=min(timeout, 2.0))
        if not data:
            return None
        txt = data.decode("latin-1", "ignore")
        if "HTTP/" in txt:
            for ln in txt.splitlines():
                if ln.lower().startswith("server:"):
                    return ln.strip()
            return txt.splitlines()[0].strip()[:120] or None
        primeira = next((l.strip() for l in txt.splitlines() if l.strip()), "")
        return primeira[:120] or None
    except Exception:  # noqa: BLE001
        return None


async def _abrir_conexao(ip: str, porta: int, timeout: float):
    """Abre conexao TCP — direta ou via proxy SOCKS5 (Tor) se configurado."""
    from .proxy import proxy_atual

    url = proxy_atual()
    if url:
        from python_socks.async_.asyncio import Proxy
        proxy = Proxy.from_url(url)
        sock = await asyncio.wait_for(
            proxy.connect(dest_host=ip, dest_port=porta, timeout=timeout), timeout=timeout
        )
        return await asyncio.open_connection(sock=sock)
    return await asyncio.wait_for(asyncio.open_connection(ip, porta), timeout=timeout)


async def _checar_porta(ip: str, porta: int, timeout: float) -> PortaAberta | None:
    try:
        reader, writer = await _abrir_conexao(ip, porta, timeout)
    except Exception:  # noqa: BLE001 — fechada/filtrada/proxy-fail => nao aberta
        return None

    banner = await _grab_banner(ip, porta, reader, writer, timeout)
    try:
        writer.close()
        await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
    except Exception:  # noqa: BLE001
        pass

    risco, sev = RISCO.get(porta, (None, None))
    return PortaAberta(
        porta=porta,
        servico=SERVICOS.get(porta, "desconhecido"),
        banner=banner,
        risco=risco,
        severidade=sev,
    )


async def scan_portas(
    ip: str, *, portas: list[int] | None = None, timeout: float = 1.5, max_paralelo: int = 200
) -> list[PortaAberta]:
    """Connect scan em um host. Retorna só as portas abertas, ordenadas."""
    portas = portas or PORTAS_COMUNS
    sem = asyncio.Semaphore(max_paralelo)

    async def _wrap(p: int):
        async with sem:
            return await _checar_porta(ip, p, timeout)

    resultados = await asyncio.gather(*[_wrap(p) for p in portas])
    return sorted([r for r in resultados if r is not None], key=lambda r: r.porta)


def scan_portas_sync(ip: str, **kwargs) -> list[PortaAberta]:
    """Wrapper síncrono (para usar fora de contexto async)."""
    return asyncio.run(scan_portas(ip, **kwargs))
