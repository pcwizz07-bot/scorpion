import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

export const list = query({
  args: {
    limit: v.optional(v.number()),
  },
  returns: v.array(
    v.object({
      _id: v.id("alerts"),
      _creationTime: v.number(),
      imsi: v.optional(v.string()),
      deviceId: v.optional(v.id("devices")),
      type: v.string(),
      severity: v.string(),
      title: v.string(),
      message: v.string(),
      aiAnalysis: v.optional(v.string()),
      resolved: v.boolean(),
      resolvedAt: v.optional(v.number()),
      resolvedBy: v.optional(v.string()),
      timestamp: v.number(),
    }),
  ),
  handler: async (ctx, args) => {
    const limit = args.limit ?? 50;
    return await ctx.db
      .query("alerts")
      .withIndex("by_timestamp", (q) => q)
      .order("desc")
      .take(limit);
  },
});

export const getUnresolved = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("alerts"),
      _creationTime: v.number(),
      imsi: v.optional(v.string()),
      deviceId: v.optional(v.id("devices")),
      type: v.string(),
      severity: v.string(),
      title: v.string(),
      message: v.string(),
      aiAnalysis: v.optional(v.string()),
      resolved: v.boolean(),
      resolvedAt: v.optional(v.number()),
      resolvedBy: v.optional(v.string()),
      timestamp: v.number(),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db
      .query("alerts")
      .withIndex("by_resolved", (q) => q.eq("resolved", false))
      .order("desc")
      .collect();
  },
});

export const getCritical = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("alerts"),
      _creationTime: v.number(),
      imsi: v.optional(v.string()),
      deviceId: v.optional(v.id("devices")),
      type: v.string(),
      severity: v.string(),
      title: v.string(),
      message: v.string(),
      aiAnalysis: v.optional(v.string()),
      resolved: v.boolean(),
      resolvedAt: v.optional(v.number()),
      resolvedBy: v.optional(v.string()),
      timestamp: v.number(),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db
      .query("alerts")
      .withIndex("by_severity", (q) => q.eq("severity", "critical"))
      .order("desc")
      .collect();
  },
});

export const createAlert = mutation({
  args: {
    imsi: v.optional(v.string()),
    deviceId: v.optional(v.id("devices")),
    type: v.string(),
    severity: v.string(),
    title: v.string(),
    message: v.string(),
    aiAnalysis: v.optional(v.string()),
  },
  returns: v.id("alerts"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("alerts", {
      ...args,
      resolved: false,
      timestamp: Date.now(),
    });
  },
});

export const resolveAlert = mutation({
  args: {
    alertId: v.id("alerts"),
    resolvedBy: v.optional(v.string()),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.alertId, {
      resolved: true,
      resolvedAt: Date.now(),
      resolvedBy: args.resolvedBy ?? "system",
    });
    return null;
  },
});

export const getAlertStats = query({
  args: {},
  returns: v.object({
    total: v.number(),
    unresolved: v.number(),
    critical: v.number(),
    warning: v.number(),
  }),
  handler: async (ctx) => {
    const all = await ctx.db.query("alerts").collect();
    return {
      total: all.length,
      unresolved: all.filter((a) => !a.resolved).length,
      critical: all.filter((a) => a.severity === "critical").length,
      warning: all.filter((a) => a.severity === "warning").length,
    };
  },
});