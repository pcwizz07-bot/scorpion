import { query, mutation } from "./_generated/server";
import { v } from "convex/values";
import type { Doc, Id } from "./_generated/dataModel";

/**
 * Compute triangulation from multiple device observations of the same IMSI.
 * Uses signal strength and known device locations to estimate position.
 */

export const compute = mutation({
  args: {
    imsi: v.string(),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    // Get observations for this IMSI from the last 5 minutes
    const fiveMinAgo = Date.now() - 300000;
    const observations = await ctx.db
      .query("imsiObservations")
      .withIndex("by_imsi", (q) => q.eq("imsi", args.imsi))
      .collect();

    const recentObs = observations.filter((o) => o.timestamp > fiveMinAgo);

    if (recentObs.length < 2) {
      return null; // Need at least 2 observations for triangulation
    }

    // Group observations by device
    const deviceObs: Record<string, typeof recentObs> = {};
    for (const obs of recentObs) {
      const key = obs.deviceId;
      if (!deviceObs[key]) deviceObs[key] = [];
      deviceObs[key].push(obs);
    }

    const deviceIds = Object.keys(deviceObs);
    if (deviceIds.length < 2) return null; // Need at least 2 different devices

    // Get device locations
    const deviceDocs = [];
    for (const id of deviceIds) {
      const doc = await ctx.db.get(id as any);
      if (doc && "location" in doc && "name" in doc) {
        deviceDocs.push(doc as any);
      }
    }

    if (deviceDocs.length < 2) return null;

    // Simple centroid-based triangulation using signal strength as weight
    let totalWeight = 0;
    let latSum = 0;
    let lngSum = 0;

    for (const device of deviceDocs) {
      const obsForDevice = deviceObs[device._id] || [];
      const avgSignal = obsForDevice.reduce(
        (sum: number, o: any) => sum + (o.signalDbm || -100),
        0,
      ) / obsForDevice.length;

      // Better signal = closer = higher weight
      const weight = Math.pow(10, avgSignal / 20);
      latSum += device.location.lat * weight;
      lngSum += device.location.lng * weight;
      totalWeight += weight;
    }

    if (totalWeight === 0) return null;

    const estLat = latSum / totalWeight;
    const estLng = lngSum / totalWeight;

    // Calculate accuracy estimate based on number of devices
    const accuracy = deviceDocs.length === 2
      ? 500 // ~500m with 2 devices
      : deviceDocs.length === 3
        ? 150 // ~150m with 3 devices
        : 50; // ~50m with 4+ devices

    const confidence = Math.min(0.5 + deviceDocs.length * 0.15, 1.0);

    const deviceIdArray = deviceDocs.map((d: any) => d._id as Id<"devices">);
    const obsIdArray = recentObs.map((o: any) => o._id as Id<"imsiObservations">);

    // Check if a triangulation already exists for this IMSI
    const existingTri = await ctx.db
      .query("triangulations")
      .withIndex("by_imsi", (q) => q.eq("imsi", args.imsi))
      .first();

    if (existingTri) {
      // Only update if confidence improved or last seen is old
      if (confidence > existingTri.confidence ||
          existingTri.lastSeen < Date.now() - 600000) {
        await ctx.db.patch(existingTri._id, {
          position: { lat: estLat, lng: estLng },
          accuracy,
          confidence,
          deviceIds: deviceIdArray,
          observationIds: obsIdArray,
          timestamp: Date.now(),
          lastSeen: Date.now(),
        });
      } else {
        // Just update last seen
        await ctx.db.patch(existingTri._id, {
          lastSeen: Date.now(),
        });
      }
    } else {
      await ctx.db.insert("triangulations", {
        imsi: args.imsi,
        position: { lat: estLat, lng: estLng },
        accuracy,
        confidence,
        deviceIds: deviceIdArray,
        observationIds: obsIdArray,
        timestamp: Date.now(),
        lastSeen: Date.now(),
      });
    }

    return null;
  },
});

export const list = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("triangulations"),
      _creationTime: v.number(),
      imsi: v.string(),
      position: v.object({ lat: v.number(), lng: v.number() }),
      accuracy: v.number(),
      confidence: v.number(),
      deviceIds: v.array(v.id("devices")),
      observationIds: v.array(v.id("imsiObservations")),
      timestamp: v.number(),
      lastSeen: v.number(),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db.query("triangulations").order("desc").collect();
  },
});

export const getActivePositions = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("triangulations"),
      imsi: v.string(),
      lat: v.number(),
      lng: v.number(),
      accuracy: v.number(),
      confidence: v.number(),
      lastSeen: v.number(),
    }),
  ),
  handler: async (ctx) => {
    const tris = await ctx.db.query("triangulations").collect();
    const now = Date.now();
    return tris
      .filter((t) => t.lastSeen > now - 3600000) // Active in last hour
      .map((t) => ({
        _id: t._id,
        imsi: t.imsi,
        lat: t.position.lat,
        lng: t.position.lng,
        accuracy: t.accuracy,
        confidence: t.confidence,
        lastSeen: t.lastSeen,
      }));
  },
});