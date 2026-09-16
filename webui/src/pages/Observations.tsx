import { useEffect, useState } from "react";
import { api, type Observation } from "../api";

export function Observations() {
  const [limit, setLimit] = useState(50);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [error, setError] = useState("");

  function refresh() {
    api.observations(limit).then(setObservations).catch((e) => setError(String(e)));
  }

  useEffect(refresh, [limit]);

  return (
    <div className="space-y-4">
      {error && <p className="text-red-400">{error}</p>}
      <div className="flex items-center gap-2">
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="rounded bg-neutral-900 p-2"
        >
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
        <button onClick={refresh} className="rounded bg-blue-700 px-4 py-2">
          Refresh
        </button>
      </div>

      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-neutral-800">
            <th className="p-2">Time</th>
            <th className="p-2">Device</th>
            <th className="p-2">IMSI</th>
            <th className="p-2">MCC/MNC</th>
            <th className="p-2">Country</th>
            <th className="p-2">Brand</th>
            <th className="p-2">Operator</th>
            <th className="p-2">Signal</th>
          </tr>
        </thead>
        <tbody>
          {observations.map((o) => (
            <tr key={o.id} className="border-b border-neutral-900">
              <td className="p-2">{o.observed_at}</td>
              <td className="p-2">{o.device_name ?? o.device_id}</td>
              <td className="p-2 font-mono">{o.imsi_masked}</td>
              <td className="p-2">
                {o.mcc ?? "?"}/{o.mnc ?? "?"}
              </td>
              <td className="p-2">{o.country ?? "?"}</td>
              <td className="p-2">{o.brand ?? "?"}</td>
              <td className="p-2">{o.operator ?? "?"}</td>
              <td className="p-2">{o.signal_dbm ?? "?"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
