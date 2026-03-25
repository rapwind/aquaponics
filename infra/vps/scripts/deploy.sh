#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/app/deploy/aquaponics"
REPO_DIR="${BASE_DIR}/repo"
ENV_FILE="${BASE_DIR}/env/app.env"
COMPOSE_DIR="${REPO_DIR}/infra/vps"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: env file not found: ${ENV_FILE}"
  exit 1
fi

if [[ ! -d "${REPO_DIR}" ]]; then
  echo "ERROR: repo dir not found: ${REPO_DIR}"
  exit 1
fi

if [[ -z "${GHCR_USER:-}" || -z "${GHCR_TOKEN:-}" ]]; then
  echo "ERROR: GHCR_USER / GHCR_TOKEN is not set"
  exit 1
fi

echo "=== git sync ==="
cd "${REPO_DIR}"
git fetch origin
git checkout main
git pull --ff-only origin main

echo "=== ghcr login ==="
echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USER}" --password-stdin

echo "=== docker compose pull ==="
cd "${COMPOSE_DIR}"
docker compose --env-file "${ENV_FILE}" pull

echo "=== docker compose up -d ==="
docker compose --env-file "${ENV_FILE}" up -d

echo "=== image cleanup ==="
docker image prune -af || true

echo "=== done ==="
