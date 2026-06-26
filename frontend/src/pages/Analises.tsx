import { useState } from "react";
import { api, AttackPathResult, BaselineResult, BasResult, ComplianceResult, PatchesResult } from "../api";

export default function Analises() {
  const [baseline, setBaseline] = useState<BaselineResult | null>(null);
  const [attackPath, setAttackPath] = useState<AttackPathResult | null>(null);
  const [compliance, setCompliance] = useState<ComplianceResult | null>(null);
  const [patches, setPatches] = useState<PatchesResult | null>(null);
  const [bas, setBas] = useState<BasResult | null>(null);
  const [analise, setAnalise] = useState("");
  const [erro, setErro] = useState("");

  async function rodarAnalise(qual: "baseline" | "attack" | "compliance" | "patches") {
    setAnalise(qual);
    setErro("");
    try {
      if (qual === "baseline") setBaseline(await api.baseline());
      else if (qual === "attack") setAttackPath(await api.attackPath());
      else if (qual === "compliance") setCompliance(await api.compliance());
      else if (qual === "patches") setPatches(await api.patches());
    } catch (e: any) {
      setErro(e.message || "falha na análise");
    } finally {
      setAnalise("");
    }
  }

  async function rodarBas() {
    if (analise) return;
    const ok = window.confirm(
      "Rodar BAS (simulação de ataque) NESTA máquina?\n\nSão testes ATÔMICOS SEGUROS e reversíveis " +
        "(EICAR, recon, LOLBin, persistência reversível) para checar se suas defesas detectam. " +
        "O teste EICAR vai gerar um alerta no seu antivírus (é esperado). Só rode em máquina sua/autorizada."
    );
    if (!ok) return;
    setAnalise("bas");
    setErro("");
    try {
      setBas(await api.bas());
    } catch (e: any) {
      setErro(e.message || "falha no BAS");
    } finally {
      setAnalise("");
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-1">🧠 Análises</h1>
      <p className="text-slate-400 text-sm mb-6">
        Mede a maturidade, traça o caminho de ataque, avalia conformidade e testa as defesas. Use após escanear alguns hosts.
      </p>

      <div className="flex flex-wrap gap-2 mb-2">
        <button onClick={() => rodarAnalise("baseline")} disabled={!!analise} className="text-sm px-3 py-1.5 bg-slate-800 border border-slate-600 hover:border-cyan-500 rounded-md disabled:opacity-50">
          {analise === "baseline" ? "medindo…" : "🛡️ Security Baseline"}
        </button>
        <button onClick={() => rodarAnalise("attack")} disabled={!!analise} className="text-sm px-3 py-1.5 bg-slate-800 border border-slate-600 hover:border-rose-500 rounded-md disabled:opacity-50">
          {analise === "attack" ? "traçando…" : "🎯 Attack Path"}
        </button>
        <button onClick={() => rodarAnalise("compliance")} disabled={!!analise} className="text-sm px-3 py-1.5 bg-slate-800 border border-slate-600 hover:border-emerald-500 rounded-md disabled:opacity-50">
          {analise === "compliance" ? "avaliando…" : "📋 Compliance"}
        </button>
        <button onClick={() => rodarAnalise("patches")} disabled={!!analise} className="text-sm px-3 py-1.5 bg-slate-800 border border-slate-600 hover:border-fuchsia-500 rounded-md disabled:opacity-50">
          {analise === "patches" ? "consultando…" : "🩹 Patch Advisor"}
        </button>
        <button onClick={rodarBas} disabled={!!analise} className="text-sm px-3 py-1.5 bg-rose-900/40 border border-rose-700 hover:border-rose-500 rounded-md disabled:opacity-50">
          {analise === "bas" ? "simulando…" : "💥 BAS (ataque simulado)"}
        </button>
      </div>

      {erro && <p className="text-rose-400 text-sm mb-3">❌ {erro}</p>}

      {baseline && (
        <div className="mt-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl font-bold">{baseline.score}</span>
            <span className="text-slate-400">/100 · {baseline.rotulo} ({baseline.so})</span>
          </div>
          <div className="grid sm:grid-cols-2 gap-1.5">
            {baseline.checks.map((c) => (
              <div key={c.chave} className="flex items-center gap-2 text-sm">
                <span>{c.estado === "ok" ? "✅" : c.estado === "falha" ? "❌" : "➖"}</span>
                <span className="text-slate-300">{c.rotulo}</span>
                {c.dica && <span className="text-slate-500 text-xs">— {c.dica}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {attackPath && (
        <div className="mt-4">
          {!attackPath.ok ? (
            <p className="text-slate-400 text-sm">{attackPath.motivo}</p>
          ) : (
            <div className="space-y-1.5">
              {attackPath.passos!.map((p, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-rose-400 font-mono text-xs mt-0.5">{i + 1}.</span>
                  <div>
                    <span className="font-mono text-cyan-300">{p.de} → {p.para}</span>{" "}
                    <span className="text-slate-200">{p.tecnica}</span>
                    <p className="text-slate-500 text-xs">{p.detalhe}</p>
                  </div>
                </div>
              ))}
              <p className="text-amber-300 text-sm mt-2">💡 {attackPath.recomendacao}</p>
            </div>
          )}
        </div>
      )}

      {compliance && (
        <div className="mt-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl font-bold text-emerald-400">{compliance.percentual}%</span>
            <span className="text-slate-400">conforme · {compliance.pendentes} pendentes</span>
          </div>
          <div className="space-y-1">
            {compliance.itens.map((it, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span>{it.estado === "conforme" ? "✅" : it.estado === "não conforme" ? "❌" : "➖"}</span>
                <span className="text-slate-300">{it.controle}</span>
                <span className="text-slate-500 text-xs ml-auto">{it.frameworks}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {patches && (
        <div className="mt-4">
          <p className="text-sm text-slate-300 mb-2">{patches.total_cves} CVE(s) · {patches.criticos} crítica(s)</p>
          <div className="space-y-1">
            {patches.cves.slice(0, 10).map((c) => (
              <div key={c.cve} className="text-sm">
                <span className="font-mono text-fuchsia-300">{c.cve}</span>{" "}
                <span className="text-slate-300">{c.descricao}</span>{" "}
                <span className="text-slate-500 text-xs">({c.hosts.length} host)</span>
              </div>
            ))}
            {patches.acoes_por_servico.map((a) => (
              <p key={a.servico} className="text-xs text-slate-400">🩹 {a.acao} — {a.hosts.length} host(s)</p>
            ))}
          </div>
        </div>
      )}

      {bas && (
        <div className="mt-4">
          <p className="text-sm text-slate-300 mb-2">
            {bas.total} testes · <span className="text-emerald-400">{bas.detectados_bloqueados} detectado(s)/bloqueado(s)</span> pelas defesas
          </p>
          <div className="space-y-1.5">
            {bas.resultados.map((r) => (
              <div key={r.id} className="flex items-start gap-2 text-sm bg-slate-800 border border-slate-700 rounded px-3 py-1.5">
                <span>{r.bloqueado === true ? "🛡️" : r.bloqueado === false ? "⚠️" : "▫️"}</span>
                <div>
                  <span className="text-slate-200">{r.tecnica}</span>{" "}
                  <span className="font-mono text-[10px] text-rose-300">{r.mitre}</span>
                  <p className="text-slate-500 text-xs">{r.detalhe}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-2">{bas.aviso}</p>
        </div>
      )}
    </div>
  );
}
