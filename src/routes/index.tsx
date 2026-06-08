import { createFileRoute } from '@tanstack/react-router'
import { useSuspenseQuery } from '@tanstack/react-query'
import { convexQuery } from '@convex-dev/react-query'
import { useMutation } from 'convex/react'
import { api } from '../../convex/_generated/api'
import { useState } from 'react'

export const Route = createFileRoute('/')({
  head: () => ({ meta: [{ title: 'IMSI Catcher - Anti-Poaching Dashboard' }] }),
  component: Home,
})

function StatCard({ label, value, color = 'text-blue-400' }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4 backdrop-blur-sm">
      <p className="text-sm text-gray-400">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

function DeviceMap() {
  const { data: devices } = useSuspenseQuery(
    convexQuery(api.devices.getDeployedLocations, {}),
  )

  // Simple CSS-based map representation
  const minLat = devices.length > 0 ? Math.min(...devices.map((d: any) => d.lat)) - 0.01 : -1;
  const maxLat = devices.length > 0 ? Math.max(...devices.map((d: any) => d.lat)) + 0.01 : -1;
  const minLng = devices.length > 0 ? Math.min(...devices.map((d: any) => d.lng)) - 0.01 : -1;
  const maxLng = devices.length > 0 ? Math.max(...devices.map((d: any) => d.lng)) + 0.01 : -1;

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4 backdrop-blur-sm">
      <h3 className="mb-3 text-lg font-semibold text-white">Deployment Map</h3>
      <div className="relative h-64 w-full rounded-lg bg-gray-900">
        {/* Grid background */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.05)_1px,transparent_1px)] bg-[length:40px_40px]" />
        {/* Device markers */}
        {devices.map((device: any, i: number) => {
          // Normalize position within the container
          const x = device.lng && minLng !== maxLng 
            ? ((device.lng - minLng) / (maxLng - minLng)) * 80 + 10 
            : 10 + i * 30;
          const y = device.lat && minLat !== maxLat
            ? ((maxLat - device.lat) / (maxLat - minLat)) * 80 + 10
            : 10 + i * 20;

          return (
            <div
              key={device._id}
              className="absolute flex flex-col items-center transition-all duration-500"
              style={{ left: `${x}%`, top: `${y}%` }}
            >
              <div
                className={`h-4 w-4 rounded-full ${
                  device.status === 'online'
                    ? 'bg-green-500 shadow-lg shadow-green-500/50'
                    : device.status === 'warning'
                      ? 'bg-yellow-500 shadow-lg shadow-yellow-500/50'
                      : 'bg-red-500 shadow-lg shadow-red-500/50'
                }`}
              />
              <span className="mt-1 whitespace-nowrap text-xs text-gray-400">
                {device.name}
              </span>
            </div>
          )
        })}
        {/* Reserve boundary placeholder */}
        <div className="absolute inset-4 rounded-lg border-2 border-dashed border-green-700/30">
          <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-sm text-green-700/40">
            Reserve Boundary
          </span>
        </div>
      </div>
    </div>
  )
}

