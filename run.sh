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
    # Frueheste und haeufigste Stelle im Cron-Tag (3x taeglich) - haelt
    # hp-ubuntu nah an main, statt dass Aenderungen erst beim naechsten
    # manuellen Pull ankommen. --ff-only statt etwas zu ueberschreiben; ein
    # Fehlschlag darf den Crawl nicht stoppen.
    git pull --ff-only || echo "WARNUNG: git pull fehlgeschlagen - laeuft mit dem lokalen Stand weiter"
    python3 crawl_biz.py
    python3 aggregate_biz.py
    echo "===== Lauf beendet:  $(date '+%Y-%m-%d %H:%M:%S') ====="
} >> "$LOG" 2>&1
