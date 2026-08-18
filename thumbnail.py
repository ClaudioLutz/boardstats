#!/usr/bin/env python3
"""Baut das YouTube-Vorschaubild des Tages.

Fester Serienrahmen (dunkler Grund, Amber-Akzent, Kopf- und Fusszeile),
links der Tages-Aufhaenger in grosser Schrift, rechts ein Bildmotiv. Das
Motiv ist entweder das vom Report-Lauf gepruefte Board-Bild des Tages oder
das statische Serienbild aus assets/ - der Rahmen bleibt in beiden Faellen
derselbe, damit die Reihe wiedererkennbar bleibt.

Bewusst ohne Netzzugriff und ohne Kenntnis der uebrigen Pipeline: das Modul
bekommt Text und Motiv gereicht und gibt eine JPEG-Datei zurueck.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

import design_tokens

BREITE = 1280
HOEHE = 720
GRUND = design_tokens.NEUTRAL[9]      # derselbe Ton wie der Videohintergrund
AKZENT = design_tokens.AKZENT[6]      # amber, wie die Wort-Hervorhebung im Video
TEXT_HELL = design_tokens.WEISS
TEXT_GRAU = design_tokens.NEUTRAL[3]

MOTIV_BREITE = 560            # Bildflaeche rechts
MOTIV_BLENDE = 200            # weiche Kante zum Textbereich hin
MOTIV_FARBE = 0.55            # entsaettigt - das Motiv soll Hintergrund sein
MOTIV_HELLIGKEIT = 0.78

MARGIN = 64
BALKEN_BREITE = 12            # Akzentbalken links neben dem Aufhaenger
BALKEN_ABSTAND = 24
KOPF_Y = 62
FUSS_Y = HOEHE - 96
TEXT_OBEN = 170
TEXT_UNTEN = FUSS_Y - 24
ZEILEN_MAX = 3
GROESSEN = list(range(112, 43, -4))
ZEILEN_FAKTOR = 1.12

JPEG_QUALITAET = 88
MAX_BYTES = 2_000_000         # harte Grenze von thumbnails/set

# Videohintergrund: das Bild bleibt in voller Qualitaet sichtbar; lesbar
# wird der Untertiteltext durch einen dunklen Verlauf nur am unteren Rand
# (dort stehen die max. 3 Textzeilen, Oberkante ~524 px). Die Titelkarten
# oben bekommen ihre Abdunkelung als eigene Bande im ASS-Renderer, weil sie
# nur zeitweise eingeblendet sind.
HG_VERLAUF_START = 420        # y, ab dem der Verlauf einsetzt
HG_VERLAUF_VOLL = 560         # ab hier volle Deckung (Textzone ab ~524)
HG_VERLAUF_DECKUNG = 0.85     # Schwaerzung in der Textzone (0..1)

# Eigene Schriften liegen als .ttf direkt neben dem Code (assets/fonts/) -
# portabel zwischen Windows-Dev und Linux-Cron, kein apt-Paket noetig. Die
# Systemschriften bleiben als Fallback, falls das Verzeichnis mal fehlt.
# Space Grotesk (Display, fett) fuer Titel/Labels/Akzente und Inter
# (Grotesk, regulaer/medium) fuer Fliesstext sind zwei verschiedene
# Familien statt nur zweier Groessen derselben Schrift - das behebt die
# zuvor bemaengelte fehlende Typo-Hierarchie zwischen Titel und
# Stichpunkten. IBM Plex Mono ist der Tabellenziffern-Font fuer die
# Zahlen-Tafel/Countup: feste Ziffernbreite haelt das Hochzaehlen ruhig
# statt horizontal zu jittern. Alle vier liegen als statische Instanzen
# vor (per fonttools varLib.instancer aus den Google-Fonts-Variable-Fonts
# gezogen, siehe assets/fonts/OFL-*.txt) - matplotlib (aktivitaet.py) kann
# Font-Gewichte anders als Pillow nicht per Variable-Font-Achse waehlen,
# eine gemeinsame statische Datei pro Rolle vermeidet dieses Sonderproblem.
FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

FONT_FETT_KANDIDATEN = [
    str(FONT_DIR / "SpaceGrotesk-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
FONT_NORMAL_KANDIDATEN = [
    str(FONT_DIR / "Inter-Regular.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
FONT_MEDIUM_KANDIDATEN = [
    str(FONT_DIR / "Inter-Medium.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
FONT_MONO_KANDIDATEN = [
    str(FONT_DIR / "IBMPlexMono-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "C:/Windows/Fonts/consolab.ttf",
]


def _font_pfad(kandidaten: list[str]) -> str:
    for f in kandidaten:
        if Path(f).exists():
            return f
    raise RuntimeError(f"keiner der Font-Kandidaten gefunden: {kandidaten}")


def _lade_schrift(kandidaten: list[str], groesse: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_font_pfad(kandidaten), groesse)


def schrift(fett: bool, groesse: int) -> ImageFont.FreeTypeFont:
    """Zentrale Schriftrolle: fett=True die fette Display-Schrift (Titel,
    Labels, Akzente), fett=False die neutrale Grotesk fuer Fliesstext."""
    kandidaten = FONT_FETT_KANDIDATEN if fett else FONT_NORMAL_KANDIDATEN
    return _lade_schrift(kandidaten, groesse)


def schrift_mono(groesse: int) -> ImageFont.FreeTypeFont:
    """Tabellenziffern-Schrift fuer Zahlen-Tafel/Countup."""
    return _lade_schrift(FONT_MONO_KANDIDATEN, groesse)


def schrift_medium(groesse: int) -> ImageFont.FreeTypeFont:
    """Inter Medium statt Regular: fuer kleinen Kartentext (Stichpunkte in
    der Themen-Karte), der nach der YouTube-Kompression sonst duenn wirken
    kann - bleibt trotzdem klar von der fetten Space-Grotesk-Display-Rolle
    unterscheidbar, die Titel/Labels tragen."""
    return _lade_schrift(FONT_MEDIUM_KANDIDATEN, groesse)


def _motiv_flaeche(motiv: Path) -> Image.Image:
    """Motiv auf die Bildflaeche zuschneiden (cover), entsaettigen, abdunkeln
    und links weich auslaufen lassen."""
    bild: Image.Image = Image.open(motiv).convert("RGB")
    skala = max(MOTIV_BREITE / bild.width, HOEHE / bild.height)
    neu = (max(MOTIV_BREITE, int(bild.width * skala + 0.5)),
           max(HOEHE, int(bild.height * skala + 0.5)))
    bild = bild.resize(neu, Image.Resampling.LANCZOS)
    links = (bild.width - MOTIV_BREITE) // 2
    # Vertikal nicht mittig, sondern im oberen Drittel schneiden: bei
    # Board-Bildern steckt das Motiv haeufiger oben als in der Mitte.
    oben = min((bild.height - HOEHE) // 3, bild.height - HOEHE)
    bild = bild.crop((links, oben, links + MOTIV_BREITE, oben + HOEHE))
    bild = ImageEnhance.Color(bild).enhance(MOTIV_FARBE)
    return ImageEnhance.Brightness(bild).enhance(MOTIV_HELLIGKEIT)


def _blende() -> Image.Image:
    """Alpha-Maske: links durchsichtig, nach MOTIV_BLENDE Pixeln deckend."""
    maske = Image.new("L", (MOTIV_BREITE, HOEHE), 255)
    zeichnen = ImageDraw.Draw(maske)
    for x in range(MOTIV_BLENDE):
        zeichnen.line([(x, 0), (x, HOEHE)], fill=int(255 * x / MOTIV_BLENDE))
    return maske


def _umbrechen(text: str, font: ImageFont.FreeTypeFont, breite: int,
               zeichnen: ImageDraw.ImageDraw) -> list[str] | None:
    """Woerter auf Zeilen verteilen. None, wenn ein einzelnes Wort schon zu
    breit ist oder es mehr als ZEILEN_MAX Zeilen braucht."""
    zeilen: list[str] = []
    aktuell = ""
    for wort in text.split():
        kandidat = f"{aktuell} {wort}".strip()
        if aktuell and zeichnen.textlength(kandidat, font=font) > breite:
            zeilen.append(aktuell)
            aktuell = wort
        else:
            aktuell = kandidat
        if zeichnen.textlength(aktuell, font=font) > breite:
            return None  # ein Wort allein passt nicht
    if aktuell:
        zeilen.append(aktuell)
    return zeilen if 0 < len(zeilen) <= ZEILEN_MAX else None


def _passende_schrift(text: str, breite: int, hoehe: int,
                      zeichnen: ImageDraw.ImageDraw
                      ) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Groesste Schrift, in der der Aufhaenger in den Textblock passt."""
    for groesse in GROESSEN:
        font = schrift(True, groesse)
        zeilen = _umbrechen(text, font, breite, zeichnen)
        if zeilen and len(zeilen) * groesse * ZEILEN_FAKTOR <= hoehe:
            return font, zeilen
    # Reissleine: kleinste Groesse, hart auf ZEILEN_MAX Zeilen gekappt.
    font = schrift(True, GROESSEN[-1])
    zeilen = _umbrechen(text, font, breite, zeichnen) or [text[:18]]
    return font, zeilen[:ZEILEN_MAX]


