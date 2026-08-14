#!/usr/bin/env bash
# ============================================================
#  boardstats /biz/ - Lagebericht: YouTube-Video (hp-ubuntu)
#
#  Vertont den bereits veroeffentlichten Tagesbericht (extrakte/<datum>/
#  bericht.md) und laedt ihn als unlisted YouTube-Video hoch. Bewusst
#  entkoppelt von report.sh (eigener Cron-Eintrag, eigenes Log): ein
#  Fehler hier (TTS/ffmpeg/Upload) darf den funktionierenden E-Mail-Versand
#  nicht gefaehrden.
#
#  Voraussetzungen (einmalig einzurichten):
#    1. pipx install edge-tts   (installiert nach ~/.local/bin)
#    2. ffmpeg ist installiert  -> ffmpeg -version
#    3. ~/.config/boardstats/youtube_client.json (OAuth-Client aus Google
#       Cloud Console) und youtube_token.json (per youtube_auth_setup.py
#       einmalig interaktiv erzeugt)
# ============================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

# pipx installiert edge-tts nach ~/.local/bin, das ist im Cron-PATH nicht
# enthalten (gleicher Grund wie die Node-PATH-Erweiterung in report.sh).
export PATH="$HOME/.local/bin:$PATH"

mkdir -p logs
LOG="logs/video_cron.log"
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 5242880 ]; then
    mv "$LOG" "$LOG.1"
fi

{
    echo "===== Video gestartet: $(date '+%Y-%m-%d %H:%M:%S') ====="
    python3 video_report.py
    echo "===== Video beendet:  $(date '+%Y-%m-%d %H:%M:%S') ====="
} >> "$LOG" 2>&1
