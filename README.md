# Aquaponics Monitoring System

自宅アクアポニックス環境のセンサーデータを収集・蓄積・可視化するモノレポ。

## Architecture

- Raspberry Pi publishes MQTT telemetry
- VPS runs Mosquitto, TimescaleDB, Grafana, and ingester
- GitHub Actions deploys Pi and VPS automatically

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
| `apps/pi-agent` | Raspberry Pi sensor reader & MQTT publisher |
| `apps/ingester` | MQTT subscriber → TimescaleDB writer |
| `infra/vps` | VPS Docker Compose, Mosquitto, Grafana, TimescaleDB |
| `infra/pi` | Pi Docker Compose |
| `packages/contracts` | MQTT topic / metric 定義 (TypeScript) |
| `.github/workflows` | CI/CD |

## Deploy

### Pi

- merge to `main`
- builds `apps/pi-agent`
- pushes image to GHCR
- Pi runner pulls and restarts via compose

### VPS

- merge to `main`
- builds `apps/ingester`
- pushes image to GHCR
- GitHub Actions SSHes into VPS and runs `infra/vps/scripts/deploy.sh`

## Secrets

### GitHub Environment: `prod`

- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_PORT`

## Local env files

- `/home/app/deploy/aquaponics/env/app.env`
- `/home/actions/deploy/aquaponics/env/pi-agent.env`
