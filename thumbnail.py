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

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

BREITE = 1280
HOEHE = 720
GRUND = (26, 26, 46)          # derselbe Ton wie der Videohintergrund
AKZENT = (255, 209, 102)      # amber, wie die Wort-Hervorhebung im Video
TEXT_HELL = (255, 255, 255)
TEXT_GRAU = (170, 175, 190)

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

# Videohintergrund: das Bild soll Kulisse hinter dem Untertiteltext sein,
# nicht Konkurrenz - deshalb deutlich staerker abgedunkelt und entsaettigt
# als das Thumbnail-Motiv, dazu leicht unscharf (verdeckt auch die
# Kompressionsartefakte kleiner Board-Bilder auf voller Bildflaeche).
HG_FARBE = 0.50
HG_HELLIGKEIT = 0.42
HG_UNSCHAERFE = 3

# Dieselben Kandidaten wie im Video-Renderer; hier erneut aufgefuehrt, damit
# das Modul ohne video_report.py nutzbar bleibt (Importrichtung: video -> thumb).
FONT_FETT_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
FONT_NORMAL_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _font_pfad(kandidaten: list[str]) -> str:
    for f in kandidaten:
        if Path(f).exists():
            return f
    raise RuntimeError(f"keiner der Font-Kandidaten gefunden: {kandidaten}")


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
    pfad = _font_pfad(FONT_FETT_KANDIDATEN)
    for groesse in GROESSEN:
        font = ImageFont.truetype(pfad, groesse)
        zeilen = _umbrechen(text, font, breite, zeichnen)
        if zeilen and len(zeilen) * groesse * ZEILEN_FAKTOR <= hoehe:
            return font, zeilen
    # Reissleine: kleinste Groesse, hart auf ZEILEN_MAX Zeilen gekappt.
    font = ImageFont.truetype(pfad, GROESSEN[-1])
    zeilen = _umbrechen(text, font, breite, zeichnen) or [text[:18]]
    return font, zeilen[:ZEILEN_MAX]


def videohintergrund(quelle: Path | None, ziel: Path) -> Path:
    """Bild als 1280x720-Videohintergrund aufbereiten (cover-Zuschnitt,
    entsaettigt, stark abgedunkelt, leicht unscharf). Ohne Quelle oder bei
    unlesbarer Datei entsteht die einfarbige Grundflaeche - der Anrufer muss
    sich um kaputte Bilder nicht kuemmern."""
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
    bild = ImageEnhance.Color(bild).enhance(HG_FARBE)
    bild = ImageEnhance.Brightness(bild).enhance(HG_HELLIGKEIT)
    bild = bild.filter(ImageFilter.GaussianBlur(HG_UNSCHAERFE))
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

    klein = ImageFont.truetype(_font_pfad(FONT_FETT_KANDIDATEN), 34)
    zeichnen.text((text_x, KOPF_Y), kopf, font=klein, fill=AKZENT,
                  stroke_width=3, stroke_fill=GRUND)
    if fuss:
        mager = ImageFont.truetype(_font_pfad(FONT_NORMAL_KANDIDATEN), 30)
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
