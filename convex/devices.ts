import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

export const list = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("devices"),
      _creationTime: v.number(),
      name: v.string(),
      location: v.object({ lat: v.number(), lng: v.number() }),
      altitude: v.optional(v.number()),
      status: v.string(),
      lastSeen: v.number(),
      firmwareVersion: v.optional(v.string()),
      signalStrength: v.optional(v.number()),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db.query("devices").order("desc").collect();
  },
});

export const getById = query({
  args: { deviceId: v.id("devices") },
  returns: v.union(
    v.object({
      _id: v.id("devices"),
      _creationTime: v.number(),
      name: v.string(),
      location: v.object({ lat: v.number(), lng: v.number() }),
      altitude: v.optional(v.number()),
      status: v.string(),
      lastSeen: v.number(),
      firmwareVersion: v.optional(v.string()),
      signalStrength: v.optional(v.number()),
    }),
    v.null(),
  ),
  handler: async (ctx, args) => {
    return await ctx.db.get(args.deviceId);
  },
});

export const register = mutation({
  args: {
    name: v.string(),
    lat: v.number(),
    lng: v.number(),
    altitude: v.optional(v.number()),
    firmwareVersion: v.optional(v.string()),
  },
  returns: v.id("devices"),
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("devices")
      .withIndex("by_status", (q) => q.eq("status", "online"))
      .collect();
    const existingByName = existing.find((d) => d.name === args.name);
    if (existingByName) {
      // Re-register - update status
      await ctx.db.patch(existingByName._id, {
        status: "online",
        lastSeen: Date.now(),
        location: { lat: args.lat, lng: args.lng },
        altitude: args.altitude,
        firmwareVersion: args.firmwareVersion,
      });

      // Create sensor for device if not exists
      const existingSensors = await ctx.db
        .query("sensors")
        .filter((q) => q.eq(q.field("deviceId"), existingByName._id))
        .collect();
      if (existingSensors.length === 0) {
        await ctx.db.insert("sensors", {
          deviceId: existingByName._id,
          enabled: true,
        });
      }

      return existingByName._id;
    }

    const deviceId = await ctx.db.insert("devices", {
      name: args.name,
      location: { lat: args.lat, lng: args.lng },
      altitude: args.altitude,
      status: "online",
      lastSeen: Date.now(),
      firmwareVersion: args.firmwareVersion,
    });

    // Auto-create a sensor for this device
    await ctx.db.insert("sensors", {
      deviceId,
      enabled: true,
    });

    // Create an alert for new device registration
    await ctx.db.insert("alerts", {
      deviceId,
      type: "new_device",
      severity: "info",
      title: `New device registered: ${args.name}`,
      message: `Device ${args.name} has been deployed at ${args.lat}, ${args.lng}`,
      resolved: false,
      timestamp: Date.now(),
    });

    return deviceId;
  },
});

export const heartbeat = mutation({
  args: {
    deviceId: v.id("devices"),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const device = await ctx.db.get(args.deviceId);
    if (!device) throw new Error("Device not found");
    await ctx.db.patch(args.deviceId, {
      lastSeen: Date.now(),
      status: "online",
    });
    return null;
  },
});

export const updateStatus = mutation({
  args: {
    deviceId: v.id("devices"),
    status: v.string(),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const device = await ctx.db.get(args.deviceId);
    if (!device) throw new Error("Device not found");
    await ctx.db.patch(args.deviceId, {
      status: args.status,
      lastSeen: Date.now(),
    });
    return null;
  },
});

export const getOnlineCount = query({
  args: {},
  returns: v.number(),
  handler: async (ctx) => {
    const devices = await ctx.db
      .query("devices")
      .withIndex("by_status", (q) => q.eq("status", "online"))
      .collect();
    return devices.length;
  },
});

export const getDeployedLocations = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("devices"),
      name: v.string(),
      lat: v.number(),
      lng: v.number(),
      status: v.string(),
    }),
  ),
  handler: async (ctx) => {
    const devices = await ctx.db.query("devices").collect();
    return devices.map((d) => ({
      _id: d._id,
      name: d.name,
      lat: d.location.lat,
      lng: d.location.lng,
      status: d.status,
    }));
  },
});