def _bodenverlauf() -> Image.Image:
    """Alpha-Maske fuer den unteren Abdunkelungs-Verlauf: oben durchsichtig,
    zwischen HG_VERLAUF_START und HG_VERLAUF_VOLL weich ansteigend, darunter
    konstant HG_VERLAUF_DECKUNG - so steht jede Textzeile auf gleichmaessig
    dunklem Grund, waehrend der obere Bildteil unangetastet bleibt."""
    maske = Image.new("L", (BREITE, HOEHE), 0)
    zeichnen = ImageDraw.Draw(maske)
    voll = int(255 * HG_VERLAUF_DECKUNG)
    spanne = HG_VERLAUF_VOLL - HG_VERLAUF_START
    for y in range(HG_VERLAUF_START, HOEHE):
        t = min(1.0, (y - HG_VERLAUF_START) / spanne)
        zeichnen.line([(0, y), (BREITE, y)], fill=int(voll * t ** 1.5))
    return maske


def videohintergrund(quelle: Path | None, ziel: Path) -> Path:
    """Bild als 1280x720-Videohintergrund aufbereiten: cover-Zuschnitt in
    voller Qualitaet, dazu der dunkle Verlauf am unteren Rand fuer die
    Textzeilen. Ohne Quelle oder bei unlesbarer Datei entsteht die
    einfarbige Grundflaeche - der Anrufer muss sich um kaputte Bilder
    nicht kuemmern."""
    bild: Image.Image
    try:
        if quelle is None:
            raise OSError("keine Quelle")
        bild = Image.open(quelle).convert("RGB")
    except OSError:
        Image.new("RGB", (BREITE, HOEHE), GRUND).save(ziel, "JPEG", quality=90)
        return ziel
    skala = max(BREITE / bild.width, HOEHE / bild.height)
    neu = (max(BREITE, int(bild.width * skala + 0.5)),
           max(HOEHE, int(bild.height * skala + 0.5)))
    bild = bild.resize(neu, Image.Resampling.LANCZOS)
    links = (bild.width - BREITE) // 2
    # oberes Drittel statt Mitte, wie beim Thumbnail-Motiv
    oben = min((bild.height - HOEHE) // 3, bild.height - HOEHE)
    bild = bild.crop((links, oben, links + BREITE, oben + HOEHE))
    schwarz = Image.new("RGB", (BREITE, HOEHE), (0, 0, 0))
    bild = Image.composite(schwarz, bild, _bodenverlauf())
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel, "JPEG", quality=90)
    return ziel


