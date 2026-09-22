import { useState } from "react";
import { api, clearToken, getToken, setToken } from "./api";
import { Alerts } from "./pages/Alerts";
import { Dashboard } from "./pages/Dashboard";
import { Devices } from "./pages/Devices";
import { KnownDevices } from "./pages/KnownDevices";
import { LteCells } from "./pages/LteCells";
import { Observations } from "./pages/Observations";

const PAGES = ["Dashboard", "Devices", "Observations", "LTE Cells", "Alerts", "Known Devices"] as const;
type Page = (typeof PAGES)[number];

function ErrorText({ msg }: { msg: string }) {
  return msg ? <p className="text-sm text-red-400">{msg}</p> : null;
}

function LoginGate({ onSet }: { onSet: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await api.authLogin({ username, password, totp_code: totp });
      setToken(res.token);
      onSet();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <form
        onSubmit={submit}
        className="w-96 space-y-3 rounded border border-neutral-800 p-6"
      >
        <h1 className="text-lg font-semibold">Scorpion</h1>
        <p className="text-sm text-neutral-400">Sign in with your account and 2FA code.</p>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full rounded bg-neutral-900 p-2"
          placeholder="username"
          autoComplete="username"
          required
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded bg-neutral-900 p-2"
          placeholder="password"
          autoComplete="current-password"
          required
        />
        <input
          type="text"
          inputMode="numeric"
          value={totp}
          onChange={(e) => setTotp(e.target.value)}
          className="w-full rounded bg-neutral-900 p-2 font-mono"
          placeholder="2FA code"
          autoComplete="one-time-code"
          required
        />
        <ErrorText msg={error} />
        <button type="submit" className="w-full rounded bg-blue-700 px-4 py-2">
          Sign in
        </button>
      </form>
    </div>
  );
}

export default function App() {
  const [hasToken, setHasToken] = useState(() => Boolean(getToken()));
  const [page, setPage] = useState<Page>("Dashboard");

  if (!hasToken) {
    return <LoginGate onSet={() => setHasToken(true)} />;
  }

  async function logout() {
    try {
      await api.authLogout();
    } catch {
      // token already invalid is fine
    }
    clearToken();
    setHasToken(false);
  }

  return (
    <div className="min-h-screen">
      <nav className="flex items-center justify-between border-b border-neutral-800 p-4">
        <div className="flex gap-4">
          {PAGES.map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={p === page ? "font-semibold text-white" : "text-neutral-400"}
            >
              {p}
            </button>
          ))}
        </div>
        <button
          onClick={logout}
          className="text-sm text-neutral-400 hover:text-red-400"
        >
          Log out
        </button>
      </nav>
      <main className="p-4">
        {page === "Dashboard" && <Dashboard />}
        {page === "Devices" && <Devices />}
        {page === "Observations" && <Observations />}
        {page === "LTE Cells" && <LteCells />}
        {page === "Alerts" && <Alerts />}
        {page === "Known Devices" && <KnownDevices />}
      </main>
    </div>
  );
}
