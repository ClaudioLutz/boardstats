#!/usr/bin/env python3
"""Vertont den taeglichen /biz/-Lagebericht und laedt ihn als YouTube-Video hoch.

Eigenstaendiger vierter Pipeline-Schritt, absichtlich entkoppelt von
run_report.py: liest nur das bereits oeffentlich abgelegte
extrakte/<datum>/bericht.md (Ergebnis von bericht_zu_markdown()) und kann
daher unabhaengig scheitern, ohne den bestehenden, funktionierenden
E-Mail-Versand zu gefaehrden.

v2: der Text scrollt kontinuierlich als Untertitel-Video (.ass, per ffmpeg
libass eingebrannt), das jeweils gesprochene Wort wird farblich
hervorgehoben. Jede Zeile ist eine eigenstaendige, in sich geschlossene
Scroll-Bewegung (von unten ins Bild bis oben hinaus) - dadurch bleibt die
Wort-Hervorhebung immer exakt deckungsgleich mit der Zeile, unabhaengig von
Sprechtempo-Schwankungen zwischen Zeilen.
"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import ImageFont

import youtube_auth

BASE = Path(__file__).parent
EXTRAKTE = BASE / "extrakte"
VIDEO_DIR = BASE / "video"
STIMME = "de-DE-KatjaNeural"
FONT_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

CANVAS_W = 1280
CANVAS_H = 720
FONTSIZE = 44
ZEILENHOEHE = 64
ZEILENBREITE_MAX = int(CANVAS_W * 0.88)
LEAD_IN_S = 2.5
LEAD_OUT_S = 2.5
FARBE_TEXT = "&H00FFFFFF&"
FARBE_AKZENT = "&H0066D1FF&"
HINTERGRUND = "0x1a1a2e"


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


# ----------------------------------------------------------- TTS mit Wort-Zeitstempeln

@dataclass
class Wort:
    text: str
    start: float
    end: float


def tts_mit_worten(text: str, ziel_mp3: Path) -> list[Wort]:
    """Vertont text und liefert dabei pro gesprochenem Wort Start/Ende (Sekunden).

    Nutzt die edge-tts-Bibliothek direkt (nicht die CLI), weil nur der
    Python-API-Stream WordBoundary-Ereignisse mit Zeitstempeln liefert."""
    import edge_tts

    async def _lauf() -> list[Wort]:
        communicate = edge_tts.Communicate(text, STIMME, boundary="WordBoundary")
        worte: list[Wort] = []
        with open(ziel_mp3, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    worte.append(Wort(
                        text=chunk["text"],
                        start=chunk["offset"] / 1e7,
                        end=(chunk["offset"] + chunk["duration"]) / 1e7,
                    ))
        return worte

    return asyncio.run(_lauf())


# ----------------------------------------------------------- Zeilenumbruch

@dataclass
class Zeile:
    worte: list[Wort]

    @property
    def start(self) -> float:
        return self.worte[0].start

    @property
    def end(self) -> float:
        return self.worte[-1].end

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.worte)


def in_zeilen_umbrechen(worte: list[Wort], font: ImageFont.FreeTypeFont) -> list[Zeile]:
    zeilen: list[Zeile] = []
    aktuell: list[Wort] = []
    for wort in worte:
        kandidat = aktuell + [wort]
        breite = font.getlength(" ".join(w.text for w in kandidat))
        if aktuell and breite > ZEILENBREITE_MAX:
            zeilen.append(Zeile(aktuell))
            aktuell = [wort]
        else:
            aktuell = kandidat
    if aktuell:
        zeilen.append(Zeile(aktuell))
    return zeilen


# ----------------------------------------------------------- .ass-Untertitel

_ASS_SPECIAL = re.compile(r"([{}\\])")


def _ass_escape(text: str) -> str:
    return _ASS_SPECIAL.sub(r"\\\1", text)


def _ass_zeit(sekunden: float) -> str:
    cs = round(max(0.0, sekunden) * 100)
    h, rest = divmod(cs, 360000)
    m, rest = divmod(rest, 6000)
    s, cs = divmod(rest, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {CANVAS_W}
PlayResY: {CANVAS_H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Report,DejaVu Sans,{FONTSIZE},{FARBE_TEXT},{FARBE_TEXT},&H00000000&,&H00000000&,-1,0,0,0,100,100,0,0,1,2,0,8,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ass_erzeugen(zeilen: list[Zeile], font: ImageFont.FreeTypeFont, ziel_ass: Path) -> None:
    """Baut pro Zeile eine eigenstaendige Scroll-Bewegung (unten rein, oben raus).

    Jede Zeile wird wortweise gerendert (nicht als ein zusammenhaengender
    String) und die Hervorhebung nutzt exakt dieselben x-Positionen wie die
    weisse Basis-Darstellung desselben Worts - PIL (Zeilenumbruch/Metriken)
    und libass/HarfBuzz (tatsaechliches Rendering) shapen Text sonst leicht
    unterschiedlich, was bei laengeren Zeilen zu sichtbarem Positionsdrift
    zwischen Overlay und Basistext fuehrt, wenn man die Zeile als ein Stueck
    misst und einzeln ueberlagert."""
    y_enter = CANVAS_H + ZEILENHOEHE
    y_exit = -ZEILENHOEHE
    events: list[str] = []

    for zeile in zeilen:
        fenster_start = max(0.0, zeile.start - LEAD_IN_S)
        fenster_end = zeile.end + LEAD_OUT_S
        dauer = fenster_end - fenster_start
        if dauer <= 0:
            continue

        def y_bei(t: float, _start: float = fenster_start, _dauer: float = dauer) -> float:
            anteil = (t - _start) / _dauer
            return y_enter + (y_exit - y_enter) * anteil

        wort_breiten = [font.getlength(w.text) for w in zeile.worte]
        leerzeichen_breite = font.getlength(" ") * 0.6
        gesamtbreite = sum(wort_breiten) + leerzeichen_breite * (len(zeile.worte) - 1)
        cursor = (CANVAS_W - gesamtbreite) / 2

        y1_zeile = y_bei(fenster_start)
        y2_zeile = y_bei(fenster_end)

        for wort, wort_breite in zip(zeile.worte, wort_breiten):
            mitte_x = cursor + wort_breite / 2
            cursor += wort_breite + leerzeichen_breite
            wort_text = _ass_escape(wort.text)

            events.append(
                f"Dialogue: 0,{_ass_zeit(fenster_start)},{_ass_zeit(fenster_end)},Report,,0,0,0,,"
                f"{{\\move({mitte_x:.0f},{y1_zeile:.0f},{mitte_x:.0f},{y2_zeile:.0f})}}"
                f"{wort_text}"
            )

            w_start = max(fenster_start, wort.start)
            w_end = max(w_start + 0.01, min(fenster_end, wort.end))
            y1 = y_bei(w_start)
            y2 = y_bei(w_end)
            events.append(
                f"Dialogue: 1,{_ass_zeit(w_start)},{_ass_zeit(w_end)},Report,,0,0,0,,"
                f"{{\\move({mitte_x:.0f},{y1:.0f},{mitte_x:.0f},{y2:.0f})\\c{FARBE_AKZENT}}}"
                f"{wort_text}"
            )

    ziel_ass.write_text(ASS_HEADER + "\n".join(events) + "\n", encoding="utf-8")


# ----------------------------------------------------------- Video-Zusammenbau

def video_erzeugen(audio_mp3: Path, ass_datei: Path, ziel_mp4: Path) -> None:
    ass_arg = str(ass_datei).replace("\\", "/").replace(":", r"\:")
    subprocess.run(
        ["ffmpeg", "-y",
         "-f", "lavfi", "-i", f"color=c={HINTERGRUND}:s={CANVAS_W}x{CANVAS_H}",
         "-i", str(audio_mp3),
         "-vf", f"ass={ass_arg}",
         "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
         "-shortest", str(ziel_mp4)],
        check=True, timeout=1200)


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
    ass_datei = arbeit / "untertitel.ass"
    video_mp4 = arbeit / "video.mp4"

    titel = f"/biz/-Lagebericht {datum}"
    print("erzeuge Vertonung mit Wort-Zeitstempeln ...")
    worte = tts_mit_worten(text, audio_mp3)
    print(f"{len(worte)} Woerter erkannt")

    font = ImageFont.truetype(font_pfad(), FONTSIZE)
    zeilen = in_zeilen_umbrechen(worte, font)
    print(f"{len(zeilen)} Zeilen")
    ass_erzeugen(zeilen, font, ass_datei)

    print("baue Video ...")
    video_erzeugen(audio_mp3, ass_datei, video_mp4)

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
