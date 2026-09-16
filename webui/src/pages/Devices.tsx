import { useEffect, useState } from "react";
import { api, type Device } from "../api";

export function Devices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [registered, setRegistered] = useState<{ device_id: string; device_token: string } | null>(null);

  function refresh() {
    api.devices().then(setDevices).catch((e) => setError(String(e)));
  }

  useEffect(refresh, []);

  async function onRegister(e: React.FormEvent) {
    e.preventDefault();
    try {
      const result = await api.registerDevice({ name, lat: Number(lat), lng: Number(lng) });
      setRegistered(result);
      refresh();
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="space-y-6">
      {error && <p className="text-red-400">{error}</p>}

      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-neutral-800">
            <th className="p-2">Name</th>
            <th className="p-2">Status</th>
            <th className="p-2">Last seen</th>
            <th className="p-2">Lat</th>
            <th className="p-2">Lng</th>
          </tr>
        </thead>
        <tbody>
          {devices.map((d) => (
            <tr key={d.id} className="border-b border-neutral-900">
              <td className="p-2">{d.name}</td>
              <td className="p-2">{d.status}</td>
              <td className="p-2">{d.last_seen}</td>
              <td className="p-2">{d.lat}</td>
              <td className="p-2">{d.lng}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <form onSubmit={onRegister} className="flex flex-wrap items-end gap-2 rounded border border-neutral-800 p-4">
        <div>
          <label className="block text-xs text-neutral-400">Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} className="rounded bg-neutral-900 p-2" required />
        </div>
        <div>
          <label className="block text-xs text-neutral-400">Lat</label>
          <input value={lat} onChange={(e) => setLat(e.target.value)} className="w-24 rounded bg-neutral-900 p-2" required />
        </div>
        <div>
          <label className="block text-xs text-neutral-400">Lng</label>
          <input value={lng} onChange={(e) => setLng(e.target.value)} className="w-24 rounded bg-neutral-900 p-2" required />
        </div>
        <button type="submit" className="rounded bg-blue-700 px-4 py-2">
          Register
        </button>
      </form>

      {registered && (
        <div className="rounded border border-green-800 p-4 text-sm">
          <p>Device registered. Save this token — it will not be shown again:</p>
          <p className="mt-1 break-all font-mono text-green-400">{registered.device_token}</p>
        </div>
      )}
    </div>
  );
}
