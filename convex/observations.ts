import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

export const recordObservation = mutation({
  args: {
    deviceId: v.id("devices"),
    sensorId: v.id("sensors"),
    imsi: v.string(),
    tmsi1: v.optional(v.string()),
    tmsi2: v.optional(v.string()),
    mcc: v.string(),
    mnc: v.string(),
    lac: v.optional(v.number()),
    cellId: v.optional(v.number()),
    country: v.optional(v.string()),
    brand: v.optional(v.string()),
    operator: v.optional(v.string()),
    signalDbm: v.optional(v.number()),
    snrDb: v.optional(v.number()),
    arfcn: v.optional(v.number()),
    frequency: v.optional(v.number()),
    rawData: v.optional(v.string()),
  },
  returns: v.id("imsiObservations"),
  handler: async (ctx, args) => {
    const observationId = await ctx.db.insert("imsiObservations", {
      deviceId: args.deviceId,
      sensorId: args.sensorId,
      imsi: args.imsi,
      tmsi1: args.tmsi1,
      tmsi2: args.tmsi2,
      mcc: args.mcc,
      mnc: args.mnc,
      lac: args.lac,
      cellId: args.cellId,
      country: args.country,
      brand: args.brand,
      operator: args.operator,
      signalDbm: args.signalDbm,
      snrDb: args.snrDb,
      arfcn: args.arfcn,
      frequency: args.frequency,
      rawData: args.rawData,
      timestamp: Date.now(),
    });

    // Update or create tracked IMSI entry
    const existing = await ctx.db
      .query("trackedImsis")
      .withIndex("by_imsi", (q) => q.eq("imsi", args.imsi))
      .first();

    if (existing) {
      await ctx.db.patch(existing._id, {
        lastSeen: Date.now(),
        isActive: true,
      });
    } else {
      await ctx.db.insert("trackedImsis", {
        imsi: args.imsi,
        firstSeen: Date.now(),
        lastSeen: Date.now(),
        isActive: true,
      });

      // Alert on new IMSI detection
      await ctx.db.insert("alerts", {
        imsi: args.imsi,
        deviceId: args.deviceId,
        type: "new_device",
        severity: args.country ? "info" : "warning",
        title: `New IMSI detected: ${args.imsi.slice(0, 8)}...`,
        message: `IMSI ${args.country ? `from ${args.country} (${args.brand})` : "unknown origin"} detected at ${new Date().toISOString()}`,
        resolved: false,
        timestamp: Date.now(),
      });
    }

    // Update sensor last scan time
    await ctx.db.patch(args.sensorId, {
      lastScanTime: Date.now(),
    });

    return observationId;
  },
});

export const batchRecord = mutation({
  args: {
    observations: v.array(
      v.object({
        deviceId: v.id("devices"),
        sensorId: v.id("sensors"),
        imsi: v.string(),
        tmsi1: v.optional(v.string()),
        tmsi2: v.optional(v.string()),
        mcc: v.string(),
        mnc: v.string(),
        lac: v.optional(v.number()),
        cellId: v.optional(v.number()),
        country: v.optional(v.string()),
        brand: v.optional(v.string()),
        operator: v.optional(v.string()),
        signalDbm: v.optional(v.number()),
        snrDb: v.optional(v.number()),
        arfcn: v.optional(v.number()),
        frequency: v.optional(v.number()),
        rawData: v.optional(v.string()),
      }),
    ),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    for (const obs of args.observations) {
      await ctx.db.insert("imsiObservations", {
        ...obs,
        timestamp: Date.now(),
      });

      const existing = await ctx.db
        .query("trackedImsis")
        .withIndex("by_imsi", (q) => q.eq("imsi", obs.imsi))
        .first();

      if (existing) {
        await ctx.db.patch(existing._id, {
          lastSeen: Date.now(),
          isActive: true,
        });
      } else {
        await ctx.db.insert("trackedImsis", {
          imsi: obs.imsi,
          firstSeen: Date.now(),
          lastSeen: Date.now(),
          isActive: true,
        });
      }
    }
    return null;
  },
});

