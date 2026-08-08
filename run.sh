#!/usr/bin/env bash
# ============================================================
#  boardstats /biz/ — Cron-Wrapper (hp-ubuntu)
#  Crawlt einen Snapshot und verdichtet ihn zu reports/latest.json.
#  Zeitversetzt zur vollen Stunde planen, damit sich der Crawl nicht
#  mit anderen 4chan-Jobs ueberschneidet (API-Limit: 1 Request/Sekunde).
# ============================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
mkdir -p logs
LOG="logs/cron.log"

if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 5242880 ]; then
    mv "$LOG" "$LOG.1"
fi

{
    echo "===== Lauf gestartet: $(date '+%Y-%m-%d %H:%M:%S') ====="
    python3 crawl_biz.py
    python3 aggregate_biz.py
    echo "===== Lauf beendet:  $(date '+%Y-%m-%d %H:%M:%S') ====="
} >> "$LOG" 2>&1
