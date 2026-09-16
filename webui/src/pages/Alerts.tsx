import { useEffect, useState } from "react";
import { api, type Alert } from "../api";

export function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState("");

  function refresh() {
    api.alerts(50).then(setAlerts).catch((e) => setError(String(e)));
  }

  useEffect(refresh, []);

  return (
    <div className="space-y-4">
      {error && <p className="text-red-400">{error}</p>}
      <button onClick={refresh} className="rounded bg-blue-700 px-4 py-2">
        Refresh
      </button>

      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-neutral-800">
            <th className="p-2">Time</th>
            <th className="p-2">Severity</th>
            <th className="p-2">Title</th>
            <th className="p-2">Message</th>
            <th className="p-2">IMSI</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a) => (
            <tr key={a.id} className="border-b border-neutral-900">
              <td className="p-2">{a.created_at}</td>
              <td className="p-2">{a.severity}</td>
              <td className="p-2">{a.title}</td>
              <td className="p-2">{a.message ?? ""}</td>
              <td className="p-2 font-mono">{a.imsi_masked ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
