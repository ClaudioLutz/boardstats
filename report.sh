#!/usr/bin/env bash
# ============================================================
#  boardstats /biz/ - Lagebericht (hp-ubuntu)
#
#  Laeuft abends nach dem 20:20-Crawl und versendet den Bericht per SMTP.
#  Bewusst auf dem Server und nicht auf dem Windows-Laptop: so kommt der
#  Bericht auch dann, wenn der Laptop aus ist.
#
#  Voraussetzungen (einmalig einzurichten):
#    1. claude ist angemeldet   -> claude  (interaktiv, einmalig)
#    2. ~/.config/boardstats/mail.env mit den SMTP-Zugangsdaten, chmod 600
# ============================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

# nvm-Node 22: Claude Code verlangt >= 22, das System-Node ist 18.
export NVM_DIR="$HOME/.nvm"
# shellcheck disable=SC1091
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" --no-use
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
