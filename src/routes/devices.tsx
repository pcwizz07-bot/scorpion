import { createFileRoute } from '@tanstack/react-router'
import { useSuspenseQuery } from '@tanstack/react-query'
import { convexQuery } from '@convex-dev/react-query'
import { api } from '../../convex/_generated/api'

export const Route = createFileRoute('/devices')({
  head: () => ({ meta: [{ title: 'Devices - IMSI Catcher' }] }),
  component: DevicesPage,
})

function DevicesPage() {
  const { data: devices } = useSuspenseQuery(
    convexQuery(api.devices.list, {}),
  )

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <a href="/" className="flex items-center gap-2 text-gray-400 hover:text-white">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Dashboard
            </a>
            <div className="h-6 w-px bg-gray-700" />
            <h1 className="text-lg font-bold">Deployed Devices</h1>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        <div className="grid gap-6 md:grid-cols-3">
          {devices.map((device: any) => (
            <div key={device._id} className="rounded-xl border border-gray-700 bg-gray-800/50 p-6 backdrop-blur-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold">{device.name}</h2>
                <span className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs ${
                  device.status === 'online' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                }`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${device.status === 'online' ? 'bg-green-400' : 'bg-red-400'}`} />
                  {device.status}
                </span>
              </div>
              <div className="space-y-2 text-sm text-gray-400">
                <div className="flex justify-between">
                  <span>Latitude</span>
                  <span className="font-mono text-white">{device.location.lat.toFixed(6)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Longitude</span>
                  <span className="font-mono text-white">{device.location.lng.toFixed(6)}</span>
                </div>
                {device.altitude && (
                  <div className="flex justify-between">
                    <span>Altitude</span>
                    <span className="text-white">{device.altitude}m</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Last Seen</span>
                  <span className="text-white">{new Date(device.lastSeen).toLocaleString()}</span>
                </div>
                {device.firmwareVersion && (
                  <div className="flex justify-between">
                    <span>Firmware</span>
                    <span className="text-white">{device.firmwareVersion}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
          {devices.length === 0 && (
            <div className="col-span-3 text-center py-20 text-gray-500">
              <p className="text-lg">No devices deployed yet</p>
              <p className="text-sm mt-2">Run the deployment script on a Raspberry Pi to register it</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}