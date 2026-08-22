#!/usr/bin/env python3
"""Baut das YouTube-Vorschaubild des Tages.

Meme-Rahmen (22.08.2026): das Motiv laeuft als Vollbild durch, der
Aufhaenger steht als Meme-Text direkt darueber - weiss mit dicker
schwarzer Kontur, wie die Bildmakros vom Board. In welchem Band und mit
welcher Ausrichtung, sagt der Aufrufer (das Modell sieht sich das Motiv
an, siehe video_report._thumb_platzierung); ohne Angabe misst
platzierung_messen() die ruhigste Flaeche selbst. Die frueheren Bausteine (dunkle Textflaeche ueber der halben
Breite, Diagonalanschnitt, Amber-Balken) sind ersatzlos weg: sie haben
das Motiv halb verdeckt, genau das war die Klage am Bild vom 21.08.
Serienmarke bleibt der kleine Amber-Chip, jetzt unten links, wo er das
Motiv nicht zerschneidet. Das Motiv ist entweder das vom Report-Lauf
gepruefte Board-Bild des Tages oder das statische Serienbild aus
assets/.

Bewusst ohne Netzzugriff und ohne Kenntnis der uebrigen Pipeline: das Modul
bekommt Text und Motiv gereicht und gibt eine JPEG-Datei zurueck.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

import design_tokens

BREITE = 1280
HOEHE = 720
GRUND = design_tokens.NEUTRAL[9]      # derselbe Ton wie der Videohintergrund
AKZENT = design_tokens.AKZENT[6]      # amber, wie die Wort-Hervorhebung im Video
TEXT_HELL = design_tokens.WEISS
TEXT_GRAU = design_tokens.NEUTRAL[3]

# Meme-Text: keine Flaeche, kein Kasten, kein Verlauf - der Aufhaenger
# steht frei ueber dem Motiv und wird allein durch die schwarze Kontur
# lesbar (KONTUR_FAKTOR mal Schriftgroesse, wie bei den Impact-Bildmakros).
# Weil keine Textflaeche mehr Platz frisst, laeuft der Umbruch ueber die
# volle Bildbreite und die Schrift darf entsprechend groesser werden.
MARGIN = 48
TEXT_OBEN = 34                # Oberkante des Meme-Blocks
TEXT_BREITE = BREITE - 2 * MARGIN
TEXT_HOEHE = 420              # Meme-Block bleibt in der oberen Bildhaelfte
ZEILEN_MAX = 3
GROESSEN = list(range(132, 55, -6))
ZEILEN_FAKTOR = 1.02
KONTUR_FAKTOR = 0.085         # Konturbreite relativ zur Schriftgroesse

CHIP_HOEHE = 46               # Amber-Chip mit der Serienmarke, unten links
CHIP_Y = HOEHE - MARGIN - CHIP_HOEHE
FUSS_Y = CHIP_Y + 8

# Wohin der Meme-Text darf: drei Baender (oben/mitte/unten) und drei
# Ausrichtungen. Welche Kombination ein Bild vertraegt, haengt am Motiv -
# ueber einem Gesicht in der Bildmitte gehoert der Text nach oben, ueber
# einem Chart-Screenshot mit Kopfzeile nach unten. Entschieden wird das vom
# Modell (video_report._thumb_platzierung), das Motiv wirklich ansieht; ohne
# Urteil greift platzierung_messen() als deterministischer Ersatz.
ZONEN = ("oben", "mitte", "unten")
AUSRICHTUNGEN = ("links", "mitte", "rechts")
ZONE_STANDARD = "oben"
AUSRICHTUNG_STANDARD = "mitte"
# Wie breit der Textblock werden darf, als Anteil der Satzbreite. "voll" ist
# die Bildmakro-Zeile ueber das ganze Bild; die engeren Stufen sind der
# Grund, warum das Modell den Umbruch mitentscheiden koennen muss - erst
# eine schmale Spalte laesst den Text NEBEN dem Motiv stehen statt darauf
# (Nutzerbefund 22.08.2026: "rechts 50% / TARIFFS im dunklen Bereich").
BLOCK_BREITEN = {"voll": 1.0, "halb": 0.52, "drittel": 0.38}
BREITE_STANDARD = "voll"
# Unterkante des Textblocks bei Zone "unten": ueber Chip und Fusstext.
TEXT_UNTEN_GRENZE = CHIP_Y - 24
# Messraster fuer platzierung_messen(): so klein, dass die Messung nichts
# kostet, so gross, dass Kanten noch zaehlen.
MESS_BREITE = 160
MESS_HOEHE = 90
MESS_SPALTEN_VORSPRUNG = 0.75  # so viel ruhiger muss eine Spalte sein,
# damit die Ausrichtung von der Mitte abweicht - sonst bleibt der Meme-Text
# zentriert, wie es die Bildmakro-Konvention will.

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
    """Motiv als Vollbild zuschneiden (cover), in voller Farbe - darauf
    kommt nur noch der Meme-Text, keine Flaeche."""
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


def platzierung_messen(motiv: Path | None) -> tuple[str, str]:
    """Deterministischer Ersatz fuer das Modellurteil: Zone und Ausrichtung
    aus der Kantenaktivitaet des Motivs. Gewaehlt wird das ruhigste der drei
    Baender - dort verdeckt der Text am wenigsten und die Kontur muss am
    wenigsten leisten. Ohne (oder mit kaputtem) Motiv bleibt es beim
    Standard.

    Der Vergleich der drei Spalten entscheidet nur, wenn eine deutlich
    ruhiger ist als der Schnitt (MESS_SPALTEN_VORSPRUNG); sonst bleibt der
    Text zentriert."""
    if motiv is None:
        return ZONE_STANDARD, AUSRICHTUNG_STANDARD
    try:
        # Gemessen wird der fertige Zuschnitt, nicht die Quelldatei: der
        # cover-Schnitt verschiebt die Baender, sonst zeigt die Messung auf
        # eine Zone, die im Vorschaubild gar nicht zu sehen ist.
        klein = _motiv_vollbild(motiv).convert("L").resize(
            (MESS_BREITE, MESS_HOEHE), Image.Resampling.LANCZOS)
    except OSError:
        return ZONE_STANDARD, AUSRICHTUNG_STANDARD
    kanten = klein.filter(ImageFilter.FIND_EDGES)
    drittel_h = MESS_HOEHE // 3
    baender = [
        ImageStat.Stat(kanten.crop((0, i * drittel_h, MESS_BREITE,
                                    (i + 1) * drittel_h))).mean[0]
        for i in range(3)]
    zone = ZONEN[baender.index(min(baender))]
    y0 = ZONEN.index(zone) * drittel_h
    drittel_b = MESS_BREITE // 3
    spalten = [
        ImageStat.Stat(kanten.crop((i * drittel_b, y0, (i + 1) * drittel_b,
                                    y0 + drittel_h))).mean[0]
        for i in range(3)]
    schnitt = sum(spalten) / 3
    beste = min(spalten)
    ausrichtung = (AUSRICHTUNGEN[spalten.index(beste)]
                   if schnitt and beste < MESS_SPALTEN_VORSPRUNG * schnitt
                   else AUSRICHTUNG_STANDARD)
    return zone, ausrichtung


def _block_oben(zone: str, block_hoehe: int) -> int:
    """Oberkante des Textblocks in der gewaehlten Zone - bei 'unten' so
    hoch, dass Chip und Fusstext frei bleiben."""
    if zone == "unten":
        return max(TEXT_OBEN, TEXT_UNTEN_GRENZE - block_hoehe)
    if zone == "mitte":
        return max(TEXT_OBEN, (HOEHE - block_hoehe) // 2)
    return TEXT_OBEN


def _zeile_links(ausrichtung: str, zeilen_breite: float) -> float:
    """x der Zeile nach Ausrichtung - immer innerhalb der Raender."""
    if ausrichtung == "links":
        return MARGIN
    if ausrichtung == "rechts":
        return max(MARGIN, BREITE - MARGIN - zeilen_breite)
    return max(MARGIN, (BREITE - zeilen_breite) / 2)


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
                      zeichnen: ImageDraw.ImageDraw,
                      umbruch: list[str] | None = None
                      ) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Groesste Schrift, in der der Aufhaenger in den Textblock passt.

    Mit `umbruch` steht die Zeilenteilung schon fest (vom Modell gewaehlt,
    siehe umbruch_pruefen) - dann wird nur noch die Schriftgroesse gesucht,
    bei der die laengste dieser Zeilen in die Blockbreite passt."""
    if umbruch:
        for groesse in GROESSEN:
            font = schrift(True, groesse)
            zu_breit = any(zeichnen.textlength(z, font=font) > breite
                           for z in umbruch)
            if not zu_breit and len(umbruch) * groesse * ZEILEN_FAKTOR <= hoehe:
                return font, umbruch
        # Passt die Vorgabe selbst in der kleinsten Schrift nicht in die
        # Spalte, ist sie unbrauchbar - dann bricht wieder der Code um.
        return _passende_schrift(text, breite, hoehe, zeichnen)
    for groesse in GROESSEN:
        font = schrift(True, groesse)
        zeilen = _umbrechen(text, font, breite, zeichnen)
        if zeilen and len(zeilen) * groesse * ZEILEN_FAKTOR <= hoehe:
            return font, zeilen
    # Reissleine: kleinste Groesse, hart auf ZEILEN_MAX Zeilen gekappt.
    font = schrift(True, GROESSEN[-1])
    zeilen = _umbrechen(text, font, breite, zeichnen) or [text[:18]]
    return font, zeilen[:ZEILEN_MAX]