function LiveFeed() {
  const { data: observations } = useSuspenseQuery(
    convexQuery(api.observations.getRecent, { limit: 10 }),
  )

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4 backdrop-blur-sm">
      <h3 className="mb-3 text-lg font-semibold text-white">Live IMSI Feed</h3>
      <div className="space-y-2">
        {observations.length === 0 ? (
          <p className="text-sm text-gray-500">No observations yet. Waiting for data...</p>
        ) : (
          observations.map((obs: any) => (
            <div
              key={obs._id}
              className="flex items-center justify-between rounded-lg bg-gray-900/50 p-2 text-sm"
            >
              <div className="flex items-center gap-3">
                <span className="h-2 w-2 rounded-full bg-green-400" />
                <span className="font-mono text-xs text-green-400">
                  {obs.imsi.slice(0, 12)}...
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span>{obs.country || '??'}</span>
                <span>{obs.brand || '??'}</span>
                <span>{obs.signalDbm ?? '?'} dBm</span>
                <span>{new Date(obs.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function AlertsPanel() {
  const { data: alerts } = useSuspenseQuery(
    convexQuery(api.alerts.getUnresolved, {}),
  )

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4 backdrop-blur-sm">
      <h3 className="mb-3 text-lg font-semibold text-white">Active Alerts</h3>
      <div className="space-y-2">
        {alerts.length === 0 ? (
          <p className="text-sm text-gray-500">No active alerts</p>
        ) : (
          alerts.map((alert: any) => (
            <div
              key={alert._id}
              className={`rounded-lg border-l-4 p-3 text-sm ${
                alert.severity === 'critical'
                  ? 'border-red-500 bg-red-900/20'
                  : alert.severity === 'warning'
                    ? 'border-yellow-500 bg-yellow-900/20'
                    : 'border-blue-500 bg-blue-900/20'
              }`}
            >
              <p className="font-medium text-white">{alert.title}</p>
              <p className="mt-1 text-xs text-gray-400">{alert.message}</p>
              <p className="mt-1 text-xs text-gray-500">
                {new Date(alert.timestamp).toLocaleString()}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function TriangulationPanel() {
  const { data: positions } = useSuspenseQuery(
    convexQuery(api.triangulation.getActivePositions, {}),
  )

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4 backdrop-blur-sm">
      <h3 className="mb-3 text-lg font-semibold text-white">Triangulated Positions</h3>
      <div className="space-y-2">
        {positions.length === 0 ? (
          <p className="text-sm text-gray-500">No active triangulations</p>
        ) : (
          positions.map((pos: any) => (
            <div
              key={pos._id}
              className="flex items-center justify-between rounded-lg bg-gray-900/50 p-2 text-sm"
            >
              <div>
                <span className="font-mono text-xs text-purple-400">
                  {pos.imsi.slice(0, 12)}...
                </span>
              </div>
              <div className="text-right text-xs text-gray-400">
                <p>
                  {pos.lat.toFixed(4)}, {pos.lng.toFixed(4)}
                </p>
                <p>±{pos.accuracy}m · {(pos.confidence * 100).toFixed(0)}%</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function AIInvestigatorButton() {
  const [analyzing, setAnalyzing] = useState(false)

  const handleAnalyze = async () => {
    setAnalyzing(true)
    // Navigate to AI investigator page
    window.location.href = '/ai-investigator'
  }

  return (
    <button
      onClick={handleAnalyze}
      className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-purple-600/30 transition-all hover:from-purple-500 hover:to-blue-500"
    >
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
      AI Investigator
    </button>
  )
}

function Home() {
  const { data: stats } = useSuspenseQuery(
    convexQuery(api.observations.getStats, {}),
  )
  const { data: onlineCount } = useSuspenseQuery(
    convexQuery(api.devices.getOnlineCount, {}),
  )
  const { data: alertStats } = useSuspenseQuery(
    convexQuery(api.alerts.getAlertStats, {}),
  )

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-red-600 to-orange-600 text-sm font-bold">
              IMSI
            </div>
            <div>
              <h1 className="text-lg font-bold">IMSI Catcher</h1>
              <p className="text-xs text-gray-400">Anti-Poaching Surveillance Network</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="h-2 w-2 rounded-full bg-green-400" />
              <span className="text-gray-400">{onlineCount} devices online</span>
            </div>
            <AIInvestigatorButton />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-6 py-6">
        {/* Stats Grid */}
        <div className="mb-6 grid grid-cols-4 gap-4">
          <StatCard
            label="Total Observations"
            value={stats.totalObservations.toLocaleString()}
            color="text-blue-400"
          />
          <StatCard
            label="Unique IMSIs"
            value={stats.uniqueImsis}
            color="text-purple-400"
          />
          <StatCard
            label="Countries Detected"
            value={stats.uniqueCountries}
            color="text-green-400"
          />
          <StatCard
            label="Active Alerts"
            value={alertStats.unresolved}
            color={alertStats.critical > 0 ? 'text-red-400' : 'text-yellow-400'}
          />
        </div>

        {/* Two column layout */}
        <div className="mb-6 grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-6">
            <DeviceMap />
            <div className="grid grid-cols-2 gap-6">
              <LiveFeed />
              <TriangulationPanel />
            </div>
          </div>
          <div>
            <AlertsPanel />
          </div>
        </div>

        {/* System Status Footer */}
        <div className="rounded-xl border border-gray-800 bg-gray-900/30 p-4">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <span>System Status</span>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-green-400" />
                Convex Backend Online
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-green-400" />
                Real-time Sync Active
              </span>
              <span className="text-xs">
                Last updated: {new Date().toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}