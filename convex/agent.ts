"use node";

import { Agent, createTool } from "@convex-dev/agent";
import { api, components } from "./_generated/api";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { z } from "zod";

const OLLAMA_HOST = process.env.OLLAMA_HOST || "http://10.10.20.118:11434";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || "qwen2.5-coder:7b";

const ollama = createOpenRouter({
  baseURL: `${OLLAMA_HOST}/v1`,
  apiKey: "ollama",
  compatibility: "compatible",
});

export const investigatorAgent = new Agent(components.agent, {
  name: "Dungbeetle AI Investigator",
  instructions: `You are an AI anti-poaching intelligence analyst for the Dungbeetle IMSI surveillance network. 
You help rangers analyze IMSI data captured by 3 Raspberry Pi devices with RTL-SDR dongles deployed across a wildlife reserve.

You have tools to query the database for device locations, IMSI observations, triangulated positions, alerts, and tracking data.

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
        const devices = await ctx.runQuery(api.devices.getDeployedLocations);
        return JSON.stringify(devices);
      },
    }),
    getRecentObservations: createTool({
      description: "Get recent IMSI observations",
      args: z.object({ limit: z.number().optional().default(50) }),
      handler: async (ctx, args): Promise<string> => {
        const obs = await ctx.runQuery(api.observations.getRecent, { limit: args.limit });
        return JSON.stringify(obs);
      },
    }),
    getActiveTrackedImsis: createTool({
      description: "Get all actively tracked IMSIs",
      args: z.object({}),
      handler: async (ctx): Promise<string> => {
        const tracked = await ctx.runQuery(api.tracking.getActive);
        return JSON.stringify(tracked);
      },
    }),
    getTriangulations: createTool({
      description: "Get all triangulated positions",
      args: z.object({}),
      handler: async (ctx): Promise<string> => {
        const tris = await ctx.runQuery(api.triangulation.getActivePositions);
        return JSON.stringify(tris);
      },
    }),
    getAlerts: createTool({
      description: "Get unresolved alerts",
      args: z.object({ severity: z.string().optional() }),
      handler: async (ctx, args): Promise<string> => {
        const alerts = await ctx.runQuery(api.alerts.getUnresolved);
        if (args.severity) return JSON.stringify(alerts.filter((a: any) => a.severity === args.severity));
        return JSON.stringify(alerts);
      },
    }),
    getImsiHistory: createTool({
      description: "Get observation history for a specific IMSI",
      args: z.object({ imsi: z.string() }),
      handler: async (ctx, args): Promise<string> => {
        const obs = await ctx.runQuery(api.observations.getRecent, { limit: 50 });
        return JSON.stringify(obs.filter((o: any) => o.imsi.includes(args.imsi)));
      },
    }),
  },
});