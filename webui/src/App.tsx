import { useState } from "react";
import { clearToken, getToken, setToken } from "./api";
import { Alerts } from "./pages/Alerts";
import { Dashboard } from "./pages/Dashboard";
import { Devices } from "./pages/Devices";
import { LteCells } from "./pages/LteCells";
import { Observations } from "./pages/Observations";

const PAGES = ["Dashboard", "Devices", "Observations", "LTE Cells", "Alerts"] as const;
type Page = (typeof PAGES)[number];

function TokenGate({ onSet }: { onSet: () => void }) {
  const [value, setValue] = useState("");
  return (
    <div className="flex min-h-screen items-center justify-center">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setToken(value);
          onSet();
        }}
        className="w-96 space-y-3 rounded border border-neutral-800 p-6"
      >
        <h1 className="text-lg font-semibold">Scorpion</h1>
        <p className="text-sm text-neutral-400">Enter a device or provisioning token.</p>
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-full rounded bg-neutral-900 p-2"
          placeholder="token"
          required
        />
        <button type="submit" className="w-full rounded bg-blue-700 px-4 py-2">
          Continue
        </button>
      </form>
    </div>
  );
}

export default function App() {
  const [hasToken, setHasToken] = useState(() => Boolean(getToken()));
  const [page, setPage] = useState<Page>("Dashboard");

  if (!hasToken) {
    return <TokenGate onSet={() => setHasToken(true)} />;
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
          onClick={() => {
            clearToken();
            setHasToken(false);
          }}
          className="text-sm text-neutral-400 hover:text-red-400"
        >
          Clear token
        </button>
      </nav>
      <main className="p-4">
        {page === "Dashboard" && <Dashboard />}
        {page === "Devices" && <Devices />}
        {page === "Observations" && <Observations />}
        {page === "LTE Cells" && <LteCells />}
        {page === "Alerts" && <Alerts />}
      </main>
    </div>
  );
}
