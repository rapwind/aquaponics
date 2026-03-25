# Runbook

## VPS 起動手順

```bash
cd infra/vps
docker compose up -d
```

## Raspberry Pi 起動手順

```bash
cd infra/pi
docker compose -f docker-compose.pi.yml up -d
```

## 障害対応

### MQTT 接続できない

1. Mosquitto コンテナの状態を確認
2. ファイアウォール (8883 ポート) を確認
3. 認証情報 (.env) を確認

### データが Grafana に表示されない

1. ingester のログを確認: `docker compose logs ingester`
2. TimescaleDB への接続を確認
3. pi-agent のログを確認: `docker compose logs pi-agent`
