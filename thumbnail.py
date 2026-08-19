#!/usr/bin/env python3
"""Baut das YouTube-Vorschaubild des Tages.

Fester Serienrahmen (Designsystem 19.08.2026): dunkle Textflaeche links,
rechts das Bildmotiv in voller Farbe, dazwischen ein harter
Diagonalanschnitt mit Amber-Kante. Oben links der Amber-Chip mit der
Serienmarke, darunter der Tages-Aufhaenger in grosser Schrift mit
Amber-Balken - das letzte Wort amber als Akzent. Das Motiv ist entweder
das vom Report-Lauf gepruefte Board-Bild des Tages oder das statische
Serienbild aus assets/ - der Rahmen bleibt in beiden Faellen derselbe,
damit die Reihe wiedererkennbar bleibt (und bei Briefmarkengroesse in
der Sidebar noch als diese Reihe lesbar ist).

Bewusst ohne Netzzugriff und ohne Kenntnis der uebrigen Pipeline: das Modul
bekommt Text und Motiv gereicht und gibt eine JPEG-Datei zurueck.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import design_tokens

BREITE = 1280
HOEHE = 720
GRUND = design_tokens.NEUTRAL[9]      # derselbe Ton wie der Videohintergrund
AKZENT = design_tokens.AKZENT[6]      # amber, wie die Wort-Hervorhebung im Video
TEXT_HELL = design_tokens.WEISS
TEXT_GRAU = design_tokens.NEUTRAL[3]

# Diagonalanschnitt: die Schnittkante laeuft von x=62% (oben) nach x=50%
# (unten), links davon liegt die opake Textflaeche, entlang der Kante ein
# schmaler Amber-Streifen. Das Motiv rechts bleibt in voller Farbe - der
# Kontrast Textflaeche/Motiv ist der Klick-Appeal bei Briefmarkengroesse.
DIAG_OBEN = 0.62
DIAG_UNTEN = 0.50
DIAG_STREIFEN = 0.013

MARGIN = 64
BALKEN_BREITE = 14            # Akzentbalken links neben dem Aufhaenger
BALKEN_ABSTAND = 26
CHIP_Y = 48                   # Amber-Chip mit der Serienmarke oben links
FUSS_Y = HOEHE - 84
TEXT_OBEN = 170
TEXT_UNTEN = FUSS_Y - 16
TEXT_BREITE = 540             # Umbruchbreite links der Diagonale
ZEILEN_MAX = 3
GROESSEN = list(range(108, 43, -4))
ZEILEN_FAKTOR = 1.08

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


def _motiv_vollbild(motiv: Path) -> Image.Image:
    """Motiv als Vollbild zuschneiden (cover), in voller Farbe - die
    Diagonale und die dunkle Textflaeche kommen daruf zu liegen."""
    bild: Image.Image = Image.open(motiv).convert("RGB")
    skala = max(BREITE / bild.width, HOEHE / bild.height)
    neu = (max(BREITE, int(bild.width * skala + 0.5)),
           max(HOEHE, int(bild.height * skala + 0.5)))
    bild = bild.resize(neu, Image.Resampling.LANCZOS)
    links = (bild.width - BREITE) // 2
    # Vertikal nicht mittig, sondern im oberen Drittel schneiden: bei
    # Board-Bildern steckt das Motiv haeufiger oben als in der Mitte.
    oben = min((bild.height - HOEHE) // 3, bild.height - HOEHE)
    return bild.crop((links, oben, links + BREITE, oben + HOEHE))


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
    if motiv is not None:
        try:
            bild = _motiv_vollbild(motiv)
        except OSError:
            pass  # kaputtes Bild: Farbflaeche statt Abbruch

    zeichnen = ImageDraw.Draw(bild)
    # Diagonalanschnitt: opake Textflaeche links, Amber-Kante entlang des
    # Schnitts. Beides steht auch ohne Motiv - der Streifen ist Serienmarke.
    xo, xu = int(BREITE * DIAG_OBEN), int(BREITE * DIAG_UNTEN)
    sb = int(BREITE * DIAG_STREIFEN)
    zeichnen.polygon([(0, 0), (xo, 0), (xu, HOEHE), (0, HOEHE)], fill=GRUND)
    zeichnen.polygon([(xo, 0), (xo + sb, 0), (xu + sb, HOEHE), (xu, HOEHE)],
                     fill=AKZENT)

    text_x = MARGIN + BALKEN_BREITE + BALKEN_ABSTAND
    font, zeilen = _passende_schrift(text.upper(), TEXT_BREITE,
                                     TEXT_UNTEN - TEXT_OBEN, zeichnen)
    schritt = int(font.size * ZEILEN_FAKTOR)
    block_hoehe = schritt * len(zeilen)
    y = TEXT_OBEN + max(0, (TEXT_UNTEN - TEXT_OBEN - block_hoehe) // 2)

    zeichnen.rectangle([MARGIN, y + 10, MARGIN + BALKEN_BREITE,
                        y + block_hoehe - 10], fill=AKZENT)
    for i, zeile in enumerate(zeilen):
        # Kontur statt Schatten haelt den Text auch dort lesbar, wo die
        # Amber-Kante oder das Motiv in den Textblock hineinreicht. Das
        # letzte Wort des Aufhaengers steht amber - der eine Akzent, der
        # das Vorschaubild von einer reinen Texttafel unterscheidet.
        zy = y + i * schritt
        if i == len(zeilen) - 1:
            teile = zeile.rsplit(" ", 1)
            if len(teile) == 2:
                vorn, akzent = teile[0] + " ", teile[1]
            else:
                vorn, akzent = "", teile[0]
            zeichnen.text((text_x, zy), vorn, font=font, fill=TEXT_HELL,
                          stroke_width=4, stroke_fill=GRUND)
            zeichnen.text((text_x + zeichnen.textlength(vorn, font=font), zy),
                          akzent, font=font, fill=AKZENT,
                          stroke_width=4, stroke_fill=GRUND)
        else:
            zeichnen.text((text_x, zy), zeile, font=font, fill=TEXT_HELL,
                          stroke_width=4, stroke_fill=GRUND)

    # Amber-Chip mit der Serienmarke: dunkler Text auf Amber statt Amber
    # auf dunkel - bei Briefmarkengroesse der auffaelligste Baustein.
    chip_font = schrift(True, 32)
    chip_breite = zeichnen.textlength(kopf, font=chip_font)
    zeichnen.rectangle([MARGIN, CHIP_Y, MARGIN + 20 + int(chip_breite) + 20,
                        CHIP_Y + 56], fill=AKZENT)
    zeichnen.text((MARGIN + 20, CHIP_Y + 8), kopf, font=chip_font, fill=GRUND)
    if fuss:
        mager = schrift(False, 28)
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
