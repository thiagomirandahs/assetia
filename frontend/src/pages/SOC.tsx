import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, EventoLog } from "../api";

const SEV: Record<string, string> = {
  critical: "bg-rose-500/15 text-rose-300 border-rose-500/40",
  warning: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  info: "bg-sky-500/15 text-sky-300 border-sky-500/40",
};

export default function SOC() {
  const nav = useNavigate();
  const [eventos, setEventos] = useState<EventoLog[]>([]);
  const [seedando, setSeedando] = useState(false);
  const ctrl = useRef<AbortController | null>(null);

  async function carregar() {
    try {
      const r = await api.socEventos();
      setEventos(r.eventos);
    } catch {
      /* silencioso */
    }
  }

  useEffect(() => {
    carregar();
    const c = new AbortController();
    ctrl.current = c;
    api.socStream((e) => setEventos((prev) => [e, ...prev].slice(0, 200)), c.signal).catch(() => {});
    return () => c.abort();
  }, []);

  async function seed() {
    setSeedando(true);
    try {
      await api.socSeedDemo();
      await carregar();
    } catch {
      /* silencioso */
    } finally {
      setSeedando(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
        <h1 className="text-2xl font-bold">🛰️ SOC — Eventos de Segurança</h1>
        <div className="flex gap-2">
          <button onClick={() => nav("/chat")} className="text-sm px-3 py-1.5 bg-cyan-700 hover:bg-cyan-600 rounded-md">
            🤖 correlacionar com a IA
          </button>
          <button onClick={seed} disabled={seedando} className="text-sm px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-md disabled:opacity-50">
            {seedando ? "..." : "+ injetar demo"}
          </button>
        </div>
      </div>
      <p className="text-slate-400 text-sm mb-4">
        Feed ao vivo dos logs ingeridos. Peça ao copiloto <span className="text-cyan-300">“tem ataque em andamento?”</span> — ele correlaciona e monta a timeline do incidente.
      </p>

      {eventos.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-700 rounded-lg p-10 text-center text-slate-400">
          Nenhum evento ainda. Clique <span className="text-cyan-400">+ injetar demo</span> para ver uma cadeia de ataque,
          ou envie logs reais via <span className="font-mono text-slate-300">POST /api/soc/ingest</span> (coletor PowerShell em <span className="font-mono">scripts/</span>).
        </div>
      ) : (
        <div className="space-y-1.5">
          {eventos.map((e) => (
            <div key={e.id} className="flex items-center gap-3 bg-slate-800 border border-slate-700 rounded-md px-4 py-2 text-sm">
              <span className="text-[10px] text-slate-500 font-mono w-16 shrink-0">
                {e.ts ? new Date(e.ts).toLocaleTimeString() : ""}
              </span>
              <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shrink-0 ${SEV[e.severidade] ?? SEV.info}`}>
                {e.severidade}
              </span>
              <span className="text-xs text-slate-400 w-20 truncate shrink-0">{e.fonte}</span>
              <span className="font-mono text-cyan-300 text-xs w-24 truncate shrink-0">{e.host || ""}</span>
              <span className="text-slate-300 flex-1">{e.mensagem}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
