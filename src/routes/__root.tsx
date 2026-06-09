import { Outlet, createRootRouteWithContext } from '@tanstack/react-router'
import * as React from 'react'
import type { QueryClient } from '@tanstack/react-query'

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient
}>()({
  notFoundComponent: () => <div>Route not found</div>,
  component: () => (
    <html>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Dungbeetle - IMSI Surveillance</title>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body><Outlet /></body>
    </html>
  ),
})