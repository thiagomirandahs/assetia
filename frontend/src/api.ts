// Cliente HTTP para a API do AssetIA. JWT persistido em localStorage.

const BASE = "/api";

export function getToken(): string | null {
  return localStorage.getItem("assetia_token");
}

export function setToken(t: string | null) {
  if (t) localStorage.setItem("assetia_token", t);
  else localStorage.removeItem("assetia_token");
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const r = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(txt || `HTTP ${r.status}`);
  }
  return (await r.json()) as T;
}

// ===== tipos =====
export interface Device {
  id: number;
  ip: string;
  mac: string | null;
  hostname: string | null;
  fabricante: string | null;
  so: string | null;
  tipo: string | null;
  vlan: string | null;
  online: boolean;
  primeira_visao: string;
  ultima_visao: string;
}

export interface DeviceList {
  total: number;
  online: number;
  offline: number;
  devices: Device[];
}

export interface User {
  id: number;
  email: string;
  nome: string;
  role: string;
  tenant_id: number;
}

export interface Alert {
  id: number;
  rule_id: number;
  device_id: number | null;
  severidade: "info" | "warning" | "critical";
  titulo: string;
  mensagem: string;
  lido: boolean;
  criado_em: string;
}

export interface AlertList {
  total: number;
  nao_lidos: number;
  alerts: Alert[];
}

export interface AlertRule {
  id: number;
  nome: string;
  descricao: string | null;
  tipo: string;
  parametros: string | null;
  severidade: string;
  canais: string;
  ativa: boolean;
}

// Evento de streaming do chat (SSE)
export type ChatEvent =
  | { tipo: "token"; texto: string }
  | { tipo: "tool"; tool: string; input: Record<string, unknown> }
  | { tipo: "fim"; resposta: string; tool_calls: { tool: string }[] }
  | { tipo: "erro"; detail: string };

// ===== Pentest =====
export type Severidade = "info" | "warning" | "critical" | null;

export interface CveMatch {
  cve: string;
  descricao: string;
  severidade: Severidade;
}

export interface PortaAberta {
  porta: number;
  servico: string;
  banner: string | null;
  risco: string | null;
  severidade: Severidade;
  cves: CveMatch[];
}

export interface ScanDiff {
  primeira_vez: boolean;
  abertas_novas: { porta: number; servico: string }[];
  fechadas: { porta: number; servico: string }[];
  risco_anterior: number | null;
}

export interface ScanPortasResult {
  device_id: number;
  ip: string;
  so: string | null;
  risco_score: number;
  risco_rotulo: string;
  total: number;
  criticas: number;
  abertas: PortaAberta[];
  diff?: ScanDiff | null;
}

export interface ExposicaoCritica {
  device_id: number;
  ip: string;
  hostname: string | null;
  porta: number;
  servico: string;
  risco: string;
}

export interface HostArriscado {
  device_id: number;
  ip: string;
  hostname: string | null;
  so: string | null;
  risco_score: number;
}

export interface SuperficieAtaque {
  hosts_escaneados: number;
  portas_abertas_total: number;
  cves_encontradas: number;
  por_severidade: { critical: number; warning: number; info: number; sem_risco: number };
  top_servicos: { servico: string; quantidade: number }[];
  exposicoes_criticas: ExposicaoCritica[];
  hosts_mais_arriscados: HostArriscado[];
}

export interface DashboardData {
  risco_medio: number;
  hosts_avaliados: number;
  buckets: { critico: number; alto: number; medio: number; baixo: number };
  portas_abertas: number;
  cves: number;
  criticas: number;
  exposicoes_criticas: ExposicaoCritica[];
  hosts_mais_arriscados: HostArriscado[];
}

export interface RedeLocal {
  interface: string;
  ip_local: string;
  cidr: string;
  hosts: number;
}

export interface HostDescoberto {
  ip: string;
  mac: string | null;
  fabricante: string | null;
  latencia_ms: number | null;
  device_id?: number;
}

export interface DescobrirResult {
  cidr: string;
  total: number;
  ips: string[];
  hosts: HostDescoberto[];
}

export interface CredAchado {
  servico: string;
  porta: number;
  usuario: string;
  senha: string;
  detalhe: string;
}

export interface CredCheckResult {
  ip: string;
  device_id: number;
  total: number;
  achados: CredAchado[];
  aviso?: string;
}

export interface WebAchado {
  porta: number;
  tipo: string;
  severidade: Severidade;
  detalhe: string;
}

