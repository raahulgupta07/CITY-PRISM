#!/usr/bin/env bash
# Starts the fake OpenRouter and the app on a fresh database, for the browser tests.
# Build the screens first (npm run build). Uses the Python in backend/.venv.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
py="$root/backend/.venv/bin"
data="$(mktemp -d)"
trap 'kill 0; rm -rf "$data"' EXIT

(cd "$root/e2e" && "$py/uvicorn" fake_openrouter:app --port 9998 --log-level warning) &

cd "$root/backend"
ENV=dev DATA_DIR="$data" FRONTEND_BUILD_DIR="$root/build" \
	OPENROUTER_API_KEY=test OPENROUTER_BASE_URL=http://127.0.0.1:9998/api/v1 \
	LLM_MODEL_FAST=test-fast LLM_MODEL_DEFAULT=test-default NO_PROXY=127.0.0.1 \
	"$py/uvicorn" app.main:app --port 8081 --log-level warning &
wait
