/**
 * HTTP API Server for Pi Device Communication
 * Runs alongside the main Vite/Convex app to handle:
 * - Device registration
 * - Heartbeat
 * - Raw GSM observations
 */
import http from "http";
import { ConvexHttpClient } from "convex/browser";
import { api } from "./convex/_generated/api";

const PORT = parseInt(process.env.PORT || "3001", 10);
const CONVEX_URL = process.env.VITE_CONVEX_URL || "http://127.0.0.1:3210";

const convex = new ConvexHttpClient(CONVEX_URL);

async function handleRequest(req: http.IncomingMessage, res: http.ServerResponse) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  let body = "";
  req.on("data", (chunk: string) => (body += chunk));
  req.on("end", async () => {
    try {
      const url = new URL(req.url || "/", `http://${req.headers.host}`);
      const data = body ? JSON.parse(body) : {};

      console.log(`[${req.method}] ${url.pathname}`);

      switch (url.pathname) {
        case "/api/devices/register": {
          const deviceId = await convex.mutation(api.devices.register, {
            name: data.name,
            lat: data.lat,
            lng: data.lng,
            altitude: data.altitude,
            firmwareVersion: data.firmware_version || data.firmwareVersion,
          });
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ deviceId, status: "registered" }));
          break;
        }

        case "/api/devices/heartbeat": {
          await convex.mutation(api.devices.heartbeat, {
            deviceId: data.deviceId,
          });
          res.writeHead(200);
          res.end(JSON.stringify({ status: "ok" }));
          break;
        }

        case "/api/observations/raw": {
          // Receives raw GSM frame data, records observation
          console.log("Raw GSM frame received", data);
          res.writeHead(200);
          res.end(JSON.stringify({ status: "received" }));
          break;
        }

        case "/api/observations/imsi": {
          const obsId = await convex.mutation(api.observations.recordObservation, {
            deviceId: data.deviceId,
            sensorId: data.sensorId,
            imsi: data.imsi,
            tmsi1: data.tmsi1,
            tmsi2: data.tmsi2,
            mcc: data.mcc,
            mnc: data.mnc,
            lac: data.lac,
            cellId: data.cellId,
            country: data.country,
            brand: data.brand,
            operator: data.operator,
            signalDbm: data.signalDbm,
            arfcn: data.arfcn,
            frequency: data.frequency,
          });
          res.writeHead(200);
          res.end(JSON.stringify({ observationId: obsId }));
          break;
        }

        case "/api/health": {
          res.writeHead(200);
          res.end(JSON.stringify({ status: "ok", timestamp: Date.now() }));
          break;
        }

        default: {
          res.writeHead(404);
          res.end(JSON.stringify({ error: "Not found" }));
        }
      }
    } catch (err: any) {
      console.error("API Error:", err);
      res.writeHead(500);
      res.end(JSON.stringify({ error: err.message || "Internal error" }));
    }
  });
}

const server = http.createServer(handleRequest);

server.listen(PORT, "0.0.0.0", () => {
  console.log(`[IMSI API Server] Running on http://0.0.0.0:${PORT}`);
  console.log(`[IMSI API Server] Convex URL: ${CONVEX_URL}`);
});