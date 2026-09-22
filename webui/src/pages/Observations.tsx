import { useEffect, useState } from "react";
import { api, type Observation } from "../api";

export function Observations() {
  const [limit, setLimit] = useState(50);
  const [hideKnown, setHideKnown] = useState(false);
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
        <label className="flex items-center gap-2 text-sm text-neutral-400">
          <input
            type="checkbox"
            checked={hideKnown}
            onChange={(e) => setHideKnown(e.target.checked)}
          />
          Hide known
        </label>
      </div>

      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-neutral-800">
            <th className="p-2">Time</th>
            <th className="p-2">Device</th>
            <th className="p-2">IMSI</th>
            <th className="p-2">TMSI</th>
            <th className="p-2">MCC/MNC</th>
            <th className="p-2">Country</th>
            <th className="p-2">Brand</th>
            <th className="p-2">Operator</th>
            <th className="p-2">Signal</th>
          </tr>
        </thead>
        <tbody>
          {observations
            .filter((o) => !(hideKnown && o.known))
            .map((o) => (
            <tr key={o.id} className="border-b border-neutral-900">
              <td className="p-2">{o.observed_at}</td>
              <td className="p-2">{o.device_name ?? o.device_id}</td>
              <td className="p-2 font-mono">{o.imsi ?? o.imsi_masked}
                {o.known && <span className="ml-2 rounded bg-green-900 px-1.5 py-0.5 text-xs text-green-300">{o.known}</span>}
              </td>
              <td className="p-2 font-mono">
                {o.tmsi1 ? (o.tmsi2 && o.tmsi2 !== o.tmsi1 ? `${o.tmsi1} → ${o.tmsi2}` : o.tmsi1) : "?"}
              </td>
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