export interface TlsInfo {
  host: string;
  porta: number;
  protocolo?: string;
  cipher?: string;
  emissor?: string;
  assunto?: string;
  self_signed?: boolean;
  expira_em?: string;
  dias_para_expirar?: number;
  erro?: string;
  achados: { severidade: Severidade; detalhe: string }[];
}

export interface WebResult {
  ip: string;
  device_id: number;
  tem_http: boolean;
  web: WebAchado[];
  tls: TlsInfo[];
}

export interface ProxyStatus {
  configurado: boolean;
  proxy: string | null;
  exit_ip?: string;
  erro?: string;
}

export interface BaselineResult {
  so: string;
  score: number;
  rotulo: string;
  ok: number;
  conclusivos: number;
  checks: { chave: string; rotulo: string; estado: string; dica: string }[];
}

export interface AttackPathResult {
  ok: boolean;
  motivo?: string;
  entrada?: { ip: string; servico: string; porta: number; risco: number; cve: string };
  alvo?: { ip: string; servico: string; porta: number };
  passos?: { de: string; para: string; tecnica: string; detalhe: string }[];
  recomendacao?: string;
}

export interface ComplianceResult {
  percentual: number;
  conformes: number;
  avaliados: number;
  pendentes: number;
  itens: { controle: string; frameworks: string; estado: string }[];
}

export interface PatchesResult {
  total_cves: number;
  criticos: number;
  cves: { cve: string; descricao: string; severidade: string; hosts: string[] }[];
  acoes_por_servico: { servico: string; acao: string; hosts: string[] }[];
}

export interface BasResult {
  total: number;
  detectados_bloqueados: number;
  resultados: {
    id: string;
    tecnica: string;
    mitre: string;
    modifica?: string;
    executou: boolean;
    bloqueado: boolean | null;
    detalhe: string;
  }[];
  aviso: string;
}

export interface NetSample {
  upload_bps: number;
  download_bps: number;
  upload_total: number;
  download_total: number;
}

export interface Correcao {
  tema: string;
  ataques: string[];
  correcao: Record<string, string[]>;
}

export interface Explicacao {
  tema: string;
  titulo: string;
  o_que_e: string;
  risco: string;
  como_explora: string;
  mitigacao: string;
  aprender_mais: string;
  correcao?: Correcao | null;
}

// Evento da varredura completa (SSE)
export type VarreduraEvent =
  | { tipo: "status"; msg: string }
  | { tipo: "inicio"; total: number; fonte: string }
  | { tipo: "progresso"; i: number; total: number; ip: string }
  | {
      tipo: "host";
      ip: string;
      device_id?: number;
      so?: string | null;
      risco_score?: number;
      risco_rotulo?: string;
      portas?: number;
      criticas?: number;
      web_achados?: number;
      erro?: string;
    }
  | { tipo: "fim"; resumo: SuperficieAtaque }
  | { tipo: "erro"; detail: string };

