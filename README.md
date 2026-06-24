<h1 align="center">
  AssetIA
</h1>

<p align="center">
  <strong>Inventário inteligente de TI com agente LLM.</strong><br/>
  Descobre dispositivos na rede, cataloga automaticamente e responde a perguntas em linguagem natural.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Claude%20API-Anthropic-D97757?style=flat" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat" />
</p>

---

## 🎯 O problema

Em qualquer empresa com mais de 30 máquinas, a TI perde tempo respondendo perguntas que **deveriam ser triviais**:

- "Quais notebooks Dell ainda estão com Windows 10?"
- "Apareceu alguma máquina nova na rede hoje?"
- "Quantos switches MikroTik estão online agora?"
- "Existe algum dispositivo desconhecido na VLAN de visitantes?"

Hoje, isso exige cruzar planilhas, abrir Winbox, rodar `nmap` manualmente e juntar tudo na cabeça. **AssetIA resolve isso em uma frase.**

---

## ✨ O que o AssetIA faz

### 🔍 1. Descoberta automática
Scanner que varre a rede e cataloga **tudo** que estiver online:

- **Ping sweep** (ICMP) para descoberta de hosts
- **ARP scan** para MAC addresses
- **SNMP** para informações detalhadas de switches, roteadores e impressoras
- **Fingerprint de OS** via TTL e portas abertas
- **Detecção de fabricante** via OUI do MAC

### 🧠 2. Agente de IA com Claude
Um chat embutido onde você pergunta em **português** e o agente busca os dados do banco em tempo real (via [tool use da API Claude](https://docs.anthropic.com/claude/docs/tool-use)):

```
Você: quais máquinas apareceram na rede nos últimos 7 dias?
🤖:    encontrei 3 dispositivos novos:
       • 192.168.10.45 (HP LaserJet M404) — descoberto há 2 dias
       • 192.168.10.78 (Apple, MacBook) — descoberto há 5 dias
       • 192.168.20.12 (desconhecido, MAC 00:1B:21:..) — descoberto hoje ⚠️
```

### 🛡️ 3. Alertas de segurança
Detecta automaticamente:

- **Dispositivos desconhecidos** que aparecem na rede
- **MAC spoofing** (mesmo MAC em VLANs diferentes)
- **OS desatualizado** (correlação com base CVE)
- **Tráfego anômalo** (em roadmap)

### 📊 4. Dashboard multi-tenant
Cada cliente vê apenas seus próprios dispositivos. JWT + RBAC.

---

## 🏗️ Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser   │────▶│  React/Vite  │────▶│   FastAPI    │
│  (Chat UI)  │     │   (Tailwind) │     │   (Python)   │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                            ┌────────────────────┼────────────────────┐
                            ▼                    ▼                    ▼
                    ┌───────────────┐   ┌────────────────┐   ┌──────────────┐
                    │  Scanner core │   │  Agent (LLM)   │   │   Database   │
                    │ (scapy, snmp) │   │ (Claude tools) │   │   (SQLite)   │
                    └───────┬───────┘   └────────────────┘   └──────────────┘
                            │                    ▲
                            ▼                    │
                    ┌───────────────┐            │
                    │  Rede LAN     │            │
                    │  (descoberta) │            │
                    └───────────────┘            │
                                                 │
                              ┌──────────────────┘
                              ▼
                    ┌─────────────────────┐
                    │  Anthropic Claude   │
                    │     API (cloud)     │
                    └─────────────────────┘
```

Detalhe em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 🛠️ Stack

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| **Scanner** | scapy (ICMP/ARP), pysnmp (SNMP), manuf (OUI), psutil |
| **IA / LLM** | Anthropic Claude API com **tool use** |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS |
| **Banco** | SQLite (dev) / PostgreSQL (prod) |
| **Auth** | JWT + bcrypt (multi-tenant via `tenant_id`) |
| **Deploy** | Docker Compose, nginx reverse proxy |

---

## 🚀 Como rodar (dev)

### Pré-requisitos
- Python 3.11+
- Node 20+
- Uma chave da API Anthropic (gere em https://console.anthropic.com)

### Backend

```bash
# 1. Clone e entre na pasta
git clone https://github.com/thiagomirandahs/assetia.git
cd assetia

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env e coloque sua ANTHROPIC_API_KEY

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Seede dados de demonstração (10 dispositivos fictícios)
python scripts/seed_demo_data.py

# 5. Suba o servidor
uvicorn backend.main:app --reload --port 8000
```

API disponível em `http://localhost:8000` · Docs em `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Interface em `http://localhost:5173`.

### Docker (tudo de uma vez)

```bash
docker compose up --build
```

---

## 💻 Modo CLI (sem frontend)

Pra testar o agente de IA direto no terminal:

```bash
python scripts/chat_cli.py
```

```
Você> quantos dispositivos com Linux estão online?
🤖    8 dispositivos com Linux estão online. Os 3 mais recentes são:
      • srv-app-01 (192.168.10.5, Ubuntu, online há 14 dias)
      • srv-db-02 (192.168.10.7, Debian, online há 9 dias)
      • dev-laptop-thiago (192.168.20.45, Ubuntu, online há 2 dias)
```

Pra rodar uma varredura manual:

```bash
python scripts/run_scan.py 192.168.0.0/24
```

---

## 🗺️ Roadmap

Veja [`docs/ROADMAP.md`](docs/ROADMAP.md) para o plano completo.

**v0.1 (MVP — atual):**
- [x] Scanner ICMP + ARP
- [x] CRUD de devices com FastAPI
- [x] Agente Claude com tool use
- [x] Frontend básico (Dashboard + Chat)
- [x] Multi-tenant + JWT

**v0.2 (próximo):**
- [ ] SNMP completo (switches/roteadores)
- [ ] Detecção de fingerprint de OS
- [ ] Histórico de mudanças (audit log)
- [ ] Alertas por e-mail/Telegram

**v0.3:**
- [ ] Agentes coletores remotos (para múltiplas redes)
- [ ] Integração com Active Directory / Entra ID
- [ ] Correlação com CVE / detecção de OS vulneráveis
- [ ] Métricas em tempo real (uso de banda, latência)

**v1.0:**
- [ ] Deploy em produção (Docker + nginx + Postgres)
- [ ] Bilhetagem multi-tenant (Stripe)
- [ ] Documentação completa da API
- [ ] Testes e2e

---

## 🤝 Contribuindo

Pull requests são bem-vindos! Para mudanças grandes, abra uma issue antes para discutirmos.

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE).

---

## 👤 Autor

**Thiago Henrique da Silva Miranda**
Analista de TI · Desenvolvedor Full-Stack · MBA em Segurança da Informação

[LinkedIn](https://www.linkedin.com/in/thiago-henrique-da-silva-miranda-389885279) · [GitHub](https://github.com/thiagomirandahs) · thiago.mirandahs@gmail.com
