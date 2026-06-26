import { useEffect, useRef, useState } from "react";
import { api, NetSample } from "../api";

function fmtTaxa(bps: number): string {
  if (bps >= 1048576) return (bps / 1048576).toFixed(2) + " MB/s";
  if (bps >= 1024) return (bps / 1024).toFixed(1) + " KB/s";
  return Math.round(bps) + " B/s";
}

function Sparkline({ hist }: { hist: NetSample[] }) {
  if (hist.length < 2) return <svg width={280} height={48} />;
  const w = 280;
  const h = 48;
  const max = Math.max(1, ...hist.map((s) => Math.max(s.upload_bps, s.download_bps)));
  const pts = (sel: (s: NetSample) => number) =>
    hist.map((s, i) => `${(i / (hist.length - 1)) * w},${h - (sel(s) / max) * h}`).join(" ");
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={pts((s) => s.download_bps)} fill="none" stroke="#34d399" strokeWidth="1.5" />
      <polyline points={pts((s) => s.upload_bps)} fill="none" stroke="#22d3ee" strokeWidth="1.5" />
    </svg>
  );
}

export default function Monitor() {
  const [monitorAtivo, setMonitorAtivo] = useState(false);
  const [netNow, setNetNow] = useState<NetSample | null>(null);
  const [netHist, setNetHist] = useState<NetSample[]>([]);
  const monitorCtrl = useRef<AbortController | null>(null);

  function iniciarMonitor() {
    if (monitorAtivo) return;
    const ctrl = new AbortController();
    monitorCtrl.current = ctrl;
    setMonitorAtivo(true);
    setNetHist([]);
    setNetNow(null);
    api
      .monitorStream((s) => {
        setNetNow(s);
        setNetHist((h) => [...h.slice(-39), s]);
      }, ctrl.signal)
      .catch(() => {})
      .finally(() => setMonitorAtivo(false));
  }

  function pararMonitor() {
    monitorCtrl.current?.abort();
    setMonitorAtivo(false);
  }

  useEffect(() => () => monitorCtrl.current?.abort(), []);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-1">📡 Monitor de Rede</h1>
      <p className="text-slate-400 text-sm mb-6">Upload e download da máquina, em tempo real.</p>

      <section className="bg-slate-900/40 border border-slate-700 rounded-lg p-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <h2 className="font-semibold">Throughput ao vivo</h2>
            <p className="text-xs text-slate-400">Atualiza a cada segundo.</p>
          </div>
          <button
            onClick={monitorAtivo ? pararMonitor : iniciarMonitor}
            className={`text-sm px-4 py-2 rounded-md font-medium ${
              monitorAtivo ? "bg-rose-700 hover:bg-rose-600" : "bg-emerald-700 hover:bg-emerald-600"
            }`}
          >
            {monitorAtivo ? "⏹ parar" : "▶ iniciar"}
          </button>
        </div>
        {netNow ? (
          <div className="mt-4 flex items-end gap-6 flex-wrap">
            <div>
              <div className="text-emerald-400 text-2xl font-bold">↓ {fmtTaxa(netNow.download_bps)}</div>
              <div className="text-xs text-slate-500">download</div>
            </div>
            <div>
              <div className="text-cyan-400 text-2xl font-bold">↑ {fmtTaxa(netNow.upload_bps)}</div>
              <div className="text-xs text-slate-500">upload</div>
            </div>
            <div className="ml-auto">
              <Sparkline hist={netHist} />
              <div className="text-[10px] text-slate-500 text-right">
                <span className="text-emerald-400">━</span> down · <span className="text-cyan-400">━</span> up
              </div>
            </div>
          </div>
        ) : (
          monitorAtivo && <p className="text-slate-400 text-sm mt-3">medindo…</p>
        )}
      </section>
    </div>
  );
}
