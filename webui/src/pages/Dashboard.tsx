import { useEffect, useState } from "react";
import { api, type Alert, type Health, type Stats } from "../api";

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded border border-neutral-800 p-4">
      <p className="text-xs text-neutral-400">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}

export function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.health(), api.stats(), api.alerts(10)])
      .then(([h, s, al]) => {
        setHealth(h);
        setStats(s);
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

      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Devices total" value={stats.devices_total} />
          <StatCard label="Devices online" value={stats.devices_online} />
          <StatCard label="Observations total" value={stats.observations_total} />
          <StatCard label="Observations (24h)" value={stats.observations_last_24h} />
          <StatCard label="Unique IMSIs" value={stats.unique_imsis} />
          <StatCard label="Tracked active" value={stats.tracked_active} />
          <StatCard label="Alerts total" value={stats.alerts_total} />
          <StatCard label="Alerts open" value={stats.alerts_open} />
        </div>
      )}

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
