# Aquaponics Monitoring System

自宅アクアポニックス環境のセンサーデータを収集・蓄積・可視化するモノレポ。

## Architecture

```
Raspberry Pi (自宅)              VPS
┌─────────────┐        ┌──────────────────────┐
│  pi-agent   │──MQTT──▶  Mosquitto           │
│  (sensors)  │        │    ↓                  │
└─────────────┘        │  ingester             │
                       │    ↓                  │
                       │  TimescaleDB          │
                       │    ↓                  │
                       │  Grafana (dashboard)  │
                       └──────────────────────┘
```

## Directory Structure

| Path | Description |
| --- | --- |
| `apps/pi-agent` | Raspberry Pi で動く sensor reader & MQTT publisher |
| `apps/ingester` | MQTT subscriber → TimescaleDB writer |
| `apps/ops-dashboard` | 管理画面 (将来用) |
| `infra/vps` | VPS 用 Docker Compose, Mosquitto, Grafana, TimescaleDB |
| `infra/pi` | Pi 用 Docker Compose, systemd, provisioning |
| `packages/contracts` | MQTT payload schema, topic 定義, 型 |
| `packages/config` | 共通設定値、メトリクス名、unit 定義 |
| `packages/utils` | 共通ライブラリ |
| `.github/workflows` | CI/CD |
| `docs` | 運用手順、障害対応、センサー追加手順 |

## Quick Start

### VPS 側

```bash
cd infra/vps
cp .env.example .env  # 環境変数を設定
docker compose -f docker-compose.vps.yml up -d
```

### Raspberry Pi 側

```bash
cd infra/pi
cp env/.env.example env/.env  # 環境変数を設定
docker compose -f docker-compose.pi.yml up -d
```

## Monitored Metrics

| Metric | Unit |
| --- | --- |
| Water Temperature | °C |
| Air Temperature | °C |
| pH | pH |
| Dissolved Oxygen | mg/L |
| Electrical Conductivity | μS/cm |
| Humidity | % |

## Deploy

### Strategy

Pi でも VPS でもローカル build はしない。GitHub Actions (GitHub-hosted runner) で Docker image を build し、GHCR に push。本番機は pull して起動するだけ。

```
main merge → GitHub Actions build → GHCR push → 本番 pull → compose up → health check
```

### Workflows

| Workflow | Trigger | Target |
| --- | --- | --- |
| `ci.yml` | PR / push to main | lint, test (GitHub-hosted) |
| `deploy-pi.yml` | push to main (`apps/pi-agent/**`, `infra/pi/**`) | Pi self-hosted runner |
| `deploy-vps.yml` | push to main (`apps/ingester/**`, `infra/vps/**`) | VPS via SSH |
| `db-migration.yml` | push to main (`infra/vps/timescaledb/**`) | TimescaleDB schema |

### Rollback

Health check が失敗した場合、直前の image tag に自動 rollback する。

## Docs

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [Sensors](docs/sensors.md)
