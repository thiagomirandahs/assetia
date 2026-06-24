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
};
