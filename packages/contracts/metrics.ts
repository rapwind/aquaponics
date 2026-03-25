export const metrics = {
  air_temp_c: { unit: "C" },
  humidity_pct: { unit: "%" },
  pressure_hpa: { unit: "hPa" },
  lux: { unit: "lux" },
  water_temp_c: { unit: "C" },
  water_level_cm: { unit: "cm" },
  ph: { unit: "pH" },
  cpu_pct: { unit: "%" },
  mem_pct: { unit: "%" },
} as const;

export type MetricName = keyof typeof metrics;
