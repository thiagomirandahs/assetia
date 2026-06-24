import { useEffect, useState } from "react";
import { Alert, AlertRule, api } from "../api";

const ICONES: Record<string, string> = { info: "ℹ️", warning: "⚠️", critical: "🚨" };
const CORES: Record<string, string> = {
  info: "border-cyan-500 bg-cyan-500/10",
  warning: "border-amber-500 bg-amber-500/10",
  critical: "border-rose-500 bg-rose-500/10",
};
const COR_BADGE: Record<string, string> = {
  info: "bg-cyan-500",
  warning: "bg-amber-500",
  critical: "bg-rose-500",
};

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [naoLidos, setNaoLidos] = useState(0);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [filtro, setFiltro] = useState<"todos" | "nao_lidos">("todos");
  const [aba, setAba] = useState<"alertas" | "regras">("alertas");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    try {
      const [a, r] = await Promise.all([
        api.listarAlertas(filtro === "nao_lidos"),
        api.listarRegras(),
      ]);
      setAlerts(a.alerts);
      setTotal(a.total);
      setNaoLidos(a.nao_lidos);
      setRules(r);
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => { carregar().catch(console.error); }, [filtro]);

  async function avaliar() {
    setCarregando(true);
    try {
      const r = await api.avaliarAlertas();
      alert(`Avaliação concluída: ${r.gerados} novos alertas gerados (de ${r.avaliadas} regras).`);
      await carregar();
    } catch (e: any) {
      alert(`Erro: ${e.message}`);
    } finally {
      setCarregando(false);
    }
  }

  async function lerTodos() {
    if (!confirm("Marcar todos os alertas como lidos?")) return;
    await api.marcarTodosLidos();
    await carregar();
  }

  async function lerUm(id: number) {
    await api.marcarLido(id);
    await carregar();
  }

  async function alternarRegra(id: number, ativa: boolean) {
    await api.alternarRegra(id, ativa);
    await carregar();
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Alertas inteligentes</h1>
          <p className="text-slate-400 text-sm">
            Sistema de detecção automática de eventos críticos na rede
          </p>
        </div>
        <button
          onClick={avaliar}
          disabled={carregando}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 rounded-md font-medium text-sm"
        >
          🔄 Avaliar regras agora
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <Card label="Total de alertas" value={total} color="text-cyan-400" />
        <Card label="Não lidos" value={naoLidos} color="text-amber-400" />
        <Card label="Regras ativas" value={rules.filter((r) => r.ativa).length} color="text-emerald-400" />
      </div>

      <div className="flex gap-1 mb-4 border-b border-slate-700">
        <TabBtn ativo={aba === "alertas"} onClick={() => setAba("alertas")}>Alertas</TabBtn>
        <TabBtn ativo={aba === "regras"} onClick={() => setAba("regras")}>Regras</TabBtn>
      </div>

      {aba === "alertas" ? (
        <>
          <div className="flex items-center justify-between mb-3">
            <div className="flex gap-1">
              <PillBtn ativo={filtro === "todos"} onClick={() => setFiltro("todos")}>todos</PillBtn>
              <PillBtn ativo={filtro === "nao_lidos"} onClick={() => setFiltro("nao_lidos")}>
                não lidos ({naoLidos})
              </PillBtn>
            </div>
            {naoLidos > 0 && (
              <button
                onClick={lerTodos}
                className="text-xs text-slate-300 hover:text-white"
              >
                marcar todos como lidos
              </button>
            )}
          </div>

          <div className="space-y-2">
            {alerts.length === 0 ? (
              <p className="text-center py-10 text-slate-500">
                {carregando ? "carregando..." : "nenhum alerta no momento 🎉"}
              </p>
            ) : (
              alerts.map((a) => (
                <div
                  key={a.id}
                  className={`border-l-4 ${CORES[a.severidade] || ""} ${
                    a.lido ? "opacity-60" : ""
                  } bg-slate-800 border-slate-700 border rounded-r-md p-4`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span>{ICONES[a.severidade]}</span>
                        <h3 className="font-semibold text-sm">{a.titulo}</h3>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded text-white ${COR_BADGE[a.severidade]}`}>
                          {a.severidade}
                        </span>
                      </div>
                      <pre className="text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">{a.mensagem}</pre>
                      <p className="text-[10px] text-slate-500 mt-2">
                        {new Date(a.criado_em).toLocaleString("pt-BR")}
                      </p>
                    </div>
                    {!a.lido && (
                      <button
                        onClick={() => lerUm(a.id)}
                        className="text-xs text-slate-300 hover:text-white shrink-0"
                      >
                        marcar lido
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      ) : (
        <div className="space-y-2">
          {rules.map((r) => (
            <div
              key={r.id}
              className="bg-slate-800 border border-slate-700 rounded-md p-4 flex items-start justify-between gap-3"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span>{ICONES[r.severidade] || "•"}</span>
                  <h3 className="font-semibold text-sm">{r.nome}</h3>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded text-white ${COR_BADGE[r.severidade]}`}>
                    {r.severidade}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{r.descricao}</p>
                <p className="text-[10px] text-slate-500 mt-1 font-mono">
                  tipo: {r.tipo} · canais: {r.canais}
                </p>
              </div>
              <label className="inline-flex items-center cursor-pointer shrink-0">
                <input
                  type="checkbox"
                  checked={r.ativa}
                  onChange={(e) => alternarRegra(r.id, e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-slate-600 peer-checked:bg-emerald-500 rounded-full relative transition-colors">
                  <div
                    className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                      r.ativa ? "translate-x-5" : ""
                    }`}
                  />
                </div>
              </label>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Card({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
      <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
      <div className={`text-3xl font-bold mt-1 ${color}`}>{value}</div>
    </div>
  );
}

function TabBtn({ ativo, onClick, children }: { ativo: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm transition-colors -mb-px border-b-2 ${
        ativo ? "border-cyan-500 text-white" : "border-transparent text-slate-400 hover:text-slate-200"
      }`}
    >
      {children}
    </button>
  );
}

function PillBtn({ ativo, onClick, children }: { ativo: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-md text-xs ${
        ativo ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
      }`}
    >
      {children}
    </button>
  );
}
