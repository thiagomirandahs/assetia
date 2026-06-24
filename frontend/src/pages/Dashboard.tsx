import { useEffect, useState } from "react";
import { api, Device, DeviceList } from "../api";

export default function Dashboard() {
  const [dados, setDados] = useState<DeviceList | null>(null);
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState<"todos" | "online" | "offline">("todos");
  const [rede, setRede] = useState("192.168.1.0/24");
  const [scanIniciado, setScanIniciado] = useState<string | null>(null);

  async function carregar() {
    const params: { busca?: string; online?: boolean } = {};
    if (busca) params.busca = busca;
    if (filtro === "online") params.online = true;
    if (filtro === "offline") params.online = false;
    const r = await api.listarDevices(params);
    setDados(r);
  }

  useEffect(() => {
    carregar().catch(console.error);
  }, [filtro]);

  async function iniciarScan() {
    setScanIniciado("iniciando...");
    try {
      const r = await api.iniciarScan(rede);
      setScanIniciado(`scan #${r.id} em andamento (${r.status}) — atualiza em ~30s`);
      setTimeout(() => { carregar(); setScanIniciado(null); }, 30000);
    } catch (e: any) {
      setScanIniciado(`erro: ${e.message}`);
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
      <p className="text-slate-400 text-sm mb-6">Inventário de dispositivos da sua rede</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card label="Total" value={dados?.total ?? "—"} color="text-cyan-400" />
        <Card label="Online" value={dados?.online ?? "—"} color="text-emerald-400" />
        <Card label="Offline" value={dados?.offline ?? "—"} color="text-rose-400" />
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 mb-6">
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-end">
          <div className="flex-1">
            <label className="text-xs text-slate-400 uppercase tracking-wide">Rede para escanear</label>
            <input
              value={rede}
              onChange={(e) => setRede(e.target.value)}
              placeholder="192.168.1.0/24"
              className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-700 rounded-md focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            onClick={iniciarScan}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-md font-medium"
          >
            🔍 Iniciar scan
          </button>
        </div>
        {scanIniciado && <p className="text-sm text-cyan-300 mt-2">{scanIniciado}</p>}
      </div>

      <div className="flex flex-col sm:flex-row gap-3 items-stretch mb-4">
        <input
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && carregar()}
          placeholder="buscar hostname, IP, MAC, fabricante..."
          className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-md focus:outline-none focus:border-cyan-500"
        />
        <div className="flex gap-1">
          {(["todos", "online", "offline"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFiltro(f)}
              className={`px-3 py-2 rounded-md text-sm capitalize ${
                filtro === f ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Hostname</th>
              <th className="text-left px-4 py-3">IP</th>
              <th className="text-left px-4 py-3">MAC</th>
              <th className="text-left px-4 py-3">Fabricante</th>
              <th className="text-left px-4 py-3">SO</th>
              <th className="text-left px-4 py-3">Tipo</th>
            </tr>
          </thead>
          <tbody>
            {dados?.devices.map((d) => (
              <DeviceRow key={d.id} d={d} />
            ))}
            {dados && dados.devices.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center py-8 text-slate-400">
                  nenhum dispositivo encontrado
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Card({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
      <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
      <div className={`text-4xl font-bold mt-2 ${color}`}>{value}</div>
    </div>
  );
}

function DeviceRow({ d }: { d: Device }) {
  return (
    <tr className="border-t border-slate-700 hover:bg-slate-700/30">
      <td className="px-4 py-3">
        <span className={`inline-block w-2.5 h-2.5 rounded-full ${d.online ? "bg-emerald-400" : "bg-slate-500"}`} />
      </td>
      <td className="px-4 py-3 font-medium">{d.hostname || <span className="text-slate-500">—</span>}</td>
      <td className="px-4 py-3 font-mono text-xs">{d.ip}</td>
      <td className="px-4 py-3 font-mono text-xs text-slate-400">{d.mac || "—"}</td>
      <td className="px-4 py-3">{d.fabricante || "—"}</td>
      <td className="px-4 py-3">{d.so || "—"}</td>
      <td className="px-4 py-3">
        {d.tipo && (
          <span className="inline-block px-2 py-0.5 text-xs bg-slate-700 rounded">{d.tipo}</span>
        )}
      </td>
    </tr>
  );
}
