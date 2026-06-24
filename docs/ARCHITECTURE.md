# Arquitetura do AssetIA

## Visão geral

AssetIA é uma aplicação **multi-tenant** que combina três componentes principais:

1. **Scanner de rede** — código de baixo nível que descobre dispositivos via ICMP, ARP e SNMP.
2. **API REST** — interface HTTP que persiste dados, autentica usuários e expõe endpoints para o frontend e para o agente de IA.
3. **Agente LLM** — wrapper sobre a API da Anthropic que recebe perguntas em linguagem natural e usa "tool calling" para consultar o banco e responder em texto natural.

```
                    ┌──────────────────────────────┐
                    │     Cliente (Browser)        │
                    │   React + TypeScript + Vite  │
                    └──────────────┬───────────────┘
                                   │ HTTPS (JWT)
                                   ▼
              ┌─────────────────────────────────────┐
              │       API REST (FastAPI)            │
              │  ┌──────┐ ┌──────┐ ┌──────┐ ┌────┐  │
              │  │ auth │ │scans │ │devices│ │chat│  │
              │  └──────┘ └──────┘ └──────┘ └────┘  │
              └────────┬─────────┬──────────┬───────┘
                       │         │          │
            ┌──────────┘         │          └──────────────┐
            ▼                    ▼                         ▼
    ┌───────────────┐   ┌────────────────┐       ┌─────────────────┐
    │ Banco (SQLA)  │   │ Scanner core   │       │  Agente LLM     │
    │ Devices       │   │ ICMP/ARP/SNMP  │       │  Claude + tools │
    │ Scans         │   │ Fingerprinting │       └────────┬────────┘
    │ Tenants       │   └────────┬───────┘                │
    │ Users         │            │                        │
    └───────────────┘            ▼                        ▼
                         ┌───────────────┐      ┌───────────────────┐
                         │ Rede da empresa│      │ Anthropic API     │
                         │ (LAN)         │      │ (Claude Sonnet 4) │
                         └───────────────┘      └───────────────────┘
```

## Decisões de design

### 1. Multi-tenant desde o início

Toda tabela de dados tem uma coluna `tenant_id`. O JWT carrega `tenant_id` no payload, e **todo** middleware/dependency filtra automaticamente por esse valor. Isso permite que um único deploy sirva múltiplos clientes sem vazamento de dados.

### 2. Scanner desacoplado da API

O scanner roda como módulos puros (`backend/scanner/*`), sem dependência de FastAPI. Pode ser executado:
- Em-process via endpoint `POST /api/scans/start`
- Via CLI (`scripts/run_scan.py`)
- Por workers remotos (roadmap v0.3)

### 3. Agente de IA com tool use

Em vez de fazer **RAG** (que embute todo o banco em embeddings e pode ficar desatualizado), usamos **tool use** da API Claude:

```python
tools = [
    {
        "name": "buscar_dispositivos",
        "description": "Busca dispositivos no inventário com filtros opcionais",
        "input_schema": { ... }
    },
    {
        "name": "contar_dispositivos_por_fabricante",
        ...
    },
]
```

O Claude decide qual ferramenta chamar e com quais parâmetros. O backend executa a query no banco e devolve o resultado. O Claude formula a resposta final em linguagem natural.

**Vantagens** sobre RAG:
- Sempre atualizado (consulta o banco em tempo real)
- Custos previsíveis (não precisa indexar embeddings)
- Funciona com queries agregadas (`SUM`, `COUNT`, `GROUP BY`) sem hack

### 4. JWT em vez de sessão

Permite escalar horizontalmente sem precisar de Redis para sessões. Token expira em 24h e carrega `user_id`, `tenant_id`, `role`.

## Modelo de dados

```
┌────────────┐      ┌──────────┐      ┌──────────┐
│  Tenant    │ 1─┐  │  User    │ 1─┐  │  Device  │
│  id        │   ├──│ tenant_id│   ├──│ tenant_id│
│  nome      │   │  │ email    │   │  │ ip       │
│  ativo     │   │  │ senha    │   │  │ mac      │
│            │   │  │ role     │   │  │ hostname │
│            │   │  └──────────┘   │  │ vendor   │
│            │   │                 │  │ so       │
│            │   │  ┌──────────┐   │  │ online   │
│            │   │  │  Scan    │ 1─┘  │ ultima_  │
│            │   ├──│ tenant_id│      │  visao   │
│            │   │  │ rede     │      └──────────┘
│            │   │  │ inicio   │
│            │   │  │ fim      │
│            │   │  │ achados  │
└────────────┘   │  └──────────┘
                 │
                 │  ┌──────────────┐
                 │  │ ChatMessage  │
                 └──│ tenant_id    │
                    │ user_id      │
                    │ role         │ (user/assistant)
                    │ conteudo     │
                    │ tool_calls   │ (JSON)
                    └──────────────┘
```

## Segurança

- **Bcrypt** para hash de senhas
- **HMAC-SHA256** no JWT (não usar `none`!)
- **Rate limiting** nos endpoints de auth (roadmap v0.2)
- **CORS** restrito a origens conhecidas via env var
- **Scanner privilégios:** `cap_add: NET_RAW` no Docker (não roda como root)
- **Segredos via env vars** — nunca hardcoded

## Performance

- **Pings paralelos** com `asyncio` (até 64 simultâneos, configurável)
- **Connection pooling** no SQLAlchemy
- **Índices** em `(tenant_id, ip)` e `(tenant_id, mac)` na tabela Device
- **Stream de respostas** do Claude (próximo: SSE no frontend)
