# Sensors

## センサー一覧

| センサー           | 計測項目       | 単位    | インターフェース |
| ------------------ | -------------- | ------- | ---------------- |
| DS18B20            | 水温           | °C      | 1-Wire           |
| DHT22              | 気温・湿度     | °C / %  | GPIO             |
| pH センサー        | pH             | pH      | ADC              |
| DO センサー        | 溶存酸素       | mg/L    | ADC              |
| EC センサー        | 電気伝導率     | μS/cm   | ADC              |

## センサー追加手順

1. `packages/contracts/metrics.ts` にメトリクス定義を追加
2. `packages/contracts/topics.ts` に必要ならトピックを追加
3. `apps/pi-agent/src/` にセンサー読み取りロジックを実装
4. `apps/ingester/src/` にパース・書き込みロジックを追加
5. Grafana ダッシュボードにパネルを追加
