#!/usr/bin/env bash
set -euo pipefail

if ! command -v opencode >/dev/null 2>&1; then
  echo "opencode CLI not found in PATH" >&2
  exit 1
fi

HOST="${OPENCODE_SMOKE_HOST:-127.0.0.1}"
PORT="${OPENCODE_SMOKE_PORT:-}"
if [[ -z "${PORT}" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
  if [[ -z "${PYTHON_BIN}" ]]; then
    echo "python3 (or python) is required to allocate a free port" >&2
    exit 1
  fi
  PORT="$("${PYTHON_BIN}" - <<'PY'
import socket

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
)"
fi

LOG_FILE="$(mktemp -t opencode-serve-smoke.XXXXXX.log)"
SERVER_PID=""

cleanup() {
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
  rm -f "${LOG_FILE}"
}
trap cleanup EXIT INT TERM

echo "[opencode-smoke] opencode version:"
opencode --version

BASE_URL="http://${HOST}:${PORT}"
echo "[opencode-smoke] starting server at ${BASE_URL}"
opencode serve --hostname "${HOST}" --port "${PORT}" --print-logs >"${LOG_FILE}" 2>&1 &
SERVER_PID="$!"

for _ in $(seq 1 60); do
  if ! kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    echo "[opencode-smoke] server exited before health check" >&2
    cat "${LOG_FILE}" >&2
    exit 1
  fi

  health_json="$(curl -fsS "${BASE_URL}/global/health" 2>/dev/null || true)"
  if [[ "${health_json}" == *"\"healthy\":true"* ]]; then
    echo "[opencode-smoke] health endpoint reachable: ${health_json}"
    echo "[opencode-smoke] PASS"
    exit 0
  fi
  sleep 0.2
done

echo "[opencode-smoke] timed out waiting for /global/health" >&2
cat "${LOG_FILE}" >&2
exit 1