// ===== chamadas =====
export const api = {
  login: (email: string, senha: string) =>
    req<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, senha }),
    }),

  eu: () => req<User>("/auth/eu"),

  listarDevices: (params: { busca?: string; online?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (params.busca) q.set("busca", params.busca);
    if (params.online !== undefined) q.set("online", String(params.online));
    return req<DeviceList>(`/devices?${q.toString()}`);
  },

  iniciarScan: (rede: string) =>
    req<{ id: number; status: string }>("/scans/start", {
      method: "POST",
      body: JSON.stringify({ rede }),
    }),

  perguntar: (pergunta: string) =>
    req<{ resposta: string; tool_calls: { tool: string }[] }>("/chat", {
      method: "POST",
      body: JSON.stringify({ pergunta }),
    }),

  historico: () =>
    req<{ id: number; role: "user" | "assistant"; conteudo: string; criado_em: string }[]>(
      "/chat/historico"
    ),

  // Versao streaming: chama onEvent para cada evento SSE conforme chega.
  perguntarStream: async (
    pergunta: string,
    onEvent: (ev: ChatEvent) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const token = getToken();
    const r = await fetch(`${BASE}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ pergunta }),
      signal,
    });
    if (!r.ok || !r.body) {
      const txt = await r.text().catch(() => "");
      throw new Error(txt || `HTTP ${r.status}`);
    }

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Frames SSE sao separados por linha em branco (\n\n)
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const linha = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!linha) continue;
        const payload = linha.slice(5).trim();
        if (!payload) continue;
        try {
          onEvent(JSON.parse(payload) as ChatEvent);
        } catch {
          /* ignora frame malformado */
        }
      }
    }
  },

  // ===== Alertas =====
  listarAlertas: (apenasNaoLidos = false) =>
    req<AlertList>(`/alerts?apenas_nao_lidos=${apenasNaoLidos}`),

  marcarLido: (id: number) =>
    req<Alert>(`/alerts/${id}/marcar_lido`, { method: "POST" }),

  marcarTodosLidos: () =>
    req<{ status: string }>("/alerts/marcar_todos_lidos", { method: "POST" }),

  avaliarAlertas: () =>
    req<{ avaliadas: number; gerados: number; notificados_email: number; notificados_telegram: number }>(
      "/alerts/avaliar",
      { method: "POST" }
    ),

  listarRegras: () => req<AlertRule[]>("/alerts/regras"),

  alternarRegra: (id: number, ativa: boolean) =>
    req<AlertRule>(`/alerts/regras/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ ativa }),
    }),

  // ===== Pentest =====
  scanPortas: (alvo: { ip?: string; device_id?: number }) =>
    req<ScanPortasResult>("/pentest/scan", {
      method: "POST",
      body: JSON.stringify(alvo),
    }),

  superficieAtaque: () => req<SuperficieAtaque>("/pentest/superficie"),

  explicar: (tema: string) =>
    req<Explicacao>(`/pentest/explicar?tema=${encodeURIComponent(tema)}`),

  redesLocais: () => req<{ redes: RedeLocal[] }>("/pentest/redes"),

  descobrir: (cidr: string) =>
    req<DescobrirResult>("/pentest/descobrir", {
      method: "POST",
      body: JSON.stringify({ cidr }),
    }),

  relatorioMd: async (): Promise<string> => {
    const token = getToken();
    const r = await fetch(`${BASE}/pentest/relatorio`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!r.ok) throw new Error((await r.text()) || `HTTP ${r.status}`);
    return r.text();
  },

  relatorioPdfBlob: async (): Promise<Blob> => {
    const token = getToken();
    const r = await fetch(`${BASE}/pentest/relatorio.pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!r.ok) throw new Error((await r.text().catch(() => "")) || `HTTP ${r.status}`);
    return r.blob();
  },

  checarCredenciais: (alvo: { ip?: string; device_id?: number }) =>
    req<CredCheckResult>("/pentest/checar-credenciais", {
      method: "POST",
      body: JSON.stringify(alvo),
    }),

  analisarWeb: (alvo: { ip?: string; device_id?: number }) =>
    req<WebResult>("/pentest/web", {
      method: "POST",
      body: JSON.stringify(alvo),
    }),

  dashboard: () => req<DashboardData>("/pentest/dashboard"),
  baseline: () => req<BaselineResult>("/pentest/baseline"),
  attackPath: () => req<AttackPathResult>("/pentest/attack-path"),
  compliance: () => req<ComplianceResult>("/pentest/compliance"),
  patches: () => req<PatchesResult>("/pentest/patches"),
  bas: () => req<BasResult>("/pentest/bas", { method: "POST", body: JSON.stringify({ confirmar: true }) }),

  // Monitor de rede ao vivo (SSE). Chama onSample a cada leitura; aborte via signal.
  monitorStream: async (onSample: (s: NetSample) => void, signal?: AbortSignal): Promise<void> => {
    const token = getToken();
    const r = await fetch(`${BASE}/pentest/monitor/stream`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal,
    });
    if (!r.ok || !r.body) throw new Error((await r.text().catch(() => "")) || `HTTP ${r.status}`);
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const linha = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!linha) continue;
        const payload = linha.slice(5).trim();
        if (!payload) continue;
        try {
          onSample(JSON.parse(payload) as NetSample);
        } catch {
          /* ignora */
        }
      }
    }
  },

  proxyStatus: () => req<ProxyStatus>("/pentest/proxy"),

  setProxy: (url: string) =>
    req<ProxyStatus>("/pentest/proxy", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  // Varredura completa da rede com progresso ao vivo (SSE).
  varreduraCompleta: async (
    body: { cidr?: string; web?: boolean },
    onEvent: (ev: VarreduraEvent) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const token = getToken();
    const r = await fetch(`${BASE}/pentest/varredura-completa`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
    if (!r.ok || !r.body) {
      throw new Error((await r.text().catch(() => "")) || `HTTP ${r.status}`);
    }
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const linha = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!linha) continue;
        const payload = linha.slice(5).trim();
        if (!payload) continue;
        try {
          onEvent(JSON.parse(payload) as VarreduraEvent);
        } catch {
          /* ignora frame malformado */
        }
      }
    }
  },
};
