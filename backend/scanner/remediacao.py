"""Hardening / Remediation Engine: para cada achado, COMO CORRIGIR (comandos reais por SO).

Complementa o modo educativo (edu.py): o edu explica o risco; aqui mostramos o passo-a-passo
de correção. Depois o usuario clica em "testar novamente" e o proprio scanner revalida (diff).
USO em alvos autorizados.
"""

# Cada tema: ataques possiveis + blocos de correcao (rotulo -> lista de passos/comandos).
CORRECOES: dict[str, dict] = {
    "ssh": {
        "ataques": ["Brute force de senha", "Credential stuffing"],
        "correcao": {
            "Ubuntu/Debian (/etc/ssh/sshd_config)": [
                "PermitRootLogin no",
                "PasswordAuthentication no",
                "sudo systemctl restart ssh",
            ],
            "Recomendado": [
                "Use chaves SSH (ssh-keygen) em vez de senha",
                "Instale fail2ban contra brute force",
                "Restrinja a origem por firewall (só IPs/VPN confiáveis)",
            ],
        },
    },
    "telnet": {
        "ataques": ["Sniffing de credenciais (texto claro)", "Sequestro de sessão"],
        "correcao": {
            "Desative o Telnet": [
                "sudo systemctl disable --now telnet.socket inetd 2>/dev/null",
                "# Windows: Dism /online /Disable-Feature /FeatureName:TelnetClient",
            ],
            "Use SSH no lugar": ["sudo apt install openssh-server", "sudo systemctl enable --now ssh"],
        },
    },
    "ftp": {
        "ataques": ["Login anônimo", "Credenciais em texto claro", "CVE da versão (vsftpd 2.3.4)"],
        "correcao": {
            "vsftpd (/etc/vsftpd.conf)": ["anonymous_enable=NO", "ssl_enable=YES", "sudo systemctl restart vsftpd"],
            "Recomendado": ["Prefira SFTP (via SSH) ou FTPS", "Atualize o servidor FTP"],
        },
    },
    "smb": {
        "ataques": ["EternalBlue (MS17-010)", "Ransomware", "Relay/captura de hash"],
        "correcao": {
            "Windows (PowerShell admin)": [
                "Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force",
                "Set-SmbServerConfiguration -RequireSecuritySignature $true -Force",
                "# Bloqueie 445/139 de redes não confiáveis no firewall",
            ],
            "Recomendado": ["Aplique os patches do Windows (MS17-010)", "Nunca exponha SMB à internet"],
        },
    },
    "rdp": {
        "ataques": ["Brute force", "BlueKeep (CVE-2019-0708)"],
        "correcao": {
            "Windows": [
                "# Exija NLA (Network Level Authentication):",
                'Set-ItemProperty "HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp" UserAuthentication 1',
                "# Habilite MFA e troque a porta padrão",
            ],
            "Recomendado": ["Nunca exponha RDP direto à internet — use VPN", "Aplique patches (BlueKeep)"],
        },
    },
    "redis": {
        "ataques": ["Acesso sem autenticação", "RCE via módulo/cron"],
        "correcao": {
            "redis.conf": ["requirepass SUA_SENHA_FORTE", 'bind 127.0.0.1 ::1', "protected-mode yes", "sudo systemctl restart redis"],
            "Recomendado": ["Nunca exponha 6379 à rede/internet", "Firewall só para o app que usa"],
        },
    },
    "mongodb": {
        "ataques": ["Leitura/escrita total sem auth"],
        "correcao": {
            "mongod.conf": ["security:\n  authorization: enabled", "net:\n  bindIp: 127.0.0.1", "sudo systemctl restart mongod"],
            "Recomendado": ["Crie usuários com roles mínimas", "Nunca exponha 27017"],
        },
    },
    "snmp": {
        "ataques": ["Community padrão 'public' vaza configuração"],
        "correcao": {
            "Recomendado": [
                "Troque a community 'public' por uma forte",
                "Migre para SNMPv3 (autenticado + cifrado)",
                "Restrinja por ACL quem pode consultar",
            ],
        },
    },
    "vnc": {
        "ataques": ["Acesso sem senha", "Tráfego sem criptografia"],
        "correcao": {
            "Recomendado": ["Defina senha forte no VNC", "Use VNC sobre túnel SSH/VPN", "Nunca exponha 5900 à internet"],
        },
    },
    "db-exposto": {
        "ataques": ["Brute force de credenciais", "Acesso direto aos dados"],
        "correcao": {
            "MySQL/Postgres": [
                "# bind só local/rede interna:",
                "MySQL: bind-address = 127.0.0.1   (my.cnf)",
                "Postgres: listen_addresses = 'localhost'   (postgresql.conf)",
            ],
            "Recomendado": ["O banco só deve ser acessível pelo app", "Senha forte + firewall"],
        },
    },
    "missing-headers": {
        "ataques": ["XSS (sem CSP)", "Clickjacking (sem X-Frame-Options)", "Downgrade (sem HSTS)"],
        "correcao": {
            "Nginx": [
                'add_header Strict-Transport-Security "max-age=31536000" always;',
                'add_header X-Frame-Options "SAMEORIGIN" always;',
                'add_header X-Content-Type-Options "nosniff" always;',
                'add_header Content-Security-Policy "default-src \'self\'" always;',
            ],
            "Recomendado": ["Teste em securityheaders.com após aplicar"],
        },
    },
    "weak-tls": {
        "ataques": ["MITM / downgrade", "Quebra de cifra fraca"],
        "correcao": {
            "Nginx": ["ssl_protocols TLSv1.2 TLSv1.3;", "ssl_ciphers HIGH:!aNULL:!MD5;", "# certificado válido (Let's Encrypt / certbot)"],
            "Recomendado": ["Desative TLS 1.0/1.1 e SSLv3", "Renove certificado expirado/auto-assinado"],
        },
    },
    "default-creds": {
        "ataques": ["Acesso total com senha de fábrica"],
        "correcao": {
            "Recomendado": ["Troque TODA senha padrão no primeiro uso", "Use senhas únicas e fortes (gerenciador)", "Habilite MFA onde der"],
        },
    },
    "docker-api": {
        "ataques": ["RCE: executar container como root no host"],
        "correcao": {
            "Recomendado": ["Nunca exponha a API Docker (2375) sem TLS", "Use TLS mútuo (2376) ou só socket local", "Firewall a porta"],
        },
    },
}


def corrigir(tema: str) -> dict | None:
    """Retorna {ataques, correcao} para um tema/serviço, ou None."""
    from .edu import _ALIASES  # reaproveita os apelidos de serviço->tema

    t = (tema or "").strip().lower()
    if t in CORRECOES:
        return {"tema": t, **CORRECOES[t]}
    alvo = _ALIASES.get(t)
    if alvo and alvo in CORRECOES:
        return {"tema": alvo, **CORRECOES[alvo]}
    return None
