export const topicRoots = {
  data: "dt",
  command: "cmd",
} as const;

export const buildDataTopic = (
  siteId: string,
  tankId: string,
  deviceId: string,
  sensorGroup: "env" | "water" | "device" | "event" | "heartbeat",
) => `${topicRoots.data}/aquaponics/${siteId}/${tankId}/${deviceId}/${sensorGroup}`;

export const buildCommandTopic = (
  siteId: string,
  tankId: string,
  deviceId: string,
  command: "config" | "restart",
) => `${topicRoots.command}/aquaponics/${siteId}/${tankId}/${deviceId}/${command}`;
