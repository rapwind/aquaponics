/**
 * MQTT topic definitions for aquaponics monitoring system.
 */

export const TOPICS = {
  SENSOR_DATA: "aquaponics/sensors/+/data",
  SENSOR_STATUS: "aquaponics/sensors/+/status",
  SYSTEM_HEARTBEAT: "aquaponics/system/heartbeat",
} as const;

export type Topic = (typeof TOPICS)[keyof typeof TOPICS];
