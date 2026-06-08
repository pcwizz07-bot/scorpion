import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

export const list = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("trackingSessions"),
      _creationTime: v.number(),
      name: v.string(),
      description: v.optional(v.string()),
      status: v.string(),
      startTime: v.number(),
      endTime: v.optional(v.number()),
      deviceIds: v.array(v.id("devices")),
      notes: v.optional(v.string()),
      createdBy: v.optional(v.string()),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db.query("trackingSessions").order("desc").collect();
  },
});

export const getActive = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("trackingSessions"),
      _creationTime: v.number(),
      name: v.string(),
      description: v.optional(v.string()),
      status: v.string(),
      startTime: v.number(),
      endTime: v.optional(v.number()),
      deviceIds: v.array(v.id("devices")),
      notes: v.optional(v.string()),
      createdBy: v.optional(v.string()),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db
      .query("trackingSessions")
      .withIndex("by_status", (q) => q.eq("status", "active"))
      .order("desc")
      .collect();
  },
});

export const create = mutation({
  args: {
    name: v.string(),
    description: v.optional(v.string()),
    deviceIds: v.array(v.id("devices")),
    notes: v.optional(v.string()),
    createdBy: v.optional(v.string()),
  },
  returns: v.id("trackingSessions"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("trackingSessions", {
      name: args.name,
      description: args.description,
      status: "active",
      startTime: Date.now(),
      deviceIds: args.deviceIds,
      notes: args.notes,
      createdBy: args.createdBy,
    });
  },
});

export const complete = mutation({
  args: {
    sessionId: v.id("trackingSessions"),
    notes: v.optional(v.string()),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const session = await ctx.db.get(args.sessionId);
    if (!session) throw new Error("Session not found");
    await ctx.db.patch(args.sessionId, {
      status: "completed",
      endTime: Date.now(),
      notes: args.notes ? `${session.notes ?? ""}\n${args.notes}` : session.notes,
    });
    return null;
  },
});