#!/usr/bin/env python3
"""Praesentations-Folien fuer das /biz/-Video (v7-Look, 19.08.2026).

Rendert die Standbilder der Praesentation als 1280x720-Bilder im
Design-Vokabular von thumbnail.py (dunkler Grund, Amber-Akzent, Balken,
Ecken-Bug): Intro mit dem Tages-Aufhaenger, Agenda, je Berichtsabschnitt
eine Themen-Folie mit Stichpunkten und optionaler Zahlen-Karte, eine
"Numbers of the day"-Folie und ein Outro. Dazu die Reveal-Bilder (rohes
Board-Bild mit Titel-Kasten) und die Blend-Zwischenbilder fuer den
Folienuebergang.

Seit dem Designsystem vom 19.08.2026 folgen die Folien dem Broadcast-Look
der Szenen (szenen.py) statt einem eigenen Folien-Raster: das Board-Motiv
liegt vollflaechig und unverdunkelt, aller Text steht auf hochdeckenden
schwarzen Kaesten (Alpha 228 wie szenen.KARTE_ALPHA), Seitenpanels sitzen
buendig an der Bildkante mit nur bildinnern gerundeten Ecken. Nur die
Zahlen- und die Outro-Folie dunkeln das Motiv stark ab - dort ist die
Flaeche selbst die Buehne.

video_report.py schaltet die fertigen Bilder per ffconcat zeitgesteuert um;
Text wird auf diesem Pfad nicht mehr per ASS eingebrannt. Das Modul kennt
wie thumbnail.py weder Netz noch Pipeline: es bekommt Texte und Bildpfade
gereicht und liefert PIL-Bilder zurueck.

Die festen Beschriftungen sind englisch - die Praesentation laeuft vorerst
nur fuer das englische Video (Entscheid 16.08.2026, deutsche Fassung auf
der Ersatzbank).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

import design_tokens
import icons
import thumbnail

B = thumbnail.BREITE
H = thumbnail.HOEHE
GRUND = thumbnail.GRUND
AKZENT = thumbnail.AKZENT
HELL = thumbnail.TEXT_HELL
GRAU = thumbnail.TEXT_GRAU
GEDIMMT = design_tokens.NEUTRAL[5]    # Fusszeilen / inaktive Nummern
NEBEN = design_tokens.NEUTRAL[4]      # Nebentext auf Kaesten
PUNKT_ALT = design_tokens.NEUTRAL[2]  # inaktive Stichpunkte
KARTE_BG = design_tokens.NEUTRAL[8]   # opake Zahlen-Karten (Zahlen-Folie)
LINIE = design_tokens.NEUTRAL[7]
MARGIN = 64

# Deckkraft der Text-Kaesten auf rohem Board-Motiv - derselbe Wert wie
# szenen.KARTE_ALPHA (dort steht auch das Warum: die Feinstruktur der
# Motive frisst Kontrast, der Kasten traegt die Lesbarkeit allein).
KASTEN = (0, 0, 0, 228)
ECKRADIUS = 16

# Serientitel "BIZ-NEWS" (C5, 22.08.2026) - Begruendung in szenen.BUG_TEXT.
KOPF_TEXT = "BIZ-NEWS"
INTRO_LABEL = "TODAY'S TOP STORY"
AGENDA_TITEL = "IN TODAY'S REPORT"
ZAHLEN_TITEL = "NUMBERS OF THE DAY"
OUTRO_TITEL = "BIZ-NEWS"
OUTRO_ZEILE1 = "New every day"
OUTRO_ZEILE2 = "Source threads and chapters in the description"

VOLLBILD_DECKUNG = 0.82       # Abdunkelung der Zahlen-Folie
OUTRO_DECKUNG = 0.86
PUNKTE_UNTEN_MAX = 650        # Stichpunkt-Kasten endet ueber dem Quellen-Chip
JPEG_QUALITAET = 90


@lru_cache(maxsize=32)
def _font(fett: bool, groesse: int) -> ImageFont.FreeTypeFont:
    return thumbnail.schrift(fett, groesse)


@lru_cache(maxsize=16)
def _font_mono(groesse: int) -> ImageFont.FreeTypeFont:
    """Tabellenziffern-Schrift fuer Zahlenwerte (Zahlen-Tafel, Countup) -
    feste Ziffernbreite haelt das Hochzaehlen ruhig statt zu jittern."""
    return thumbnail.schrift_mono(groesse)


@lru_cache(maxsize=16)
def _font_medium(groesse: int) -> ImageFont.FreeTypeFont:
    return thumbnail.schrift_medium(groesse)


def _umbrechen(d: ImageDraw.ImageDraw, text: str,
               font: ImageFont.FreeTypeFont, breite: int) -> list[str]:
    zeilen: list[str] = []
    aktuell = ""
    for wort in text.split():
        kandidat = f"{aktuell} {wort}".strip()
        if aktuell and d.textlength(kandidat, font=font) > breite:
            zeilen.append(aktuell)
            aktuell = wort
        else:
            aktuell = kandidat
    if aktuell:
        zeilen.append(aktuell)
    return zeilen


def _vollbild(motiv: Path | None, deckung: float = 0.0,
              entsaettigen: float = 1.0) -> Image.Image:
    """Vollflaechiger Bildhintergrund. deckung=0 laesst das Motiv roh (die
    Kaesten tragen die Lesbarkeit); die Zahlen-/Outro-Folie blendet es
    stark gegen GRUND ab, dort ist die Flaeche selbst die Buehne."""
    if motiv is None:
        return Image.new("RGB", (B, H), GRUND)
    try:
        bild = Image.open(motiv).convert("RGB")
    except OSError:
        return Image.new("RGB", (B, H), GRUND)
    skala = max(B / bild.width, H / bild.height)
    neu = (max(B, int(bild.width * skala + 0.5)),
           max(H, int(bild.height * skala + 0.5)))
    bild = bild.resize(neu, Image.Resampling.LANCZOS)
    links = (bild.width - B) // 2
    oben = min((bild.height - H) // 3, bild.height - H)
    bild = bild.crop((links, oben, links + B, oben + H))
    if entsaettigen < 1.0:
        bild = ImageEnhance.Color(bild).enhance(entsaettigen)
    if deckung > 0:
        bild = Image.blend(bild, Image.new("RGB", (B, H), GRUND), deckung)
    return bild


def _verlauf_oben(bild: Image.Image) -> None:
    """Hauch Abdunkelung hinter dem Ecken-Bug, wie szenen.vignette()."""
    d = ImageDraw.Draw(bild, "RGBA")
    for y in range(96):
        d.line([(0, y), (B, y)], fill=(0, 0, 0, int(110 * (1 - y / 96))))


def _kopfzeile(d: ImageDraw.ImageDraw, datum: str) -> None:
    """Ecken-Bug wie in den Szenen: Serienmarke links, Datum rechts."""
    d.text((40, 30), KOPF_TEXT, font=_font(True, 24), fill=AKZENT,
           stroke_width=2, stroke_fill=(0, 0, 0))
    breite = d.textlength(datum, font=_font(False, 24))
    d.text((B - 40 - breite, 30), datum, font=_font(False, 24), fill=GRAU,
           stroke_width=2, stroke_fill=(0, 0, 0))


def _zahlen_karte(d: ImageDraw.ImageDraw, karte: dict, x: int, y: int,
                  breite: int, hoehe: int, rahmen: int = 0,
                  bg: str | tuple[int, ...] | None = None,
                  wert_groessen: tuple[int, ...] = (72, 64, 56)) -> None:
    """Kennzahl-Karte: Amber-Balken links, Mono-Wert, Titel, Quellenzeile.
    `rahmen` ist die Rahmenbreite in px (0 = kein Rahmen), `bg` die
    Kartenflaeche (Default: der hochdeckende schwarze Kasten)."""
    d.rounded_rectangle([x, y, x + breite, y + hoehe], radius=14,
                        fill=bg if bg is not None else KASTEN,
                        outline=AKZENT if rahmen else None, width=rahmen)
    d.rectangle([x, y + 22, x + 8, y + hoehe - 22], fill=AKZENT)
    wert = str(karte.get("wert", ""))[:14]
    for gr in wert_groessen:
        if d.textlength(wert, font=_font_mono(gr)) <= breite - 34 - 30:
            break
    d.text((x + 34, y + 24), wert, font=_font_mono(gr), fill=AKZENT)
    d.text((x + 34, y + hoehe - 90), str(karte.get("titel", ""))[:40],
           font=_font(False, 26), fill=HELL)
    d.text((x + 34, y + hoehe - 54), str(karte.get("sub", ""))[:44],
           font=_font(False, 22), fill=GRAU)


# ------------------------------------------------------------------ Folien

def intro(hook: str, datum: str, motiv: Path | None) -> Image.Image:
    """Today's Top Story als Broadcast-Karte ueber dem rohen Vollbild-Motiv:
    Amber-Balken, Label, grosser Aufhaenger, Abbinder-Zeile - alles in
    einem Kasten statt frei auf der abgedunkelten Flaeche."""
    bild = _vollbild(motiv)
    _verlauf_oben(bild)
    d = ImageDraw.Draw(bild, "RGBA")
    _kopfzeile(d, datum)
    kb = 860
    breite = kb - 48 - 44
    for gr in (64, 56, 48):
        font = _font(True, gr)
        zeilen = _umbrechen(d, hook.upper(), font, breite)
        if len(zeilen) <= 3:
            break
    schritt = int(gr * 1.16)
    ky = 218
    kh = 34 + 32 + 16 + schritt * len(zeilen) + 24 + 30 + 36
    d.rounded_rectangle([MARGIN, ky, MARGIN + kb, ky + kh],
                        radius=ECKRADIUS, fill=KASTEN)
    d.rectangle([MARGIN, ky + 28, MARGIN + 10, ky + kh - 28], fill=AKZENT)
    d.text((MARGIN + 48, ky + 34), INTRO_LABEL, font=_font(True, 26),
           fill=AKZENT)
    ty = ky + 34 + 32 + 16
    for i, z in enumerate(zeilen):
        d.text((MARGIN + 48, ty + i * schritt), z, font=font, fill=HELL)
    d.text((MARGIN + 48, ty + schritt * len(zeilen) + 24),
           f"Daily report from the 4chan business board  ·  {datum}",
           font=_font(False, 24), fill=NEBEN)
    return bild


def agenda(eintraege: list[str], aktiv: int, datum: str,
           motiv: Path | None) -> Image.Image:
    """Kapitel-Uebersicht als Seitenpanel buendig an der linken Bildkante;
    der gerade gesprochene Eintrag (aktiv, -1 = keiner) steht hell mit
    Amber-Nummer, die uebrigen gedimmt."""
    bild = _vollbild(motiv)
    _verlauf_oben(bild)
    d = ImageDraw.Draw(bild, "RGBA")
    _kopfzeile(d, datum)
    d.rounded_rectangle([0, 96, 730, H], radius=ECKRADIUS, fill=KASTEN,
                        corners=(False, True, False, False))
    d.rectangle([0, 142, 8, 186], fill=AKZENT)
    d.text((MARGIN, 138), AGENDA_TITEL, font=_font(True, 44), fill=HELL)
    start = 138 + 55 + 36
    n = max(1, len(eintraege))
    schritt = min(60, (H - 40 - start) // n)
    gr = 30 if schritt >= 52 else 26
    for i, eintrag in enumerate(eintraege):
        y = start + i * schritt
        hell = i == aktiv
        d.text((MARGIN, y), f"{i + 1:02d}", font=_font(True, gr),
               fill=AKZENT if hell else GEDIMMT)
        d.text((MARGIN + 72, y), eintrag[:60], font=_font(False, gr),
               fill=HELL if hell else GRAU)
    return bild


def reveal(titel: str, datum: str, motiv: Path) -> Image.Image:
    """Kapitelwechsel: das Board-Bild vollflaechig und unverdunkelt,
    darueber der Kapiteltitel in einem Kasten buendig an der linken
    Bildkante - dieselbe Formensprache wie die Randspalte der Szenen."""
    bild = _vollbild(motiv)
    d = ImageDraw.Draw(bild, "RGBA")
    for gr in (52, 46, 40):
        font = _font(True, gr)
        zeilen = _umbrechen(d, titel.upper(), font, 760 - 52 - 42)
        if len(zeilen) <= 2:
            break
    schritt = int(gr * 1.16)
    oben = 110
    unten = oben + 30 + schritt * len(zeilen) + 32
    d.rounded_rectangle([0, oben, 760, unten], radius=ECKRADIUS, fill=KASTEN,
                        corners=(False, True, True, False))
    d.rectangle([0, oben + 28, 10, unten - 28], fill=AKZENT)
    for i, z in enumerate(zeilen):
        d.text((52, oben + 30 + i * schritt), z, font=font, fill=HELL)
    return bild


def thema(titel: str, punkte: list[str], sichtbar: int, aktiv: int,
          karte: dict | None, fuss: str, datum: str,
          motiv: Path | None) -> Image.Image:
    """Themen-Folie ueber rohem Vollbild-Motiv: Titel-Kasten mit
    Lesezeichen-Icon, Stichpunkt-Kasten (der Index `aktiv` hell mit
    Amber-Marker, die uebrigen gedimmt), optional die Zahlen-Karte rechts
    unten und der Quellen-Chip am unteren Rand."""
    bild = _vollbild(motiv)
    _verlauf_oben(bild)
    d = ImageDraw.Draw(bild, "RGBA")
    _kopfzeile(d, datum)

    # Titel-Kasten: Breite folgt dem Text, Lesezeichen-Icon als Marker.
    for gr in (36, 32, 28):
        tfont = _font(True, gr)
        tzeilen = _umbrechen(d, titel.upper(), tfont, 1150 - 58 - 28)
        if len(tzeilen) <= 1:
            break
    tzeilen = tzeilen[:2]
    tschritt = int(gr * 1.22)
    tb = max(d.textlength(z, font=tfont) for z in tzeilen)
    kb = min(int(tb) + 58 + 28, 1150)
    t_unten = 100 + 14 + tschritt * len(tzeilen) + 14
    d.rounded_rectangle([MARGIN, 100, MARGIN + kb, t_unten], radius=12,
                        fill=KASTEN)
    d.rectangle([MARGIN, 112, MARGIN + 8, t_unten - 12], fill=AKZENT)
    marker = icons.icon("bookmark", 20, AKZENT)
    bild.paste(marker, (MARGIN + 24, 100 + (t_unten - 100 - 20) // 2), marker)
    for i, z in enumerate(tzeilen):
        d.text((MARGIN + 58, 100 + 14 + i * tschritt), z, font=tfont,
               fill=HELL)

    # Stichpunkt-Kasten: schrumpfen, bis alle in die Flaeche passen. Reicht
    # selbst die kleinste Schrift nicht, weichen die AELTESTEN Punkte nach
    # oben hinaus - ein neu erscheinender Punkt muss immer zu sehen sein.
    p_oben = t_unten + 36
    innen = 660 - 63 - 32
    for gr in (26, 24, 22):
        font = _font(False, gr)
        zeilenhoehe = int(gr * 1.38)
        hoehe = 0
        for p in punkte:
            hoehe += len(_umbrechen(d, p, font, innen)) * zeilenhoehe + 16
        if p_oben + 28 + hoehe - 16 + 28 <= PUNKTE_UNTEN_MAX:
            break

    def _block_hoehe(p: str) -> int:
        return len(_umbrechen(d, p, font, innen)) * zeilenhoehe + 16

    gezeigt = list(enumerate(punkte[:sichtbar]))
    while len(gezeigt) > 1 and \
            p_oben + 28 + sum(_block_hoehe(p) for _, p in gezeigt) - 16 + 28 \
            > PUNKTE_UNTEN_MAX:
        gezeigt.pop(0)
    if gezeigt:
        box_unten = p_oben + 28 \
            + sum(_block_hoehe(p) for _, p in gezeigt) - 16 + 28
        d.rounded_rectangle([MARGIN, p_oben, MARGIN + 660, box_unten],
                            radius=12, fill=KASTEN)
        y = p_oben + 28
        for i, p in gezeigt:
            d.rectangle([MARGIN + 32, y + 12, MARGIN + 43, y + 23],
                        fill=AKZENT if i == aktiv else NEBEN)
            for z in _umbrechen(d, p, font, innen):
                d.text((MARGIN + 63, y), z, font=font,
                       fill=HELL if i == aktiv else PUNKT_ALT)
                y += zeilenhoehe
            y += 16
    if karte:
        _zahlen_karte(d, karte, 764, 440, 452, 204, rahmen=2,
                      wert_groessen=(64, 56, 48))
    if fuss:
        cf = _font(False, 22)
        cw = d.textlength(fuss, font=cf)
        d.rounded_rectangle([MARGIN, H - 68, MARGIN + 18 + int(cw) + 18,
                             H - 24], radius=8, fill=KASTEN)
        d.text((MARGIN + 18, H - 60), fuss, font=cf, fill=NEBEN)
    return bild


def zahlen(karten: list[dict], sichtbar: int, datum: str,
           motiv: Path | None) -> Image.Image:
    """Zahlen-des-Tages-Folie: bis zu vier Karten im Raster auf stark
    abgedunkelter Flaeche, die ersten `sichtbar` sind zu sehen, die
    zuletzt erschienene traegt den Amber-Rahmen."""
    bild = _vollbild(motiv, deckung=VOLLBILD_DECKUNG, entsaettigen=0.5)
    d = ImageDraw.Draw(bild, "RGBA")
    d.text((MARGIN, 36), KOPF_TEXT, font=_font(True, 24), fill=AKZENT)
    breite = d.textlength(datum, font=_font(False, 24))
    d.text((B - MARGIN - breite, 36), datum, font=_font(False, 24), fill=GRAU)
    d.rectangle([MARGIN, 112, MARGIN + 12, 162], fill=AKZENT)
    d.text((100, 106), ZAHLEN_TITEL, font=_font(True, 52), fill=HELL)
    for i, karte in enumerate(karten[:4][:sichtbar]):
        x = MARGIN + (i % 2) * 592
        y = 224 + (i // 2) * 228
        _zahlen_karte(d, karte, x, y, 560, 204,
                      rahmen=3 if i == sichtbar - 1 else 0, bg=KARTE_BG)
    d.text((MARGIN, 678), "All figures: poster claims from the source threads",
           font=_font(False, 22), fill=GEDIMMT)
    return bild


def outro(datum: str, motiv: Path | None) -> Image.Image:
    """Abbinder: fast schwarze Flaeche, Serientitel linksbuendig mit
    Amber-Linie darunter - ruhiges Ende statt zentrierter Tafel."""
    bild = _vollbild(motiv, deckung=OUTRO_DECKUNG, entsaettigen=0.5)
    d = ImageDraw.Draw(bild)
    breite = d.textlength(datum, font=_font(False, 24))
    d.text((B - MARGIN - breite, 42), datum, font=_font(False, 24), fill=GRAU)
    d.text((MARGIN, 252), OUTRO_TITEL, font=_font(True, 84), fill=HELL)
    d.rectangle([MARGIN, 376, MARGIN + 548, 386], fill=AKZENT)
    d.text((MARGIN, 420), OUTRO_ZEILE1, font=_font(False, 34), fill=GRAU)
    d.text((MARGIN, 478), OUTRO_ZEILE2, font=_font(False, 28), fill=GEDIMMT)
    return bild


def blend(von: Image.Image, nach: Image.Image, schritte: int) -> list[Image.Image]:
    """Zwischenbilder fuer die weiche Ueberblendung (Reveal -> Folie); als
    Standbilder in der ffconcat-Liste ersetzt das fragile xfade-Filterketten."""
    return [Image.blend(von, nach, (i + 1) / (schritte + 1))
            for i in range(schritte)]


def speichern(bild: Image.Image, ziel: Path) -> Path:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel, "JPEG", quality=JPEG_QUALITAET)
    return ziel
