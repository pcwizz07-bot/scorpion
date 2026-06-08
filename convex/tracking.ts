import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

export const list = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("trackedImsis"),
      _creationTime: v.number(),
      imsi: v.string(),
      label: v.optional(v.string()),
      notes: v.optional(v.string()),
      sessionId: v.optional(v.id("trackingSessions")),
      firstSeen: v.number(),
      lastSeen: v.number(),
      riskLevel: v.optional(v.string()),
      isActive: v.boolean(),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db.query("trackedImsis").order("desc").collect();
  },
});

export const getActive = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("trackedImsis"),
      _creationTime: v.number(),
      imsi: v.string(),
      label: v.optional(v.string()),
      notes: v.optional(v.string()),
      sessionId: v.optional(v.id("trackingSessions")),
      firstSeen: v.number(),
      lastSeen: v.number(),
      riskLevel: v.optional(v.string()),
      isActive: v.boolean(),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db
      .query("trackedImsis")
      .withIndex("by_active", (q) => q.eq("isActive", true))
      .order("desc")
      .collect();
  },
});

export const getByImsi = query({
  args: { imsi: v.string() },
  returns: v.union(
    v.object({
      _id: v.id("trackedImsis"),
      _creationTime: v.number(),
      imsi: v.string(),
      label: v.optional(v.string()),
      notes: v.optional(v.string()),
      sessionId: v.optional(v.id("trackingSessions")),
      firstSeen: v.number(),
      lastSeen: v.number(),
      riskLevel: v.optional(v.string()),
      isActive: v.boolean(),
    }),
    v.null(),
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("trackedImsis")
      .withIndex("by_imsi", (q) => q.eq("imsi", args.imsi))
      .first();
  },
});

export const update = mutation({
  args: {
    id: v.id("trackedImsis"),
    label: v.optional(v.string()),
    notes: v.optional(v.string()),
    riskLevel: v.optional(v.string()),
    isActive: v.optional(v.boolean()),
    sessionId: v.optional(v.id("trackingSessions")),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const { id, ...updates } = args;
    await ctx.db.patch(id, updates);
    return null;
  },
});

export const getCountByBrand = query({
  args: {},
  returns: v.array(
    v.object({
      brand: v.string(),
      count: v.number(),
    }),
  ),
  handler: async (ctx) => {
    const tracked = await ctx.db.query("trackedImsis").collect();
    // Get operator info from observations
    const obs = await ctx.db.query("imsiObservations").collect();
    const brandCounts: Record<string, number> = {};
    for (const o of obs) {
      if (o.brand) {
        brandCounts[o.brand] = (brandCounts[o.brand] || 0) + 1;
      }
    }
    return Object.entries(brandCounts).map(([brand, count]) => ({ brand, count }));
  },
});