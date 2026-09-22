import { useEffect, useState } from "react";
import { api, type LteCell } from "../api";

export function LteCells() {
  const [limit, setLimit] = useState(50);
  const [cells, setCells] = useState<LteCell[]>([]);
  const [error, setError] = useState("");

  function refresh() {
    api.lteCells(limit).then(setCells).catch((e) => setError(String(e)));
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
            <th className="p-2">Freq (MHz)</th>
            <th className="p-2">EARFCN</th>
            <th className="p-2">Band</th>
            <th className="p-2">PCI</th>
            <th className="p-2">Signal</th>
          </tr>
        </thead>
        <tbody>
          {cells.map((c) => (
            <tr key={c.id} className="border-b border-neutral-900">
              <td className="p-2">{c.observed_at}</td>
              <td className="p-2">{c.device_name ?? c.device_id}</td>
              <td className="p-2 font-mono">{c.freq_mhz?.toFixed(2) ?? "?"}</td>
              <td className="p-2 font-mono">{c.earfcn ?? "?"}</td>
              <td className="p-2">{c.band ?? "?"}</td>
              <td className="p-2 font-mono">{c.pci ?? "—"}</td>
              <td className="p-2">{c.signal_dbm ?? "?"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}