-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Sensor readings hypertable
CREATE TABLE IF NOT EXISTS sensor_readings (
    time        TIMESTAMPTZ NOT NULL,
    sensor_id   TEXT        NOT NULL,
    metric      TEXT        NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    unit        TEXT        NOT NULL
);

SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_sensor_readings_sensor_metric
    ON sensor_readings (sensor_id, metric, time DESC);
