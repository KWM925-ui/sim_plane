# Bash helper library. Source this file from executable scripts; do not run it directly.

wait_for_pid_exit() {
  local pid="${1:-}"
  local attempts="${2:-10}"
  local sleep_s="${3:-0.5}"
  local i

  if [[ -z "$pid" ]]; then
    return 0
  fi

  for ((i = 0; i < attempts; i++)); do
    if ! kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    sleep "$sleep_s"
  done
  return 1
}

stop_pid_gracefully() {
  local pid="${1:-}"

  if [[ -z "$pid" ]]; then
    return 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    wait "$pid" 2>/dev/null || true
    return 0
  fi

  kill -INT "$pid" 2>/dev/null || true
  if wait_for_pid_exit "$pid" 10 0.5; then
    wait "$pid" 2>/dev/null || true
    return 0
  fi

  kill -TERM "$pid" 2>/dev/null || true
  if wait_for_pid_exit "$pid" 6 0.5; then
    wait "$pid" 2>/dev/null || true
    return 0
  fi

  kill -KILL "$pid" 2>/dev/null || true
  wait_for_pid_exit "$pid" 4 0.25 || true
  wait "$pid" 2>/dev/null || true
}

stop_pid_list_gracefully() {
  local pid
  for pid in "$@"; do
    stop_pid_gracefully "$pid"
  done
}
