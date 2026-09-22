import { useEffect, useState } from "react";
import { api, type KnownIdentity } from "../api";

export function KnownDevices() {
  const [rows, setRows] = useState<KnownIdentity[]>([]);
  const [kind, setKind] = useState("imsi");
  const [value, setValue] = useState("");
  const [label, setLabel] = useState("");
  const [isOwn, setIsOwn] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  function refresh() {
    api.known().then(setRows).catch((e) => setError(String(e)));
  }

  useEffect(refresh, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setNotice("");
    setError("");
    try {
      await api.knownCreate({ kind, value, label, is_own: isOwn });
      setValue("");
      setLabel("");
      setIsOwn(false);
      refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  async function remove(id: number) {
    setError("");
    try {
      await api.knownDelete(id);
      refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="space-y-4">
      {error && <p className="text-red-400">{error}</p>}
      {notice && <p className="text-green-400">{notice}</p>}

      <form onSubmit={add} className="flex flex-wrap items-end gap-2">
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          className="rounded bg-neutral-900 p-2"
        >
          <option value="imsi">imsi</option>
          <option value="imei">imei</option>
          <option value="imeisv">imeisv</option>
        </select>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="rounded bg-neutral-900 p-2 font-mono"
          placeholder="IMSI / IMEI value"
          required
        />
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="rounded bg-neutral-900 p-2"
          placeholder="label (e.g. Francois phone)"
          required
        />
        <label className="flex items-center gap-2 text-sm text-neutral-400">
          <input type="checkbox" checked={isOwn} onChange={(e) => setIsOwn(e.target.checked)} />
          Own device
        </label>
        <button type="submit" className="rounded bg-blue-700 px-4 py-2">
          Add
        </button>
      </form>

      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-neutral-800">
            <th className="p-2">Kind</th>
            <th className="p-2">Label</th>
            <th className="p-2">Own</th>
            <th className="p-2">Added</th>
            <th className="p-2"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-neutral-900">
              <td className="p-2 font-mono">{r.kind}</td>
              <td className="p-2">{r.label}</td>
              <td className="p-2">{r.is_own ? "yes" : "no"}</td>
              <td className="p-2">{r.created_at}</td>
              <td className="p-2">
                <button onClick={() => remove(r.id)} className="rounded bg-red-900 px-2 py-1 text-xs">
                  remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-neutral-500">
        Only hashes are stored — the raw IMSI/IMEI never touches the database.
      </p>
    </div>
  );
}