export const getRecent = query({
  args: {
    limit: v.optional(v.number()),
  },
  returns: v.array(
    v.object({
      _id: v.id("imsiObservations"),
      _creationTime: v.number(),
      deviceId: v.id("devices"),
      sensorId: v.id("sensors"),
      imsi: v.string(),
      tmsi1: v.optional(v.string()),
      tmsi2: v.optional(v.string()),
      mcc: v.string(),
      mnc: v.string(),
      lac: v.optional(v.number()),
      cellId: v.optional(v.number()),
      country: v.optional(v.string()),
      brand: v.optional(v.string()),
      operator: v.optional(v.string()),
      signalDbm: v.optional(v.number()),
      snrDb: v.optional(v.number()),
      arfcn: v.optional(v.number()),
      frequency: v.optional(v.number()),
      rawData: v.optional(v.string()),
      timestamp: v.number(),
    }),
  ),
  handler: async (ctx, args) => {
    const limit = args.limit ?? 50;
    return await ctx.db
      .query("imsiObservations")
      .withIndex("by_timestamp", (q) => q)
      .order("desc")
      .take(limit);
  },
});

export const getByImsi = query({
  args: {
    imsi: v.string(),
    limit: v.optional(v.number()),
  },
  returns: v.array(
    v.object({
      _id: v.id("imsiObservations"),
      _creationTime: v.number(),
      deviceId: v.id("devices"),
      sensorId: v.id("sensors"),
      imsi: v.string(),
      tmsi1: v.optional(v.string()),
      tmsi2: v.optional(v.string()),
      mcc: v.string(),
      mnc: v.string(),
      lac: v.optional(v.number()),
      cellId: v.optional(v.number()),
      country: v.optional(v.string()),
      brand: v.optional(v.string()),
      operator: v.optional(v.string()),
      signalDbm: v.optional(v.number()),
      snrDb: v.optional(v.number()),
      arfcn: v.optional(v.number()),
      frequency: v.optional(v.number()),
      rawData: v.optional(v.string()),
      timestamp: v.number(),
    }),
  ),
  handler: async (ctx, args) => {
    const limit = args.limit ?? 20;
    return await ctx.db
      .query("imsiObservations")
      .withIndex("by_imsi", (q) => q.eq("imsi", args.imsi))
      .order("desc")
      .take(limit);
  },
});

export const getStats = query({
  args: {},
  returns: v.object({
    totalObservations: v.number(),
    uniqueImsis: v.number(),
    uniqueCountries: v.number(),
    activeImsis24h: v.number(),
  }),
  handler: async (ctx) => {
    const allObs = await ctx.db.query("imsiObservations").collect();
    const allTracked = await ctx.db.query("trackedImsis").collect();

    const uniqueImsis = new Set(allObs.map((o) => o.imsi)).size;
    const countries = new Set(allObs.filter((o) => o.country).map((o) => o.country!)).size;
    const now = Date.now();
    const active24h = allTracked.filter((t) => t.lastSeen > now - 86400000 && t.isActive).length;

    return {
      totalObservations: allObs.length,
      uniqueImsis,
      uniqueCountries: countries,
      activeImsis24h: active24h,
    };
  },
});

export const getByDevice = query({
  args: {
    deviceId: v.id("devices"),
    limit: v.optional(v.number()),
  },
  returns: v.array(
    v.object({
      _id: v.id("imsiObservations"),
      _creationTime: v.number(),
      deviceId: v.id("devices"),
      sensorId: v.id("sensors"),
      imsi: v.string(),
      mcc: v.string(),
      mnc: v.string(),
      country: v.optional(v.string()),
      brand: v.optional(v.string()),
      operator: v.optional(v.string()),
      signalDbm: v.optional(v.number()),
      timestamp: v.number(),
    }),
  ),
  handler: async (ctx, args) => {
    const limit = args.limit ?? 20;
    return await ctx.db
      .query("imsiObservations")
      .withIndex("by_device", (q) => q.eq("deviceId", args.deviceId))
      .order("desc")
      .take(limit);
  },
});
