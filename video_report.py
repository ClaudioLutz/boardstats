#!/usr/bin/env python3
"""Vertont den taeglichen /biz/-Lagebericht und laedt ihn als YouTube-Video hoch.

Eigenstaendiger vierter Pipeline-Schritt, absichtlich entkoppelt von
run_report.py: liest nur das bereits oeffentlich abgelegte
extrakte/<datum>/bericht.md (Ergebnis von bericht_zu_markdown()) und kann
daher unabhaengig scheitern, ohne den bestehenden, funktionierenden
E-Mail-Versand zu gefaehrden.

v1 bewusst minimal: keine dynamischen Bilder/Avatare (eine generierte
Standbild-Titelkarte per ffmpeg drawtext), keine eingebrannten Untertitel,
kein Glossar in der Vertonung.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

import youtube_auth

BASE = Path(__file__).parent
EXTRAKTE = BASE / "extrakte"
VIDEO_DIR = BASE / "video"
STIMME = "de-DE-KatjaNeural"
FONT_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def edge_tts_pfad() -> str:
    p = os.environ.get("EDGE_TTS_BIN")
    if p:
        return p
    kandidat = Path.home() / ".local" / "bin" / "edge-tts"
    if kandidat.exists():
        return str(kandidat)
    gefunden = shutil.which("edge-tts")
    if not gefunden:
        raise SystemExit("edge-tts nicht gefunden - pipx install edge-tts oder EDGE_TTS_BIN setzen")
    return gefunden


def font_pfad() -> str:
    for f in FONT_KANDIDATEN:
        if Path(f).exists():
            return f
    raise SystemExit(f"keine der FONT_KANDIDATEN gefunden: {FONT_KANDIDATEN}")


# ----------------------------------------------------------- Text-Bereinigung

_URL_ZEILE = re.compile(r"^(?:https?://\S+(?:\s+und\s+)?)+$")
_QUELLEN_ZEILE = re.compile(r"^(Quelle|Quellen|Belege):", re.IGNORECASE)


def text_fuer_tts(markdown: str) -> str:
    """Reduziert den veroeffentlichten bericht.md-Text auf das Vorlesbare.

    Markdown-Syntax (Titel, Archiv-Link, Trennlinie, ##-Ueberschriften) kann
    man nicht hoeren; Quell-/Beleg-Zeilen und nackte Thread-URLs sind fuer
    einen Leser gedacht, der klicken kann, nicht fuer einen Zuhoerer. Das
    GLOSSAR ist zum Nachschlagen gedacht, nicht zum Anhoeren, und entfaellt
    komplett - es bleibt oeffentlich im bericht.md sichtbar."""
    zeilen = markdown.splitlines()
    ergebnis: list[str] = []
    for i, zeile in enumerate(zeilen):
        z = zeile.strip()
        if i == 0 and z.startswith("# "):
            continue
        if z.startswith("## GLOSSAR"):
            break
        if not z or z == "---":
            continue
        if z.startswith("[") and "](README.md)" in z:
            continue
        if z.startswith("*Datenstand:") and z.endswith("*"):
            continue
        if _URL_ZEILE.match(z):
            continue
        if _QUELLEN_ZEILE.match(z):
            continue
        if z.startswith("## "):
            z = z[3:]
        ergebnis.append(z)
    return "\n\n".join(ergebnis)


# ----------------------------------------------------------- TTS + Video

def tts_erzeugen(text: str, ziel_mp3: Path) -> None:
    subprocess.run(
        [edge_tts_pfad(), "--voice", STIMME, "--text", text, "--write-media", str(ziel_mp3)],
        check=True, timeout=300)


def video_erzeugen(audio_mp3: Path, titelkarte_text: str, ziel_mp4: Path) -> None:
    text_escaped = titelkarte_text.replace(":", r"\:").replace("'", r"\'")
    drawtext = (
        f"drawtext=fontfile={font_pfad()}:text='{text_escaped}':"
        "fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2"
    )
    subprocess.run(
        ["ffmpeg", "-y",
         "-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1280x720",
         "-i", str(audio_mp3),
         "-vf", drawtext,
         "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
         "-shortest", str(ziel_mp4)],
        check=True, timeout=600)


# ----------------------------------------------------------- Orchestrierung

def main() -> None:
    datum = date.today().isoformat()
    tag_dir = EXTRAKTE / datum
    bericht_pfad = tag_dir / "bericht.md"
    marker_pfad = tag_dir / "video.json"

    if not bericht_pfad.exists():
        print(f"kein Bericht fuer {datum} unter {bericht_pfad} - nichts zu tun")
        return
    if marker_pfad.exists():
        print(f"Video fuer {datum} schon hochgeladen: {marker_pfad}")
        return

    markdown = bericht_pfad.read_text(encoding="utf-8")
    text = text_fuer_tts(markdown)

    arbeit = VIDEO_DIR / datum
    arbeit.mkdir(parents=True, exist_ok=True)
    audio_mp3 = arbeit / "audio.mp3"
    video_mp4 = arbeit / "video.mp4"

    titel = f"/biz/-Lagebericht {datum}"
    print("erzeuge Vertonung ...")
    tts_erzeugen(text, audio_mp3)
    print("baue Video ...")
    video_erzeugen(audio_mp3, titel, video_mp4)

    beschreibung = (
        f"Automatisierter Lagebericht aus dem 4chan-Board /biz/ (Business & "
        f"Finance) vom {datum}. Diskurs-Dokumentation, keine Anlageberatung.\n\n"
        f"Vollstaendiger Text mit Quellen: "
        f"https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/{datum}/bericht.md"
    )
    print("lade auf YouTube hoch ...")
    video_id, url = youtube_auth.hochladen(video_mp4, titel, beschreibung)
    marker_pfad.write_text(json.dumps({"video_id": video_id, "url": url}, indent=2), encoding="utf-8")
    print(f"hochgeladen: {url}")


if __name__ == "__main__":
    main()
