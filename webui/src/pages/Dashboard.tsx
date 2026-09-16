import { useEffect, useState } from "react";
import { api, type Alert, type Health, type Observation } from "../api";

export function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.health(), api.observations(10), api.alerts(10)])
      .then(([h, obs, al]) => {
        setHealth(h);
        setObservations(obs);
        setAlerts(al);
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="space-y-6">
      {error && <p className="text-red-400">{error}</p>}
      <div className="rounded border border-neutral-800 p-4">
        <h2 className="mb-2 font-semibold">Health</h2>
        <p>{health ? `${health.status} (v${health.version})` : "loading..."}</p>
      </div>

      <div className="rounded border border-neutral-800 p-4">
        <h2 className="mb-2 font-semibold">Recent observations ({observations.length})</h2>
        <ul className="space-y-1 text-sm">
          {observations.map((o) => (
            <li key={o.id} className="text-neutral-300">
              {o.ts} — {o.imsi_masked} — {o.country ?? "?"} / {o.brand ?? "?"}
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded border border-neutral-800 p-4">
        <h2 className="mb-2 font-semibold">Recent alerts ({alerts.length})</h2>
        <ul className="space-y-1 text-sm">
          {alerts.map((a) => (
            <li key={a.id} className="text-neutral-300">
              {a.created_at} — [{a.severity}] {a.title}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
