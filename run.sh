#!/usr/bin/env bash
# ============================================================
#  boardstats /biz/ — Cron-Wrapper (hp-ubuntu)
#  Crawlt einen Snapshot und verdichtet ihn zu reports/latest.json.
#  Zeitversetzt zur vollen Stunde planen, damit sich der Crawl nicht
#  mit anderen 4chan-Jobs ueberschneidet (API-Limit: 1 Request/Sekunde).
#
#  Aufruf:
#    run.sh              Crawl + Verdichtung (aggregate_biz.py) - 3x taeglich
#    run.sh crawl-only   nur Crawl - stuendlich, fuer die feine Zeitreihe
#
#  Warum getrennt: aggregate_biz.py fuehrt mit seen.json einen Novelty-Zustand
#  ueber die Laeufe ("bereits gemeldet") und speist reports/latest.json, das in
#  den Tagesbericht eingeht. Stuendlich verdichten wuerde diesen Zustand 8x so
#  schnell fortschreiben und damit den Berichtspfad veraendern - der Crawl
#  selbst ist zustandslos und darf beliebig oft laufen.
# ============================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
mkdir -p logs
MODUS="${1:-voll}"
# Eigenes Log fuer die stuendlichen Laeufe, sonst ertraenken 24 Crawl-Eintraege
# pro Tag die drei Verdichtungslaeufe, an denen der Bericht haengt.
if [ "$MODUS" = "crawl-only" ]; then
    LOG="logs/crawl.log"
else
    LOG="logs/cron.log"
fi

if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 5242880 ]; then
    mv "$LOG" "$LOG.1"
fi

{
    echo "===== Lauf gestartet: $(date '+%Y-%m-%d %H:%M:%S') ====="
    # Frueheste und haeufigste Stelle im Cron-Tag (seit 22.08.2026 stuendlich) - haelt
    # hp-ubuntu nah an main, statt dass Aenderungen erst beim naechsten
    # manuellen Pull ankommen. --ff-only statt etwas zu ueberschreiben; ein
    # Fehlschlag darf den Crawl nicht stoppen.
    git pull --ff-only || echo "WARNUNG: git pull fehlgeschlagen - laeuft mit dem lokalen Stand weiter"
    python3 crawl_biz.py
    if [ "$MODUS" != "crawl-only" ]; then
        python3 aggregate_biz.py
    fi
    echo "===== Lauf beendet:  $(date '+%Y-%m-%d %H:%M:%S') ====="
} >> "$LOG" 2>&1
