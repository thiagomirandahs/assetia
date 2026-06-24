import { useEffect, useRef, useState } from "react";
import { api } from "../api";

interface Msg {
  role: "user" | "assistant";
  texto: string;
  tools?: string[];
}

const SUGESTOES = [
  "me dá um resumo do inventário",
  "quantos dispositivos online eu tenho?",
  "apareceu algo novo na rede nos últimos 7 dias?",
  "quais dispositivos estão offline há mais de 30 dias?",
  "tem algum dispositivo desconhecido?",
];

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "assistant", texto: "Olá! Sou o AssetIA. Pergunte qualquer coisa sobre seu inventário 🛰️" },
  ]);
  const [pergunta, setPergunta] = useState("");
  const [enviando, setEnviando] = useState(false);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  async function enviar(texto?: string) {
    const q = (texto ?? pergunta).trim();
    if (!q || enviando) return;
    setMsgs((m) => [...m, { role: "user", texto: q }]);
    setPergunta("");
    setEnviando(true);
    try {
      const r = await api.perguntar(q);
      setMsgs((m) => [
        ...m,
        { role: "assistant", texto: r.resposta, tools: r.tool_calls?.map((t) => t.tool) },
      ]);
    } catch (e: any) {
      setMsgs((m) => [...m, { role: "assistant", texto: `❌ erro: ${e.message}` }]);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 flex flex-col h-[calc(100vh-80px)]">
      <h1 className="text-2xl font-bold mb-1">Chat com a IA</h1>
      <p className="text-slate-400 text-sm mb-6">
        O agente consulta seu banco de dispositivos em tempo real para responder.
      </p>

      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {msgs.map((m, i) => (
          <Bubble key={i} msg={m} />
        ))}
        {enviando && <Bubble msg={{ role: "assistant", texto: "..." }} />}
        <div ref={fim} />
      </div>

      {msgs.length <= 1 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {SUGESTOES.map((s) => (
            <button
              key={s}
              onClick={() => enviar(s)}
              className="text-xs px-3 py-1.5 bg-slate-800 border border-slate-700 hover:border-cyan-500 rounded-full text-slate-300"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <form
        onSubmit={(e) => { e.preventDefault(); enviar(); }}
        className="flex gap-2"
      >
        <input
          value={pergunta}
          onChange={(e) => setPergunta(e.target.value)}
          placeholder="pergunte algo sobre seus dispositivos..."
          disabled={enviando}
          className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 rounded-md focus:outline-none focus:border-cyan-500"
        />
        <button
          type="submit"
          disabled={enviando || !pergunta.trim()}
          className="px-5 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 rounded-md font-medium"
        >
          enviar
        </button>
      </form>
    </div>
  );
}

function Bubble({ msg }: { msg: Msg }) {
  const ehUser = msg.role === "user";
  return (
    <div className={`flex ${ehUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] px-4 py-3 rounded-2xl ${
          ehUser ? "bg-cyan-600 text-white" : "bg-slate-800 border border-slate-700"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.texto}</p>
        {msg.tools && msg.tools.length > 0 && (
          <p className="text-[10px] text-slate-400 mt-2 italic">
            🔧 ferramentas: {msg.tools.join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}
