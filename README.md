# Aquaponics Monitoring System

自宅アクアポニックス環境のセンサーデータを収集・蓄積・可視化するモノレポ。

## Architecture

```
Raspberry Pi (自宅)                    VPS
┌──────────────────────┐      ┌──────────────────────────────┐
│  pi-agent            │      │  Mosquitto (port 1883)       │
│                      │ MQTT │    ↓                         │
│  BME280  → 気温/湿度/気圧 │──────▶  ingester (MQTT → DB)     │
│  BH1750  → 照度      │      │    ↓                         │
│  DS18B20 → 水温      │      │  TimescaleDB (port 5432)     │
│  psutil  → CPU/Mem/Disk │   │    ↓                         │
└──────────────────────┘      │  Grafana (port 3000)         │
                              └──────────────────────────────┘
```

- Raspberry Pi がセンサーデータを MQTT で VPS へ送信
- VPS の ingester が MQTT subscribe → TimescaleDB へ書き込み
- Grafana でダッシュボード可視化
- GitHub Actions が Pi / VPS を自動デプロイ

## Directory Structure

```
.
├── apps/
│   ├── ingester/              # MQTT subscriber → TimescaleDB writer
│   │   ├── Dockerfile
│   │   ├── requirements.txt   # paho-mqtt, psycopg
│   │   └── src/
│   │       ├── main.py        # MQTT loop + DB insert
│   │       ├── config.py      # 環境変数読み込み
│   │       ├── parser.py      # topic 解析 / payload → row 変換
│   │       └── db.py          # PostgreSQL 接続 / INSERT
│   └── pi-agent/              # Raspberry Pi sensor publisher
│       ├── Dockerfile         # python:3.12-slim + libgpiod2
│       ├── requirements.txt   # paho-mqtt, psutil, adafruit-*, w1thermsensor
│       └── src/
│           └── main.py        # センサー読取 → MQTT publish (30s間隔)
├── infra/
│   ├── vps/
│   │   ├── docker-compose.yml          # Mosquitto, TimescaleDB, Grafana, ingester
│   │   ├── scripts/deploy.sh           # git sync → compose pull → up
│   │   ├── mosquitto/config/
│   │   │   └── mosquitto.conf          # 認証あり, ファイルログ
│   │   ├── timescaledb/migrations/
│   │   │   └── 001_init.sql            # hypertable + 圧縮 + 保持 + 集約ビュー
│   │   ├── grafana/
│   │   │   ├── provisioning/
│   │   │   │   ├── datasources/postgres.yml
│   │   │   │   └── dashboards/dashboards.yml
│   │   │   └── dashboards/
│   │   │       └── aquaponics-overview.json
│   │   └── env/app.env.example
│   └── pi/
│       ├── docker-compose.pi.yml       # pi-agent (privileged, host network)
│       └── env/pi-agent.env.example
├── packages/contracts/
│   ├── topics.ts              # MQTT topic builder (dt/aquaponics/...)
│   └── metrics.ts             # メトリクス名 / unit 定義
└── .github/workflows/
    ├── deploy-vps.yml         # ingester build → GHCR push → SSH deploy
    ├── deploy-pi.yml          # checkout → rsync → compose up (on Pi runner)
    └── ping-pi.yml            # Pi runner 診断 (手動実行)
```

## Sensors

| センサー | メトリクス | unit | topic group |
| --- | --- | --- | --- |
| BME280 (I2C) | `air_temp_c` | C | env |
| BME280 (I2C) | `humidity_pct` | % | env |
| BME280 (I2C) | `pressure_hpa` | hPa | env |
| BH1750 (I2C) | `lux` | lux | env |
| DS18B20 (1-Wire) | `water_temp_c` | C | water |
| psutil | `cpu_pct` | % | device |
| psutil | `mem_pct` | % | device |
| psutil | `disk_pct` | % | device |

センサーが接続されていなくても pi-agent は落ちずに動作する。
`ENABLE_BME280`, `ENABLE_BH1750`, `ENABLE_DS18B20` 環境変数で個別に無効化可能。

## MQTT Topics

```
dt/aquaponics/{site_id}/{tank_id}/{device_id}/{group}
```

| group | 内容 |
| --- | --- |
| `env` | 気温 / 湿度 / 気圧 / 照度 |
| `water` | 水温 |
| `device` | CPU / メモリ / ディスク使用率 |
| `heartbeat` | 生存確認 (ts, alive, ip) |
| `event` | エラー / 情報イベント |

Payload 例:

```json
{
  "ts": "2026-03-25T01:00:00Z",
  "schema_version": 1,
  "metrics": {
    "air_temp_c": { "value": 23.4, "unit": "C" },
    "humidity_pct": { "value": 44.2, "unit": "%" }
  }
}
```

## Database

TimescaleDB hypertable `sensor_metrics`:

| column | type | note |
| --- | --- | --- |
| `ts` | TIMESTAMPTZ | パーティションキー |
| `tank_id` | TEXT | |
| `device_id` | TEXT | |
| `sensor_group` | TEXT | env / water / device |
| `metric_name` | TEXT | air_temp_c, humidity_pct, etc. |
| `value` | DOUBLE PRECISION | |
| `unit` | TEXT | nullable |
| `status` | TEXT | nullable |
| `topic` | TEXT | 元 MQTT topic |
| `raw_payload` | JSONB | 生データ保存 |
| `created_at` | TIMESTAMPTZ | DEFAULT now() |