def bauen(text: str, motiv: Path | None, ziel: Path, kopf: str = "4CHAN /biz/",
          fuss: str = "") -> Path:
    """Vorschaubild zusammensetzen und als JPEG unter 2 MB ablegen."""
    bild = Image.new("RGB", (BREITE, HOEHE), GRUND)
    text_breite = BREITE - 2 * MARGIN - BALKEN_BREITE - BALKEN_ABSTAND
    if motiv is not None:
        bild.paste(_motiv_flaeche(motiv), (BREITE - MOTIV_BREITE, 0), _blende())
        text_breite -= MOTIV_BREITE - MOTIV_BLENDE // 2

    zeichnen = ImageDraw.Draw(bild)
    text_x = MARGIN + BALKEN_BREITE + BALKEN_ABSTAND
    font, zeilen = _passende_schrift(text.upper(), text_breite,
                                     TEXT_UNTEN - TEXT_OBEN, zeichnen)
    schritt = int(font.size * ZEILEN_FAKTOR)
    block_hoehe = schritt * len(zeilen)
    y = TEXT_OBEN + max(0, (TEXT_UNTEN - TEXT_OBEN - block_hoehe) // 2)

    zeichnen.rectangle([MARGIN, y + 6, MARGIN + BALKEN_BREITE,
                        y + block_hoehe - 6], fill=AKZENT)
    for i, zeile in enumerate(zeilen):
        # Kontur statt Schatten: haelt den Text auch dort lesbar, wo die
        # weiche Kante des Motivs in den Textbereich hineinreicht.
        zeichnen.text((text_x, y + i * schritt), zeile, font=font,
                      fill=TEXT_HELL, stroke_width=4, stroke_fill=GRUND)

    klein = schrift(True, 34)
    zeichnen.text((text_x, KOPF_Y), kopf, font=klein, fill=AKZENT,
                  stroke_width=3, stroke_fill=GRUND)
    if fuss:
        mager = schrift(False, 30)
        zeichnen.text((text_x, FUSS_Y), fuss, font=mager, fill=TEXT_GRAU,
                      stroke_width=3, stroke_fill=GRUND)

    ziel.parent.mkdir(parents=True, exist_ok=True)
    for qualitaet in (JPEG_QUALITAET, 75, 60):
        bild.save(ziel, "JPEG", quality=qualitaet, optimize=True)
        if ziel.stat().st_size <= MAX_BYTES:
            return ziel
    raise RuntimeError(f"Vorschaubild bleibt ueber {MAX_BYTES} Bytes: "
                       f"{ziel.stat().st_size}")


if __name__ == "__main__":  # Handprobe: thumbnail.py TEXT [MOTIV]
    import sys
    ziel = Path("thumbnail_probe.jpg")
    bauen(sys.argv[1] if len(sys.argv) > 1 else "CHAIN SPLIT",
          Path(sys.argv[2]) if len(sys.argv) > 2 else None, ziel,
          fuss="Lagebericht 15.08.2026")
    print(ziel.resolve())
