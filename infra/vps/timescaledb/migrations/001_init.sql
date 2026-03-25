CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS sensor_metrics (
  ts            TIMESTAMPTZ        NOT NULL,
  tank_id       TEXT               NOT NULL,
  device_id     TEXT               NOT NULL,
  sensor_group  TEXT               NOT NULL,
  metric_name   TEXT               NOT NULL,
  value         DOUBLE PRECISION   NOT NULL,
  unit          TEXT,
  status        TEXT,
  topic         TEXT               NOT NULL,
  raw_payload   JSONB,
  created_at    TIMESTAMPTZ        NOT NULL DEFAULT now()
);

SELECT create_hypertable('sensor_metrics', 'ts', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_sensor_metrics_tank_metric_ts
  ON sensor_metrics (tank_id, metric_name, ts DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_metrics_device_group_ts
  ON sensor_metrics (device_id, sensor_group, ts DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_metrics_topic_ts
  ON sensor_metrics (topic, ts DESC);

ALTER TABLE sensor_metrics SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'tank_id,device_id,sensor_group,metric_name',
  timescaledb.compress_orderby = 'ts DESC'
);

SELECT add_compression_policy('sensor_metrics', INTERVAL '7 days');
SELECT add_retention_policy('sensor_metrics', INTERVAL '45 days');

CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
  time_bucket(INTERVAL '1 hour', ts) AS bucket,
  tank_id,
  device_id,
  sensor_group,
  metric_name,
  avg(value) AS avg_value,
  min(value) AS min_value,
  max(value) AS max_value,
  count(*)   AS samples
FROM sensor_metrics
GROUP BY 1,2,3,4,5;

SELECT add_continuous_aggregate_policy(
  'sensor_metrics_hourly',
  start_offset => INTERVAL '7 days',
  end_offset => INTERVAL '5 minutes',
  schedule_interval => INTERVAL '15 minutes'
);

CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_metrics_daily
WITH (timescaledb.continuous) AS
SELECT
  time_bucket(INTERVAL '1 day', ts) AS bucket,
  tank_id,
  device_id,
  sensor_group,
  metric_name,
  avg(value) AS avg_value,
  min(value) AS min_value,
  max(value) AS max_value,
  count(*)   AS samples
FROM sensor_metrics
GROUP BY 1,2,3,4,5;

SELECT add_continuous_aggregate_policy(
  'sensor_metrics_daily',
  start_offset => INTERVAL '90 days',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour'
);
