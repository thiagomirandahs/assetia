import { useState } from "react";
import { api, setToken, User } from "../api";

export default function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [email, setEmail] = useState("admin@example.com");
  const [senha, setSenha] = useState("demo123");
  const [erro, setErro] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setLoading(true);
    try {
      const r = await api.login(email, senha);
      setToken(r.access_token);
      onLogin(r.user);
    } catch (err: any) {
      setErro(err.message || "falha no login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-6">
      <form
        onSubmit={entrar}
        className="bg-slate-800 border border-slate-700 rounded-xl p-8 w-full max-w-sm shadow-xl"
      >
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🛰️</div>
          <h1 className="text-2xl font-bold">AssetIA</h1>
          <p className="text-sm text-slate-400 mt-1">Inventário inteligente de TI</p>
        </div>

        <label className="block text-sm text-slate-300 mb-1">E-mail</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-md mb-4 focus:outline-none focus:border-cyan-500"
        />

        <label className="block text-sm text-slate-300 mb-1">Senha</label>
        <input
          type="password"
          required
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-md mb-4 focus:outline-none focus:border-cyan-500"
        />

        {erro && <p className="text-sm text-red-400 mb-3">{erro}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 rounded-md font-medium transition-colors"
        >
          {loading ? "entrando..." : "entrar"}
        </button>

        <p className="text-xs text-slate-500 mt-6 text-center">
          demo: <span className="font-mono">admin@example.com / demo123</span>
        </p>
      </form>
    </div>
  );
}
