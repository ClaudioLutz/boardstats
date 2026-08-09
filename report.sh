#!/usr/bin/env bash
# ============================================================
#  boardstats /biz/ - Lagebericht (hp-ubuntu)
#
#  Versendet den Bericht per SMTP. Bewusst auf dem Server und nicht auf
#  dem Windows-Laptop: so kommt der Bericht auch dann, wenn der Laptop
#  aus ist.
#
#  Voraussetzungen (einmalig einzurichten):
#    1. claude ist angemeldet   -> claude  (interaktiv, einmalig)
#    2. ~/.config/boardstats/mail.env mit den SMTP-Zugangsdaten, chmod 600
# ============================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

# Nur den PATH um Node 22 (nvm) erweitern - claude selbst braucht das,
# python3/run_report.py findet die Binary auch so ueber claude_pfad().
# BEWUSST NICHT `. nvm.sh` sourcen: das lief am 08.08. um 21:00 spurlos
# gegen `set -e` - Cron bestaetigte den Start, aber report_cron.log blieb
# leer und "No MTA installed, discarding output" zeigte unabgefangenen
# Output vor der eigenen Log-Umleitung. nvm.sh kann beim Sourcen intern
# einen Nicht-Null-Status hinterlassen, den `[ -s ... ] &&` dann als
# Fehlschlag des ganzen Befehls wertet - unter `set -e` toedlich, und
# fuer diesen Zweck ohnehin unnoetig: es wird nur der PATH gebraucht.
export PATH="$HOME/.nvm/versions/node/v22.23.2/bin:$PATH"

mkdir -p logs
LOG="logs/report_cron.log"
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 5242880 ]; then
    mv "$LOG" "$LOG.1"
fi

{
    echo "===== Bericht gestartet: $(date '+%Y-%m-%d %H:%M:%S') ====="
    python3 run_report.py --top 15 --versand smtp
    echo "===== Bericht beendet:  $(date '+%Y-%m-%d %H:%M:%S') ====="
} >> "$LOG" 2>&1
