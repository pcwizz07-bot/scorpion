const TOKEN_KEY = "scorpion_token";
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Device-Token": getToken(),
      "X-Provisioning-Token": getToken(),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type Health = { status: string; version: string };

export type Device = {
  id: string;
  name: string;
  lat: number;
  lng: number;
  status: string;
  last_seen: string;
};

export type Observation = {
  id: number;
  device_id: string;
  imsi_masked: string;
  mcc: string | null;
  mnc: string | null;
  lac: number | null;
  cell_id: number | null;
  country: string | null;
  brand: string | null;
  operator: string | null;
  ts: string;
};

export type Alert = {
  id: number;
  device_id: string | null;
  imsi_masked: string | null;
  title: string;
  severity: string;
  message: string | null;
  created_at: string;
};

export const api = {
  health: () => request<Health>("/health"),
  devices: () => request<Device[]>("/devices"),
  registerDevice: (body: { name: string; lat: number; lng: number }) =>
    request<{ device_id: string; device_token: string }>("/devices/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  observations: (limit: number) => request<Observation[]>(`/observations?limit=${limit}`),
  alerts: (limit: number) => request<Alert[]>(`/alerts?limit=${limit}`),
};
