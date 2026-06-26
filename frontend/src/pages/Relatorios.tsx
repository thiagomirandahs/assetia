import { useState } from "react";
import { api } from "../api";

export default function Relatorios() {
  const [erro, setErro] = useState("");

  function baixarBlob(blob: Blob, nome: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = nome;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function baixarRelatorio() {
    try {
      const md = await api.relatorioMd();
      baixarBlob(new Blob([md], { type: "text/markdown;charset=utf-8" }), "relatorio-reconia.md");
    } catch (e: any) {
      setErro(e.message || "falha ao gerar relatório");
    }
  }

  async function baixarPdf() {
    try {
      baixarBlob(await api.relatorioPdfBlob(), "relatorio-reconia.pdf");
    } catch (e: any) {
      setErro(e.message || "falha ao gerar PDF");
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-1">📄 Relatórios</h1>
      <p className="text-slate-400 text-sm mb-6">
        Gera o laudo da avaliação com resumo executivo, exposições críticas e detalhe por host (portas, CVE, score).
      </p>

      <div className="bg-slate-900/40 border border-slate-700 rounded-lg p-6">
        <p className="text-slate-300 mb-4">Baixe o laudo no formato que preferir:</p>
        <div className="flex gap-3">
          <button onClick={baixarRelatorio} className="px-4 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-md font-medium">
            ⬇ Markdown (.md)
          </button>
          <button onClick={baixarPdf} className="px-4 py-2.5 bg-rose-700 hover:bg-rose-600 rounded-md font-medium">
            ⬇ PDF
          </button>
        </div>
        {erro && <p className="text-rose-400 text-sm mt-4">❌ {erro}</p>}
        <p className="text-xs text-slate-500 mt-5">
          O relatório usa os dados já escaneados. Faça uma Avaliação antes para ter conteúdo.
        </p>
      </div>
    </div>
  );
}
