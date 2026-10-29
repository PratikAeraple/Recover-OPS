#!/usr/bin/env bash
set -euo pipefail

# Read-only, deliberately small local host snapshot. No service names or logs are sent anywhere.
printf 'captured_utc='; date -u +%Y-%m-%dT%H:%M:%SZ
printf 'hostname='; hostname -s
printf 'uptime='; uptime -p
printf 'load='; awk '{print $1, $2, $3}' /proc/loadavg
printf 'memory_kib='; awk '/MemTotal:|MemAvailable:/ {printf "%s=%s ", $1, $2} END {print ""}' /proc/meminfo
printf 'root_filesystem='; df -P / | awk 'NR==2 {print "size=" $2 " used=" $3 " available=" $4 " use=" $5}'
for unit in docker.service ssh.service; do
  if command -v systemctl >/dev/null 2>&1; then
    state=$(systemctl is-active "$unit" 2>/dev/null || true)
    printf 'unit_%s=%s\n' "$unit" "${state:-unknown}"
  fi
done
