import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, getToken, setToken, User } from "./api";
import Alerts from "./pages/Alerts";
import Chat from "./pages/Chat";
import Analises from "./pages/Analises";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Mapa from "./pages/Mapa";
import Monitor from "./pages/Monitor";
import Pentest from "./pages/Pentest";
import Relatorios from "./pages/Relatorios";
import SOC from "./pages/SOC";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [alertasNaoLidos, setAlertasNaoLidos] = useState(0);

  const recarregarBadge = useCallback(async () => {
    if (!getToken()) return;
    try {
      const r = await api.listarAlertas(true);
      setAlertasNaoLidos(r.nao_lidos);
    } catch { /* silencioso */ }
  }, []);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api.eu()
      .then((u) => { setUser(u); recarregarBadge(); })
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, [recarregarBadge]);

  // Atualiza badge a cada 30s
  useEffect(() => {
    if (!user) return;
    const id = setInterval(recarregarBadge, 30000);
    return () => clearInterval(id);
  }, [user, recarregarBadge]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <span className="text-slate-400">carregando...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {user && (
        <Topbar
          user={user}
          alertasNaoLidos={alertasNaoLidos}
          onLogout={() => { setToken(null); setUser(null); }}
        />
      )}
      <main className="flex-1">
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to="/" /> : <Login onLogin={(u) => { setUser(u); recarregarBadge(); }} />}
          />
          <Route path="/" element={user ? <Home /> : <Navigate to="/login" />} />
          <Route path="/avaliacao" element={user ? <Pentest /> : <Navigate to="/login" />} />
          <Route path="/pentest" element={user ? <Pentest /> : <Navigate to="/login" />} />
          <Route path="/analises" element={user ? <Analises /> : <Navigate to="/login" />} />
          <Route path="/monitor" element={user ? <Monitor /> : <Navigate to="/login" />} />
          <Route path="/mapa" element={user ? <Mapa /> : <Navigate to="/login" />} />
          <Route path="/soc" element={user ? <SOC /> : <Navigate to="/login" />} />
          <Route path="/relatorios" element={user ? <Relatorios /> : <Navigate to="/login" />} />
          <Route path="/inventario" element={user ? <Dashboard /> : <Navigate to="/login" />} />
          <Route path="/alertas" element={user ? <Alerts /> : <Navigate to="/login" />} />
          <Route path="/chat" element={user ? <Chat /> : <Navigate to="/login" />} />
        </Routes>
      </main>
    </div>
  );
}

function Topbar({ user, alertasNaoLidos, onLogout }: { user: User; alertasNaoLidos: number; onLogout: () => void }) {
  const loc = useLocation();
  const nav = useNavigate();
  const link = (to: string, label: string, badge?: number) => (
    <Link
      to={to}
      className={`relative px-3 py-2 rounded-md text-sm transition-colors ${
        loc.pathname === to ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800"
      }`}
    >
      {label}
      {badge !== undefined && badge > 0 && (
        <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] inline-flex items-center justify-center px-1">
          {badge > 99 ? "99+" : badge}
        </span>
      )}
    </Link>
  );
  return (
    <header className="bg-slate-800 border-b border-slate-700">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🛡️</span>
          <span className="font-bold text-lg">ReconIA</span>
        </div>
        <nav className="flex items-center gap-1 ml-4">
          {link("/", "Visão geral")}
          {link("/avaliacao", "Avaliação")}
          {link("/analises", "Análises")}
          {link("/mapa", "Mapa")}
          {link("/monitor", "Monitor")}
          {link("/soc", "SOC")}
          {link("/relatorios", "Relatórios")}
          {link("/alertas", "Alertas", alertasNaoLidos)}
          {link("/chat", "Copiloto")}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-sm text-slate-400">{user.email}</span>
          <button
            onClick={() => { onLogout(); nav("/login"); }}
            className="text-sm px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-600"
          >
            sair
          </button>
        </div>
      </div>
    </header>
  );
}