ポリシー:
- **圧縮**: 7 日経過後 (segment by: tank_id, device_id, sensor_group, metric_name)
- **保持**: 45 日で自動削除
- **集約ビュー**: `sensor_metrics_hourly` (1h bucket), `sensor_metrics_daily` (1d bucket)

## VPS Services

| service | image | port |
| --- | --- | --- |
| mosquitto | eclipse-mosquitto:2.0 | 1883 |
| timescaledb | timescale/timescaledb:2.25.2-pg17 | 5432 |
| grafana | grafana/grafana:11.6.0 | 3000 |
| ingester | ghcr.io/rapwind/aquaponics/ingester:latest | - |

## Deploy

### VPS

1. `main` に push
2. GitHub Actions が `apps/ingester` を build → GHCR push
3. SSH で VPS に接続し `infra/vps/scripts/deploy.sh` を実行
4. deploy.sh: git pull → docker compose pull → up → grafana restart → image prune

### Pi

1. `main` に push
2. GitHub Actions が Pi の self-hosted runner 上で実行
3. checkout → rsync で `/home/actions/deploy/aquaponics/repo/` に同期
4. `docker compose -f docker-compose.pi.yml up -d`

### Workflows

| workflow | trigger | runner | 処理 |
| --- | --- | --- | --- |
| `deploy-vps.yml` | push to main (`apps/ingester/**`, `infra/vps/**`) | ubuntu-latest → SSH | build, push, deploy.sh |
| `deploy-pi.yml` | push to main (`apps/pi-agent/**`, `infra/pi/**`) | self-hosted ARM64 | checkout, rsync, compose up |
| `ping-pi.yml` | 手動 (workflow_dispatch) | self-hosted ARM64 | コンテナ状態 / env / ログ確認 |

## Secrets

### GitHub Environment: `prod`

| secret | 用途 |
| --- | --- |
| `VPS_HOST` | VPS の IP / hostname |
| `VPS_USER` | SSH ユーザー |
| `VPS_SSH_KEY` | SSH 秘密鍵 |
| `VPS_PORT` | SSH ポート |
| `PI_AGENT_ENV` | pi-agent.env の内容 (deploy-pi で書き出し) |

### Local env files (Git 管理外)

**VPS**: `/home/app/deploy/aquaponics/env/app.env`

```
DB_PASSWORD=...
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=...
MQTT_USER=piwriter
MQTT_PASSWORD=...
```

**Pi**: `/home/actions/deploy/aquaponics/env/pi-agent.env`

```
MQTT_HOST=<VPS_IP>
MQTT_PORT=1883
MQTT_USER=piwriter
MQTT_PASSWORD=...
SITE_ID=home
TANK_ID=tank-01
DEVICE_ID=pi-01
PUBLISH_INTERVAL_SEC=30
```

## Initial Setup

### VPS

```bash
# 1. ディレクトリ作成
mkdir -p ~/deploy/aquaponics/{repo,env,data}

# 2. env ファイル配置
cp infra/vps/env/app.env.example ~/deploy/aquaponics/env/app.env
vim ~/deploy/aquaponics/env/app.env  # パスワード設定

# 3. repo clone
git clone https://github.com/rapwind/aquaponics.git ~/deploy/aquaponics/repo

# 4. Mosquitto パスワード作成
cd ~/deploy/aquaponics/repo/infra/vps
docker run --rm -it \
  -v "$PWD/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto:2.0 \
  mosquitto_passwd -c /mosquitto/config/passwd piwriter

# 5. 初回起動
docker compose --env-file ~/deploy/aquaponics/env/app.env up -d
```

### Pi

```bash
# 1. ディレクトリ作成
mkdir -p ~/deploy/aquaponics/env

# 2. env ファイル配置
cp infra/pi/env/pi-agent.env.example ~/deploy/aquaponics/env/pi-agent.env
vim ~/deploy/aquaponics/env/pi-agent.env  # VPS IP, パスワード設定

# 3. GitHub Actions self-hosted runner をインストール・起動
# 4. main に push → deploy-pi.yml が自動実行
```

## Grafana Dashboard

`aquaponics-overview` ダッシュボード (自動プロビジョニング):

**Current Values** (stat + sparkline)

| パネル | メトリクス | thresholds |
| --- | --- | --- |
| Air Temp | `air_temp_c` | 18 green / 30 orange / 35 red |
| Humidity | `humidity_pct` | 30 green / 70 blue |
| Pressure | `pressure_hpa` | — |
| Light | `lux` | 200 yellow / 1000 orange |
| Water Temp | `water_temp_c` | 20 green / 28 orange / 32 red |
| Last Seen | 最終データ受信からの経過秒 | — |

**Environment** (timeseries)

| パネル | 内容 |
| --- | --- |
| Temperature (Air + Water) | `air_temp_c` + `water_temp_c` 重ね表示 |
| Humidity | `humidity_pct` |
| Atmospheric Pressure | `pressure_hpa` |
| Light (Lux) | `lux` |

**Device Health**

| パネル | 内容 |
| --- | --- |
| Pi Resource Usage | `cpu_pct` + `mem_pct` + `disk_pct` 重ね表示 |
| Recent Data | 直近 30 件テーブル |

ダッシュボード JSON は `infra/vps/grafana/dashboards/` に配置。
Grafana UI で編集 → Export JSON → repo にコミットで管理。
