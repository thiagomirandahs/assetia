import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, getToken, setToken, User } from "./api";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api.eu()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <span className="text-slate-400">carregando...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {user && <Topbar user={user} onLogout={() => { setToken(null); setUser(null); }} />}
      <main className="flex-1">
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to="/" /> : <Login onLogin={setUser} />}
          />
          <Route
            path="/"
            element={user ? <Dashboard /> : <Navigate to="/login" />}
          />
          <Route
            path="/chat"
            element={user ? <Chat /> : <Navigate to="/login" />}
          />
        </Routes>
      </main>
    </div>
  );
}

function Topbar({ user, onLogout }: { user: User; onLogout: () => void }) {
  const loc = useLocation();
  const nav = useNavigate();
  const link = (to: string, label: string) => (
    <Link
      to={to}
      className={`px-3 py-2 rounded-md text-sm transition-colors ${
        loc.pathname === to ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800"
      }`}
    >
      {label}
    </Link>
  );
  return (
    <header className="bg-slate-800 border-b border-slate-700">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🛰️</span>
          <span className="font-bold text-lg">AssetIA</span>
        </div>
        <nav className="flex items-center gap-1 ml-4">
          {link("/", "Dashboard")}
          {link("/chat", "Chat IA")}
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
