import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // Raspberry Pi devices deployed in the field
  devices: defineTable({
    name: v.string(),           // e.g., "Pi-1-North"
    location: v.object({
      lat: v.number(),
      lng: v.number(),
    }),
    altitude: v.optional(v.number()),
    status: v.string(),         // "online", "offline", "warning"
    lastSeen: v.number(),        // timestamp
    firmwareVersion: v.optional(v.string()),
    signalStrength: v.optional(v.number()),
  }).index("by_status", ["status"]),

  // RTL-SDR sensor config per device
  sensors: defineTable({
    deviceId: v.id("devices"),
    frequency: v.optional(v.number()),
    gain: v.optional(v.number()),
    enabled: v.boolean(),
    lastScanTime: v.optional(v.number()),
  }),

  // IMSI observations captured by sensors
  imsiObservations: defineTable({
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
    timestamp: v.number(),
    rawData: v.optional(v.string()),
  })
    .index("by_imsi", ["imsi"])
    .index("by_device", ["deviceId"])
    .index("by_timestamp", ["timestamp"])
    .index("by_device_timestamp", ["deviceId", "timestamp"]),

  // Triangulated positions for detected IMSIs
  triangulations: defineTable({
    imsi: v.string(),
    position: v.object({
      lat: v.number(),
      lng: v.number(),
    }),
    accuracy: v.number(),      // estimated accuracy in meters
    confidence: v.number(),    // 0-1 confidence score
    deviceIds: v.array(v.id("devices")),
    observationIds: v.array(v.id("imsiObservations")),
    timestamp: v.number(),
    lastSeen: v.number(),
  })
    .index("by_imsi", ["imsi"])
    .index("by_timestamp", ["timestamp"]),

  // Organized tracking sessions (anti-poaching operations)
  trackingSessions: defineTable({
    name: v.string(),
    description: v.optional(v.string()),
    status: v.string(),         // "active", "completed", "cancelled"
    startTime: v.number(),
    endTime: v.optional(v.number()),
    deviceIds: v.array(v.id("devices")),
    notes: v.optional(v.string()),
    createdBy: v.optional(v.string()),
  })
    .index("by_status", ["status"])
    .index("by_start_time", ["startTime"]),

  // IMSI targets being tracked
  trackedImsis: defineTable({
    imsi: v.string(),
    label: v.optional(v.string()),
    notes: v.optional(v.string()),
    sessionId: v.optional(v.id("trackingSessions")),
    firstSeen: v.number(),
    lastSeen: v.number(),
    riskLevel: v.optional(v.string()),  // "low", "medium", "high", "critical"
    isActive: v.boolean(),
  })
    .index("by_imsi", ["imsi"])
    .index("by_active", ["isActive"])
    .index("by_session", ["sessionId"]),

  // AI investigator alerts and analysis
  alerts: defineTable({
    imsi: v.optional(v.string()),
    deviceId: v.optional(v.id("devices")),
    type: v.string(),           // "suspicious_imei", "new_device", "frequency_anomaly", "ai_analysis"
    severity: v.string(),       // "info", "warning", "critical"
    title: v.string(),
    message: v.string(),
    aiAnalysis: v.optional(v.string()),
    resolved: v.boolean(),
    resolvedAt: v.optional(v.number()),
    resolvedBy: v.optional(v.string()),
    timestamp: v.number(),
  })
    .index("by_severity", ["severity"])
    .index("by_resolved", ["resolved"])
    .index("by_timestamp", ["timestamp"]),

  // AI conversation history
  aiConversations: defineTable({
    query: v.string(),
    response: v.string(),
    context: v.optional(v.string()),
    timestamp: v.number(),
    userId: v.optional(v.string()),
  })
    .index("by_timestamp", ["timestamp"]),
});