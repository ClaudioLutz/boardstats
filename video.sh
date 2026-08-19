#!/usr/bin/env bash
# ============================================================
#  boardstats /biz/ - Lagebericht: YouTube-Video (hp-ubuntu)
#
#  Vertont den bereits veroeffentlichten Tagesbericht (extrakte/<datum>/
#  bericht.md, seit 16.08.2026 englisch) und laedt ihn als YouTube-Video
#  hoch. Bewusst entkoppelt von report.sh (eigener Cron-Eintrag, eigenes
#  Log): ein Fehler hier (TTS/ffmpeg/Upload) darf die Berichts-
#  Veroeffentlichung nicht gefaehrden.
#
#  Voraussetzungen (einmalig einzurichten):
#    1. venv ~/.venvs/boardstats-video mit edge-tts + pillow
#       (python3 -m venv ~/.venvs/boardstats-video && .../pip install
#        edge-tts pillow) - noetig, weil video_report.py die edge-tts-
#       Python-Bibliothek direkt nutzt (Wort-Zeitstempel fuer Karaoke-Scroll)
#       und Pillow fuer Textmetriken braucht; beides via pip statt apt/pipx,
#       da es Bibliotheken und keine CLI-Tools sind.
#    1b. optional: zusaetzlich `pip install matplotlib` im selben venv fuer
#        die Board-Aktivitaets-Balkengrafik im Outro (aktivitaet.py, seit
#        18.08.2026). Ohne matplotlib ueberspringt szenen_bauen() diesen
#        einen Beat automatisch (eigenes try/except) - der Rest des Videos
#        laeuft unveraendert, es fehlt nur die Grafik.
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
    # Ohne diesen Pull lief hp-ubuntu wiederholt tagelang auf einem Stand
    # zurueck, waehrend main schon weiter war (August 2026: mehrfach von Hand
    # nachgezogen). --ff-only verweigert bei lokalen Aenderungen/Konflikten
    # statt etwas zu ueberschreiben; ein Fehlschlag hier darf den Lauf nicht
    # stoppen (lieber mit dem alten Stand rendern als gar kein Video).
    git pull --ff-only || echo "WARNUNG: git pull fehlgeschlagen - baue mit dem lokalen Stand weiter"
    # Seit 16.08.2026 ist die ganze Pipeline englisch; --sprache en ist die
    # einzige Konfiguration (eine deutsche Berichtsfassung existiert nicht
    # mehr, seit die Synthese direkt auf Englisch laeuft).
    "$VENV_PY" video_report.py --sprache en || echo "Video fehlgeschlagen (Status $?)"
    # Rohclips des WebM/MP4-Katalogs aufraeumen (Katalog-Eintrag bleibt) -
    # an denselben Lauf gebunden, der sie zuletzt gebraucht haben koennte,
    # statt eines eigenen Cron-Eintrags. Ein Fehlschlag hier darf das
    # bereits fertige Video nicht nachtraeglich als gescheitert markieren.
    "$VENV_PY" klip_katalog.py || echo "Clip-Bereinigung fehlgeschlagen (Status $?)"
    echo "===== Video beendet:  $(date '+%Y-%m-%d %H:%M:%S') ====="
} >> "$LOG" 2>&1
