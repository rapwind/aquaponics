/**
 * Metric definitions for aquaponics monitoring system.
 */

export const METRICS = {
  WATER_TEMP: { name: "water_temperature", unit: "°C" },
  AIR_TEMP: { name: "air_temperature", unit: "°C" },
  PH: { name: "ph", unit: "pH" },
  DISSOLVED_OXYGEN: { name: "dissolved_oxygen", unit: "mg/L" },
  EC: { name: "electrical_conductivity", unit: "μS/cm" },
  WATER_LEVEL: { name: "water_level", unit: "cm" },
  HUMIDITY: { name: "humidity", unit: "%" },
} as const;

export type MetricKey = keyof typeof METRICS;
export type Metric = (typeof METRICS)[MetricKey];
