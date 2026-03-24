# Architecture

## Overview

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

## Components

| Component    | Role                                   |
| ------------ | -------------------------------------- |
| pi-agent     | センサー読み取り & MQTT publish        |
| Mosquitto    | MQTT ブローカー                        |
| ingester     | MQTT subscribe → TimescaleDB write     |
| TimescaleDB  | 時系列データ保存                       |
| Grafana      | 可視化ダッシュボード                   |
