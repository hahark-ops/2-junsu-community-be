#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT_DIR}"
docker compose up -d --build
docker compose ps

echo
echo "FE: http://localhost:3000"
echo "BE: http://localhost:8000"
