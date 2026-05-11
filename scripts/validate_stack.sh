#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

required_containers=(redpanda timescaledb rust_ingestor zscore_processor grafana)

for container in "${required_containers[@]}"; do
  running="$(docker inspect --format='{{.State.Running}}' "$container")"
  if [[ "$running" != "true" ]]; then
    echo "Container is not running: $container" >&2
    exit 1
  fi
done

curl --fail --silent http://localhost:3000/api/health >/dev/null

db_row_count="$(docker exec timescaledb psql -U "${DB_USER:-postgres}" -d "${DB_NAME:-market_data}" -tAc "SELECT count(*) FROM trades;")"
if [[ -z "$db_row_count" ]]; then
  echo "Failed to query trades row count." >&2
  exit 1
fi

grafana_datasources="$(curl --fail --silent -u "admin:${GF_PASSWORD:-password}" http://localhost:3000/api/datasources)"
if [[ "$grafana_datasources" != *"timescaledb"* ]]; then
  echo "Provisioned Grafana datasource not found." >&2
  exit 1
fi

dashboard_search="$(curl --fail --silent -u "admin:${GF_PASSWORD:-password}" "http://localhost:3000/api/search?query=QuantStream")"
if [[ "$dashboard_search" != *"QuantStream Overview"* ]]; then
  echo "Provisioned Grafana dashboard not found." >&2
  exit 1
fi

if [[ "${1:-}" == "--require-data" && "$db_row_count" -lt 1 ]]; then
  echo "Trades table is still empty." >&2
  exit 1
fi

anomaly_count="$(docker exec timescaledb psql -U "${DB_USER:-postgres}" -d "${DB_NAME:-market_data}" -tAc "SELECT count(*) FROM anomalies;")"

printf 'Validation passed: trades=%s anomalies=%s\n' "$db_row_count" "$anomaly_count"