def umbruch_pruefen(text: str, umbruch: object) -> list[str] | None:
    """Nimmt die Zeilenteilung des Modells nur an, wenn sie denselben Text
    traegt: gleiche Woerter in gleicher Reihenfolge, hoechstens ZEILEN_MAX
    Zeilen, keine leere Zeile. Sonst None - der Code bricht dann selbst um.

    Der Riegel ist der Punkt: ein Modell, das den Umbruch waehlen darf,
    koennte sonst die Schlagzeile umschreiben, kuerzen oder etwas
    dazuerfinden, und das stuende dann als Kanalanstrich im Netz."""
    if not isinstance(umbruch, list) or not 0 < len(umbruch) <= ZEILEN_MAX:
        return None
    zeilen = [str(z).strip().upper() for z in umbruch]
    if not all(zeilen):
        return None
    if " ".join(zeilen).split() != text.strip().upper().split():
        return None
    return zeilen


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


def bauen(text: str, motiv: Path | None, ziel: Path, kopf: str = "BIZ-NEWS",
          fuss: str = "", zone: str = "", ausrichtung: str = "",
          block_breite: str = "", umbruch: list[str] | None = None) -> Path:
    """Vorschaubild zusammensetzen und als JPEG unter 2 MB ablegen.

    zone/ausrichtung sagen, wo der Meme-Text steht (siehe ZONEN und
    AUSRICHTUNGEN), block_breite wie breit er dabei werden darf (siehe
    BLOCK_BREITEN) und umbruch, an welchen Stellen die Zeilen brechen. Leer
    oder unbekannt heisst: selbst entscheiden - Zone und Ausrichtung ueber
    platzierung_messen(), Breite ueber BREITE_STANDARD, Umbruch im Code. So
    bleibt das Modul auch ohne den Modellaufruf des Video-Laufs brauchbar."""
    if zone not in ZONEN or ausrichtung not in AUSRICHTUNGEN:
        gemessen_zone, gemessen_aus = platzierung_messen(motiv)
        zone = zone if zone in ZONEN else gemessen_zone
        ausrichtung = (ausrichtung if ausrichtung in AUSRICHTUNGEN
                       else gemessen_aus)
    if block_breite not in BLOCK_BREITEN:
        block_breite = BREITE_STANDARD
    satzbreite = int(TEXT_BREITE * BLOCK_BREITEN[block_breite])
    umbruch = umbruch_pruefen(text, umbruch)
    bild = Image.new("RGB", (BREITE, HOEHE), GRUND)
    if motiv is not None:
        try:
            bild = _motiv_vollbild(motiv)
        except OSError:
            pass  # kaputtes Bild: Farbflaeche statt Abbruch

    zeichnen = ImageDraw.Draw(bild)
    font, zeilen = _passende_schrift(text.upper(), satzbreite, TEXT_HOEHE,
                                     zeichnen, umbruch)
    schritt = int(font.size * ZEILEN_FAKTOR)
    kontur = max(3, int(font.size * KONTUR_FAKTOR))
    y = _block_oben(zone, schritt * len(zeilen))

    for i, zeile in enumerate(zeilen):
        # Meme-Satz: weiss mit dicker schwarzer Kontur, zentriert - keine
        # Flaeche darunter. Das letzte Wort steht amber und bleibt die
        # Serienfarbe, die das Bild vom beliebigen Bildmakro unterscheidet.
        zy = y + i * schritt
        if i == len(zeilen) - 1 and len(zeilen) > 0:
            teile = zeile.rsplit(" ", 1)
            vorn, akzent = (teile[0] + " ", teile[1]) if len(teile) == 2 \
                else ("", teile[0])
        else:
            vorn, akzent = zeile, ""
        breite_vorn = zeichnen.textlength(vorn, font=font)
        breite_ganz = breite_vorn + zeichnen.textlength(akzent, font=font)
        x = _zeile_links(ausrichtung, breite_ganz)
        if vorn:
            zeichnen.text((x, zy), vorn, font=font, fill=TEXT_HELL,
                          stroke_width=kontur, stroke_fill=(0, 0, 0))
        if akzent:
            zeichnen.text((x + breite_vorn, zy), akzent, font=font,
                          fill=AKZENT, stroke_width=kontur,
                          stroke_fill=(0, 0, 0))

    # Amber-Chip mit der Serienmarke: dunkler Text auf Amber, unten links -
    # klein genug, um das Motiv nicht anzuschneiden, kraeftig genug, um bei
    # Briefmarkengroesse die Reihe zu markieren.
    chip_font = schrift(True, 28)
    chip_breite = int(zeichnen.textlength(kopf, font=chip_font))
    chip_rechts = MARGIN + 16 + chip_breite + 16
    zeichnen.rectangle([MARGIN, CHIP_Y, chip_rechts, CHIP_Y + CHIP_HOEHE],
                       fill=AKZENT)
    zeichnen.text((MARGIN + 16, CHIP_Y + 7), kopf, font=chip_font, fill=GRUND)
    if fuss:
        mager = schrift(False, 26)
        zeichnen.text((chip_rechts + 18, FUSS_Y), fuss, font=mager,
                      fill=TEXT_HELL, stroke_width=4, stroke_fill=(0, 0, 0))

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
