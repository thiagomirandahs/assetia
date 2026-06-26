import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, DashboardData } from "../api";

export default function Home() {
  const nav = useNavigate();
  const [d, setD] = useState<DashboardData | null>(null);

  useEffect(() => {
    api.dashboard().then(setD).catch(() => {});
  }, []);

  const hosts = d?.hosts_avaliados ?? 0;
  const criticas = d?.criticas ?? 0;
  // passo atual da jornada: 1 descobrir · 2 avaliar · 3 corrigir · 4 relatar
  const passoAtual = hosts === 0 ? 1 : criticas > 0 ? 3 : 4;

  const exp0 = d?.exposicoes_criticas?.[0];
  const proximo =
    hosts === 0
      ? { texto: "Comece descobrindo os hosts da sua rede.", cta: "Descobrir rede", rota: "/avaliacao" }
      : criticas > 0 && exp0
        ? {
            texto: `Corrija o ${exp0.servico} (porta ${exp0.porta}) exposto em ${exp0.ip} — é a sua maior exposição crítica.`,
            cta: "Ver como corrigir",
            rota: "/avaliacao",
          }
        : { texto: "Sem exposições críticas. Gere o relatório da avaliação.", cta: "Gerar relatório", rota: "/avaliacao" };

  function rotuloRisco(s: number): [string, string] {
    if (s >= 80) return ["crítico", "text-rose-400"];
    if (s >= 50) return ["alto", "text-orange-400"];
    if (s >= 20) return ["médio", "text-amber-400"];
    return ["baixo", "text-sky-400"];
  }
  const [rotulo, cor] = rotuloRisco(d?.risco_medio ?? 0);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Visão Geral</h1>

      <button
        onClick={() => nav("/chat")}
        className="w-full flex items-center gap-3 px-4 py-3 mb-6 bg-slate-800/60 border border-slate-700 hover:border-cyan-500 rounded-lg text-left transition-colors"
      >
        <span className="text-cyan-400 text-lg">✨</span>
        <span className="text-slate-400">peça o que quiser — “avalie minha rede e me dê as prioridades”</span>
        <span className="ml-auto text-sm text-cyan-400 whitespace-nowrap">perguntar →</span>
      </button>

      <div className="grid md:grid-cols-[180px_1fr] gap-4 mb-5">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 flex flex-col items-center justify-center">
          <span className="text-xs text-slate-400">risco geral</span>
          <span className={`text-5xl font-bold ${cor}`}>{d ? d.risco_medio : "—"}</span>
          <span className={`text-xs ${cor}`}>{rotulo}</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Metric label="hosts" valor={hosts} />
          <Metric label="críticas" valor={criticas} cor="text-rose-400" />
          <Metric label="CVEs" valor={d?.cves ?? 0} />
          <Metric label="portas abertas" valor={d?.portas_abertas ?? 0} />
        </div>
      </div>

      <div className="flex items-center gap-4 border-2 border-cyan-600/60 bg-cyan-950/30 rounded-lg px-4 py-3 mb-6">
        <span className="text-cyan-400 text-2xl">➜</span>
        <div className="min-w-0">
          <p className="font-semibold text-cyan-300">seu próximo passo</p>
          <p className="text-sm text-slate-300">{proximo.texto}</p>
        </div>
        <button
          onClick={() => nav(proximo.rota)}
          className="ml-auto whitespace-nowrap px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 rounded-md text-sm font-medium"
        >
          {proximo.cta}
        </button>
      </div>

      <p className="text-sm text-slate-400 mb-2">sua jornada</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-7">
        <Step n={1} nome="descobrir" icone="🔍" atual={passoAtual} />
        <Step n={2} nome="avaliar" icone="🎯" atual={passoAtual} />
        <Step n={3} nome="corrigir" icone="🛠️" atual={passoAtual} />
        <Step n={4} nome="relatar" icone="📄" atual={passoAtual} />
      </div>

      <p className="text-sm text-slate-400 mb-2">principais achados</p>
      {d && d.exposicoes_criticas.length === 0 ? (
        <p className="text-slate-400 text-sm">Nenhuma exposição crítica encontrada. 🎉</p>
      ) : (
        <div className="space-y-2">
          {d?.exposicoes_criticas.slice(0, 5).map((e, i) => (
            <div key={i} className="flex items-center gap-3 bg-slate-800 border border-slate-700 rounded-md px-4 py-2.5 text-sm">
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded border bg-rose-500/15 text-rose-300 border-rose-500/40">
                crítica
              </span>
              <span className="font-mono text-cyan-300">{e.ip}:{e.porta}</span>
              <span className="text-slate-400 truncate">{e.servico} — {e.risco}</span>
              <button onClick={() => nav("/avaliacao")} className="ml-auto text-cyan-400 text-xs whitespace-nowrap">
                corrigir
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({ label, valor, cor = "text-white" }: { label: string; valor: number; cor?: string }) {
  return (
    <div className="bg-slate-800/60 rounded-md px-4 py-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className={`text-2xl font-bold ${cor}`}>{valor}</div>
    </div>
  );
}

function Step({ n, nome, icone, atual }: { n: number; nome: string; icone: string; atual: number }) {
  const feito = n < atual;
  const ativo = n === atual;
  const cls = ativo
    ? "border-2 border-cyan-600 bg-cyan-950/30"
    : feito
      ? "border border-emerald-700/50 bg-emerald-950/20"
      : "border border-slate-700";
  const estado = feito ? "concluído" : ativo ? "você está aqui" : "a seguir";
  const estadoCor = ativo ? "text-cyan-300" : feito ? "text-emerald-400" : "text-slate-500";
  return (
    <div className={`rounded-lg p-3 ${cls}`}>
      <div className="flex items-center gap-2">
        <span>{feito ? "✅" : icone}</span>
        <span className="text-sm font-medium">{n} · {nome}</span>
      </div>
      <div className={`text-xs mt-1 ${estadoCor}`}>{estado}</div>
    </div>
  );
}
