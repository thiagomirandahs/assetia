# Roadmap do AssetIA

## v0.1 — MVP (atual)

> Objetivo: validar a tese de que descoberta automática + agente IA é útil.

- [x] Estrutura do projeto (FastAPI + React + Vite)
- [x] Modelos de dados (Tenant, User, Device, Scan, ChatMessage)
- [x] Auth JWT + bcrypt
- [x] Scanner ICMP (ping sweep paralelo)
- [x] Scanner ARP (descoberta de MAC)
- [x] OUI lookup (fabricante via MAC)
- [x] CRUD de devices (listar, filtrar, buscar)
- [x] Endpoint de scan (POST /api/scans/start)
- [x] Agente LLM com tool use (Claude)
- [x] Tools básicas: `buscar_dispositivos`, `contar_por_fabricante`, `dispositivos_novos`
- [x] Frontend: Dashboard (lista) + Chat
- [x] Multi-tenant (filtragem automática por tenant_id)
- [x] Seed de dados de demonstração
- [x] Docker Compose (api + Postgres + frontend)

## v0.2 — Enriquecimento

> Objetivo: trazer dados de melhor qualidade para o agente raciocinar.

- [ ] **SNMP completo** — coleta de uptime, modelo, firmware de switches/roteadores
- [ ] **OS fingerprint** — detecção de Windows/Linux/macOS/IoT via TTL e portas
- [ ] **Histórico de mudanças** — audit log do que mudou em cada device (IP novo, OS atualizado, etc.)
- [ ] **Alertas** — regras configuráveis ("avise quando um device novo aparecer na VLAN 10")
  - [ ] Canais: e-mail (SMTP), Telegram, webhook
- [ ] **Tags / categorização** — agrupar devices por função (servidor, estação, IoT, impressora)
- [ ] **Mais tools** para o agente:
  - [ ] `historico_de_um_dispositivo`
  - [ ] `dispositivos_em_uma_vlan`
  - [ ] `dispositivos_offline_mais_de_X_dias`
- [ ] **Streaming SSE** das respostas do agente no frontend

## v0.3 — Agentes coletores

> Objetivo: monitorar múltiplas redes (filiais) a partir de um único painel.

- [ ] **Coletor remoto** — binário Python que roda em cada filial e envia dados para a API central via HTTPS
- [ ] **Autenticação de coletor** (token de longa duração, escopo restrito)
- [ ] **Fila de scans** — workers consomem trabalhos de uma fila (Redis ou RabbitMQ)
- [ ] **Topologia de rede** — relacionamento entre switches e devices conectados (descoberta CDP/LLDP)
- [ ] **Integração AD / Entra ID** — correlacionar device → usuário logado

## v0.4 — Segurança ativa

> Objetivo: virar a chave de "inventário" para "monitor de segurança".

- [ ] **Correlação CVE** — para cada OS detectado, listar vulnerabilidades públicas relevantes
- [ ] **Detecção de MAC spoofing** — mesmo MAC em VLANs diferentes
- [ ] **Detecção de novos dispositivos** — alerta automático quando aparece algo novo na rede
- [ ] **Score de risco** — atribuir risco baixo/médio/alto a cada device baseado em OS, idade do firmware, etc.
- [ ] **Integração SIEM** — exportar eventos para Wazuh, Graylog, Splunk via syslog

## v1.0 — Produção

> Objetivo: SaaS comercial.

- [ ] **Bilhetagem multi-tenant** (Stripe — planos por número de devices)
- [ ] **Onboarding self-service** — empresa se cadastra, baixa o coletor, configura em 5 min
- [ ] **Dashboard administrativo** (super-admin) para visão geral de tenants
- [ ] **Backup automatizado** + restore testado
- [ ] **Documentação OpenAPI** publicada e versionada
- [ ] **Testes** — unit (pytest) + e2e (Playwright)
- [ ] **CI/CD** com GitHub Actions
- [ ] **Observabilidade** — Prometheus + Grafana + Loki

## v2.0 — Futuro

- [ ] **Agente proativo** — o LLM analisa proativamente o ambiente e gera relatórios semanais ("notei que 5 servidores estão sem reboot há mais de 200 dias, considere reiniciar...")
- [ ] **Integração com helpdesk** — abrir ticket automaticamente quando detectar problema
- [ ] **Mobile app** — gestor recebe push de alertas críticos
- [ ] **Plugins de scanner** — comunidade pode contribuir com novos coletores
