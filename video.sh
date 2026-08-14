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
#    1. venv ~/.venvs/boardstats-video mit edge-tts + pillow
#       (python3 -m venv ~/.venvs/boardstats-video && .../pip install
#        edge-tts pillow) - noetig, weil video_report.py die edge-tts-
#       Python-Bibliothek direkt nutzt (Wort-Zeitstempel fuer Karaoke-Scroll)
#       und Pillow fuer Textmetriken braucht; beides via pip statt apt/pipx,
#       da es Bibliotheken und keine CLI-Tools sind.
#    2. ffmpeg ist installiert (mit libass)  -> ffmpeg -version
#    3. ~/.config/boardstats/youtube_client.json (OAuth-Client aus Google
#       Cloud Console) und youtube_token.json (per youtube_auth_setup.py
#       einmalig interaktiv erzeugt)
# ============================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

VENV_PY="$HOME/.venvs/boardstats-video/bin/python3"
if [ ! -x "$VENV_PY" ]; then
    echo "venv $VENV_PY fehlt - siehe Voraussetzungen oben" >&2
    exit 1
fi

mkdir -p logs
LOG="logs/video_cron.log"
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 5242880 ]; then
    mv "$LOG" "$LOG.1"
fi

{
    echo "===== Video gestartet: $(date '+%Y-%m-%d %H:%M:%S') ====="
    "$VENV_PY" video_report.py
    echo "===== Video beendet:  $(date '+%Y-%m-%d %H:%M:%S') ====="
} >> "$LOG" 2>&1
