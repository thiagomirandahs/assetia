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

const SAUDACAO: Msg = {
  role: "assistant",
  texto: "Olá! Sou o ReconIA 🛡️ Posso descobrir hosts, escanear portas, mapear vulnerabilidades e analisar a superfície de ataque. O que vamos avaliar?",
};

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([SAUDACAO]);
  const [pergunta, setPergunta] = useState("");
  const [enviando, setEnviando] = useState(false);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  // carrega o histórico salvo ao abrir o chat (persiste a conversa entre sessões)
  useEffect(() => {
    api.historico()
      .then((hist) => {
        if (hist.length > 0) {
          setMsgs([SAUDACAO, ...hist.map((h) => ({ role: h.role, texto: h.conteudo }))]);
        }
      })
      .catch(() => {});
  }, []);

  // Atualiza a ultima mensagem (a bolha do assistente que esta sendo preenchida).
  function atualizarUltima(fn: (m: Msg) => Msg) {
    setMsgs((arr) => {
      const copy = [...arr];
      const i = copy.length - 1;
      if (copy[i]?.role === "assistant") copy[i] = fn(copy[i]);
      return copy;
    });
  }

  async function enviar(texto?: string) {
    const q = (texto ?? pergunta).trim();
    if (!q || enviando) return;
    // adiciona a pergunta + uma bolha vazia do assistente que sera preenchida via streaming
    setMsgs((m) => [...m, { role: "user", texto: q }, { role: "assistant", texto: "", tools: [] }]);
    setPergunta("");
    setEnviando(true);
    try {
      await api.perguntarStream(q, (ev) => {
        if (ev.tipo === "token") {
          atualizarUltima((m) => ({ ...m, texto: m.texto + ev.texto }));
        } else if (ev.tipo === "tool") {
          atualizarUltima((m) => ({ ...m, tools: [...(m.tools ?? []), ev.tool] }));
        } else if (ev.tipo === "fim") {
          atualizarUltima((m) => ({ ...m, texto: m.texto || ev.resposta }));
        } else if (ev.tipo === "erro") {
          atualizarUltima((m) => ({ ...m, texto: `❌ erro: ${ev.detail}` }));
        }
      });
    } catch (e: any) {
      atualizarUltima((m) => ({ ...m, texto: m.texto || `❌ erro: ${e.message}` }));
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
          <Bubble
            key={i}
            msg={m}
            streaming={enviando && i === msgs.length - 1 && m.role === "assistant"}
          />
        ))}
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

function Bubble({ msg, streaming = false }: { msg: Msg; streaming?: boolean }) {
  const ehUser = msg.role === "user";
  return (
    <div className={`flex ${ehUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] px-4 py-3 rounded-2xl ${
          ehUser ? "bg-cyan-600 text-white" : "bg-slate-800 border border-slate-700"
        }`}
      >
        {msg.tools && msg.tools.length > 0 && (
          <p className="text-[10px] text-cyan-300/80 mb-1.5 italic">
            🔧 {msg.tools.join(" · ")}
          </p>
        )}
        <p className="text-sm whitespace-pre-wrap leading-relaxed">
          {msg.texto}
          {streaming && (
            <span className="inline-block w-1.5 h-4 ml-0.5 -mb-0.5 align-middle bg-cyan-400 animate-pulse" />
          )}
        </p>
      </div>
    </div>
  );
}
