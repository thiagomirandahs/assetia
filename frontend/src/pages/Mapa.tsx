import { useEffect, useState } from "react";
import { api, MapaHost, MapaRede } from "../api";

function corRisco(s: number | null): string {
  if (s == null) return "#64748b"; // slate
  if (s >= 80) return "#f43f5e"; // rose
  if (s >= 50) return "#fb923c"; // orange
  if (s >= 20) return "#fbbf24"; // amber
  return "#38bdf8"; // sky
}

export default function Mapa() {
  const [m, setM] = useState<MapaRede | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    try {
      setM(await api.mapa());
    } catch {
      /* silencioso */
    } finally {
      setCarregando(false);
    }
  }
  useEffect(() => {
    carregar();
  }, []);

  const W = 900;
  const H = 600;
  const cx = W / 2;
  const cy = 320;
  const hosts: MapaHost[] = (m?.hosts ?? []).filter((h) => !h.eh_gateway);
  const N = hosts.length;
  const raio = Math.min(240, 120 + N * 6);

  const legenda: [string, string][] = [
    ["crítico", "#f43f5e"],
    ["alto", "#fb923c"],
    ["médio", "#fbbf24"],
    ["baixo", "#38bdf8"],
    ["sem dados", "#64748b"],
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between gap-3 mb-1">
        <h1 className="text-2xl font-bold">🗺️ Digital Twin — Mapa da Rede</h1>
        <button
          onClick={carregar}
          disabled={carregando}
          className="text-sm px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-md disabled:opacity-50"
        >
          {carregando ? "..." : "↻ atualizar"}
        </button>
      </div>
      <p className="text-slate-400 text-sm mb-4">
        Cada host aparece conforme você o escaneia, colorido pelo risco. O gateway fica no centro.
      </p>

      <div className="flex flex-wrap gap-3 text-xs text-slate-400 mb-3">
        {legenda.map(([l, c]) => (
          <span key={l} className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: c }} />
            {l}
          </span>
        ))}
      </div>

      {N === 0 ? (
        <div className="bg-slate-900/40 border border-slate-700 rounded-lg p-10 text-center text-slate-400">
          Nenhum host no mapa ainda. Vá em <span className="text-cyan-400">Avaliação</span>, faça uma varredura — os equipamentos aparecem aqui automaticamente.
        </div>
      ) : (
        <div className="bg-slate-900/40 border border-slate-700 rounded-lg p-2 overflow-x-auto">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 620 }}>
            <line x1={cx} y1={72} x2={cx} y2={cy} stroke="#334155" strokeWidth="2" />

            {hosts.map((h, i) => {
              const ang = (i / N) * 2 * Math.PI - Math.PI / 2;
              const x = cx + raio * Math.cos(ang);
              const y = cy + raio * Math.sin(ang);
              return (
                <g key={h.ip}>
                  <line x1={cx} y1={cy} x2={x} y2={y} stroke="#334155" strokeWidth="1" />
                  <circle cx={x} cy={y} r="9" fill={corRisco(h.risco_score)} stroke="#0f172a" strokeWidth="2" />
                  <text x={x} y={y - 14} textAnchor="middle" fontSize="11" fill="#cbd5e1" fontFamily="monospace">
                    {h.ip}
                  </text>
                  <text x={x} y={y + 23} textAnchor="middle" fontSize="9" fill="#64748b">
                    {(h.fabricante || h.so || "").slice(0, 18)}
                  </text>
                </g>
              );
            })}

            <rect x={cx - 52} y={45} width="104" height="36" rx="8" fill="#1e293b" stroke="#475569" />
            <text x={cx} y={68} textAnchor="middle" fontSize="13" fill="#94a3b8">
              🌐 Internet
            </text>

            <circle cx={cx} cy={cy} r="28" fill="#0e7490" stroke="#22d3ee" strokeWidth="2" />
            <text x={cx} y={cy - 2} textAnchor="middle" fontSize="11" fill="#e0f2fe">
              Gateway
            </text>
            <text x={cx} y={cy + 12} textAnchor="middle" fontSize="9" fill="#a5f3fc" fontFamily="monospace">
              {m?.gateway || "?"}
            </text>
          </svg>
        </div>
      )}

      <p className="text-xs text-slate-500 mt-3">
        {N} host(s) no mapa.{m?.gateway ? ` Gateway: ${m.gateway}.` : ""} Topologia lógica — links físicos exigiriam LLDP/SNMP.
      </p>
    </div>
  );
}
