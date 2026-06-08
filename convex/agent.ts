"use node";

import { Agent, createTool } from "@convex-dev/agent";
import { components } from "./_generated/api";
import { createOpenAI } from "@ai-sdk/openai";
import { z } from "zod";

const OLLAMA_HOST = process.env.OLLAMA_HOST || "http://10.10.20.118:11434";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || "qwen2.5-coder:7b";

const ollama = createOpenAI({
  baseURL: `${OLLAMA_HOST}/v1/`,
  apiKey: "ollama", // Ollama doesn't need a real key, but the SDK requires one
});

export const investigatorAgent = new Agent(components.agent, {
  name: "Dungbeetle AI Investigator",
  instructions: `You are an AI anti-poaching intelligence analyst for the Dungbeetle IMSI surveillance network. 
You help rangers analyze IMSI (International Mobile Subscriber Identity) data captured by 3 Raspberry Pi 
devices with RTL-SDR dongles deployed across a wildlife reserve.

You have tools to query the database for device locations, IMSI observations, triangulated positions, 
alerts, and tracking data.

When analyzing data:
1. Identify unusual patterns - phones at unusual hours, new IMSIs
2. Correlate sightings across Pi devices for triangulation
3. Flag suspicious IMSIs and provide actionable intelligence
4. Estimate confidence levels for assessments

Always consider reserve boundaries, normal vs suspicious movements, and time patterns (poaching often at dawn/dusk).`,
  languageModel: ollama.chat(OLLAMA_MODEL),
  maxSteps: 5,
  tools: {
    getDeviceStatus: createTool({
      description: "Get the status and location of all deployed Pi devices",
      args: z.object({}),
      handler: async (ctx): Promise<string> => {
        const devices = await ctx.db.query("devices").collect();
        return JSON.stringify(devices.map((d) => ({ name: d.name, status: d.status, location: d.location, lastSeen: new Date(d.lastSeen).toISOString() })));
      },
    }),
    getRecentObservations: createTool({
      description: "Get recent IMSI observations",
      args: z.object({ limit: z.number().optional().default(50) }),
      handler: async (ctx, args): Promise<string> => {
        const obs = await ctx.db.query("imsiObservations").withIndex("by_timestamp", (q) => q).order("desc").take(args.limit ?? 50);
        return JSON.stringify(obs.map((o) => ({ imsi: o.imsi, country: o.country, brand: o.brand, signalDbm: o.signalDbm, deviceId: o.deviceId, timestamp: new Date(o.timestamp).toISOString() })));
      },
    }),
    getActiveTrackedImsis: createTool({
      description: "Get all actively tracked IMSIs",
      args: z.object({}),
      handler: async (ctx): Promise<string> => {
        const tracked = await ctx.db.query("trackedImsis").withIndex("by_active", (q) => q.eq("isActive", true)).collect();
        return JSON.stringify(tracked.map((t) => ({ imsi: t.imsi, riskLevel: t.riskLevel, firstSeen: new Date(t.firstSeen).toISOString(), lastSeen: new Date(t.lastSeen).toISOString() })));
      },
    }),
    getTriangulations: createTool({
      description: "Get all triangulated positions",
      args: z.object({}),
      handler: async (ctx): Promise<string> => {
        const tris = await ctx.db.query("triangulations").collect();
        return JSON.stringify(tris.map((t) => ({ imsi: t.imsi, position: t.position, accuracy: t.accuracy, confidence: t.confidence, lastSeen: new Date(t.lastSeen).toISOString() })));
      },
    }),
    getAlerts: createTool({
      description: "Get unresolved alerts",
      args: z.object({ severity: z.string().optional() }),
      handler: async (ctx, args): Promise<string> => {
        let alerts = await ctx.db.query("alerts").withIndex("by_resolved", (q) => q.eq("resolved", false)).order("desc").collect();
        if (args.severity) alerts = alerts.filter((a) => a.severity === args.severity);
        return JSON.stringify(alerts.map((a) => ({ type: a.type, severity: a.severity, title: a.title, imsi: a.imsi, timestamp: new Date(a.timestamp).toISOString() })));
      },
    }),
    getImsiHistory: createTool({
      description: "Get observation history for a specific IMSI",
      args: z.object({ imsi: z.string() }),
      handler: async (ctx, args): Promise<string> => {
        const obs = await ctx.db.query("imsiObservations").withIndex("by_imsi", (q) => q.eq("imsi", args.imsi)).order("desc").take(50);
        return JSON.stringify(obs.map((o) => ({ deviceId: o.deviceId, signalDbm: o.signalDbm, country: o.country, brand: o.brand, timestamp: new Date(o.timestamp).toISOString() })));
      },
    }),
  },
});