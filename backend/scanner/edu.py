"""Modo educativo: explica cada achado em termos de pentest (para aprender).

Cada tema traz: o que é, por que é risco, como costuma ser explorado (conceitual, para
DEFESA e estudo), como mitigar, e onde aprender mais. Foco didático para quem está
começando em hacking ético / pentest AUTORIZADO.
"""

EXPLICACOES: dict[str, dict] = {
    "port-scan": {
        "titulo": "Varredura de portas",
        "o_que_e": "Descobrir quais portas TCP estão abertas num host = quais serviços ele expõe.",
        "risco": "Cada porta aberta é uma 'porta de entrada' potencial. Mapear isso é o passo 1 de qualquer pentest.",
        "como_explora": "O atacante escaneia (nmap), identifica serviços/versões e busca exploits para cada um.",
        "mitigacao": "Feche o que não usa, restrinja por firewall, exponha o mínimo necessário.",
        "aprender_mais": "Nmap (nmap.org/book) e a sala 'Nmap' do TryHackMe.",
    },
    "smb": {
        "titulo": "SMB (445/139)",
        "o_que_e": "Compartilhamento de arquivos/impressoras do Windows.",
        "risco": "Exposto, é alvo clássico de ransomware e do EternalBlue (MS17-010).",
        "como_explora": "Exploits públicos (EternalBlue) ou credenciais fracas → RCE/leitura de arquivos. Em lab: metasploit ms17_010, nmap --script smb-vuln*.",
        "mitigacao": "Bloqueie 445/139 na borda, desative SMBv1, aplique patches, exija autenticação forte.",
        "aprender_mais": "TryHackMe 'Blue' (EternalBlue na prática).",
    },
    "rdp": {
        "titulo": "RDP (3389)",
        "o_que_e": "Área de trabalho remota do Windows.",
        "risco": "Exposto à internet é alvo nº1 de brute force e ransomware; CVE BlueKeep (RCE pré-auth) em versões antigas.",
        "como_explora": "Brute force de credenciais, ou exploit BlueKeep em sistemas sem patch.",
        "mitigacao": "Nunca exponha RDP direto; use VPN, NLA, MFA, e patches. Restrinja IPs de origem.",
        "aprender_mais": "Pesquise 'BlueKeep CVE-2019-0708' e MFA para RDP.",
    },
    "telnet": {
        "titulo": "Telnet (23)",
        "o_que_e": "Acesso remoto a linha de comando — antigo e SEM criptografia.",
        "risco": "Login e dados trafegam em texto claro: qualquer um na rede captura a senha (sniffing).",
        "como_explora": "Wireshark/tcpdump capturam as credenciais direto do tráfego.",
        "mitigacao": "Desative o Telnet e use SSH no lugar.",
        "aprender_mais": "Compare Telnet vs SSH; pratique sniffing com Wireshark (na sua rede).",
    },
    "ftp": {
        "titulo": "FTP (21)",
        "o_que_e": "Transferência de arquivos — geralmente sem criptografia.",
        "risco": "Login anônimo, credenciais em texto claro, e versões com backdoor (vsftpd 2.3.4).",
        "como_explora": "Tenta login anônimo/padrão; captura credenciais; explora CVEs da versão.",
        "mitigacao": "Use SFTP/FTPS, desative login anônimo, troque credenciais padrão.",
        "aprender_mais": "TryHackMe salas de enumeração de serviços.",
    },
    "ssh": {
        "titulo": "SSH (22)",
        "o_que_e": "Acesso remoto seguro (criptografado) — o jeito certo de administrar.",
        "risco": "Em si é seguro, mas sofre brute force de senha e versões antigas têm CVEs (ex: enum de usuários).",
        "como_explora": "Brute force (hydra) com credenciais fracas; enumeração de usuários em versões antigas.",
        "mitigacao": "Use chaves (não senha), desative login de root, fail2ban, mantenha atualizado.",
        "aprender_mais": "Autenticação por chave SSH e hardening do sshd.",
    },
    "redis": {
        "titulo": "Redis (6379)",
        "o_que_e": "Banco de dados em memória, super rápido.",
        "risco": "Por padrão sobe SEM autenticação — quem alcança a porta lê/escreve tudo e pode ganhar RCE.",
        "como_explora": "Conecta sem senha, escreve em cron/chave SSH autorizada → execução de comando.",
        "mitigacao": "Exija senha (requirepass), bind em 127.0.0.1, firewall, modo protegido.",
        "aprender_mais": "Pesquise 'Redis unauthenticated RCE'.",
    },
    "mongodb": {
        "titulo": "MongoDB (27017)",
        "o_que_e": "Banco NoSQL de documentos.",
        "risco": "Historicamente exposto sem autenticação — vazamento total de dados.",
        "como_explora": "Conecta sem credenciais e despeja todas as coleções.",
        "mitigacao": "Habilite auth, bind local, firewall. Nunca exponha à internet.",
        "aprender_mais": "Casos de 'MongoDB data breach' por falta de auth.",
    },
    "elasticsearch": {
        "titulo": "Elasticsearch (9200)",
        "o_que_e": "Motor de busca/indexação de dados.",
        "risco": "Sem auth, expõe e permite alterar todos os índices (dados sensíveis).",
        "como_explora": "GET /_cat/indices e /_search sem credencial → lê tudo.",
        "mitigacao": "Ative segurança (X-Pack/auth), firewall, proxy autenticado.",
        "aprender_mais": "Documentação de segurança do Elastic.",
    },
    "snmp": {
        "titulo": "SNMP (161)",
        "o_que_e": "Protocolo de gerência de equipamentos de rede.",
        "risco": "Community string padrão ('public') vaza configuração, rotas, e às vezes senhas.",
        "como_explora": "snmpwalk com 'public' extrai um mapa do equipamento.",
        "mitigacao": "Troque a community, use SNMPv3 (autenticado/cifrado), restrinja por ACL.",
        "aprender_mais": "Pratique snmpwalk/snmp-check em lab.",
    },
    "default-creds": {
        "titulo": "Credenciais padrão",
        "o_que_e": "Usuário/senha de fábrica que nunca foram trocados (admin/admin, root/root...).",
        "risco": "É a forma mais fácil de invadir — acesso total sem esforço.",
        "como_explora": "Testa a lista de defaults conhecidos do fabricante/serviço.",
        "mitigacao": "Troque TODA senha padrão no primeiro uso; use um gerenciador de senhas.",
        "aprender_mais": "Sites de 'default password' (ex: datarecovery default password list).",
    },
    "missing-headers": {
        "titulo": "Headers de segurança ausentes",
        "o_que_e": "Cabeçalhos HTTP que o navegador usa para proteger o usuário (CSP, HSTS, X-Frame-Options).",
        "risco": "Sem eles, o site fica mais exposto a XSS, clickjacking e downgrade de HTTPS.",
        "como_explora": "Sem CSP → XSS é mais fácil; sem X-Frame-Options → clickjacking via iframe.",
        "mitigacao": "Configure os headers no servidor/app (CSP, HSTS, X-Frame-Options, nosniff).",
        "aprender_mais": "PortSwigger Web Security Academy (XSS, clickjacking) e securityheaders.com.",
    },
    "weak-tls": {
        "titulo": "TLS fraco / certificado ruim",
        "o_que_e": "Protocolo antigo (TLS 1.0/1.1), cipher fraco, cert expirado ou auto-assinado.",
        "risco": "Permite interceptação/MITM e quebra a confiança da conexão.",
        "como_explora": "Downgrade para protocolo fraco e ataque ao canal cifrado.",
        "mitigacao": "Force TLS 1.2+/1.3, ciphers fortes, cert válido (Let's Encrypt).",
        "aprender_mais": "ssllabs.com/ssltest e testssl.sh.",
    },
    "exposed-git": {
        "titulo": "Repositório .git exposto",
        "o_que_e": "A pasta .git acessível pela web no servidor.",
        "risco": "Baixar o .git revela TODO o código-fonte — e às vezes segredos/credenciais no histórico.",
        "como_explora": "Ferramentas como git-dumper baixam o repositório inteiro do site.",
        "mitigacao": "Nunca publique .git; bloqueie no servidor; remova segredos do histórico.",
        "aprender_mais": "Pesquise 'git-dumper' e 'secrets in git history'.",
    },
    "arp-spoofing": {
        "titulo": "ARP spoofing / MITM",
        "o_que_e": "Um device mente no ARP dizendo ser o gateway, e o tráfego passa por ele.",
        "risco": "Permite interceptar/alterar o tráfego de toda a rede (man-in-the-middle).",
        "como_explora": "Ferramentas (ettercap, bettercap) envenenam o ARP e capturam dados.",
        "mitigacao": "ARP estático/Dynamic ARP Inspection no switch, segmentação, monitorar ARP.",
        "aprender_mais": "Pratique com bettercap em lab isolado.",
    },
    "db-exposto": {
        "titulo": "Banco de dados exposto (MySQL/Postgres/MSSQL)",
        "o_que_e": "Porta de banco (3306/5432/1433) acessível pela rede.",
        "risco": "Brute force de credenciais e, se entrar, acesso a todos os dados da aplicação.",
        "como_explora": "Brute force; credenciais reaproveitadas; injeção via app conectado.",
        "mitigacao": "Banco só acessível pelo app (bind local/rede interna), senha forte, firewall.",
        "aprender_mais": "Salas de SQL/banco no TryHackMe.",
    },
}

# aliases de serviço/finding -> tema
_ALIASES = {
    "netbios-ssn": "smb", "https": "missing-headers", "http": "missing-headers",
    "http-alt": "missing-headers", "http-proxy": "missing-headers", "mysql": "db-exposto",
    "postgres": "db-exposto", "mssql": "db-exposto", "oracle": "db-exposto",
    "smtps": "weak-tls", "imaps": "weak-tls", "vnc": "default-creds",
}


def explicar(tema: str) -> dict | None:
    """Busca a explicação por tema/serviço (com aliases). None se não houver."""
    t = (tema or "").strip().lower()
    if t in EXPLICACOES:
        return {"tema": t, **EXPLICACOES[t]}
    if t in _ALIASES:
        alvo = _ALIASES[t]
        return {"tema": alvo, **EXPLICACOES[alvo]}
    return None


def temas_disponiveis() -> list[str]:
    return sorted(EXPLICACOES.keys())
