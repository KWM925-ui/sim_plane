#!/usr/bin/env bash

# This file is sourced by manual probe runners. The open flock stays owned by
# the runner process until it exits, so hygiene can distinguish active probes.

MANUAL_PROBE_LOCK_FD=""

manual_probe_start() {
  local probe_dir="$1"
  mkdir -p "$probe_dir"
  exec {MANUAL_PROBE_LOCK_FD}>"$probe_dir/.probe.lock"
  if ! flock -n "$MANUAL_PROBE_LOCK_FD"; then
    echo "manual probe directory is already active: $probe_dir" >&2
    return 1
  fi
  local marker_tmp="$probe_dir/.running.tmp.$$"
  printf '{"schema_version":1,"state":"running","pid":%s,"started_at_utc":"%s"}\n' \
    "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$marker_tmp"
  mv "$marker_tmp" "$probe_dir/.running"
}

manual_probe_complete() {
  local probe_dir="$1"
  local status="$2"
  local marker_tmp="$probe_dir/.complete.tmp.$$"
  printf '{"schema_version":1,"state":"complete","status":"%s","pid":%s,"completed_at_utc":"%s"}\n' \
    "$status" "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$marker_tmp"
  mv "$marker_tmp" "$probe_dir/.complete"
  rm -f "$probe_dir/.running"
}
