#!/usr/bin/env python3
"""Praesentations-Folien fuer das /biz/-Video (v6, 16.08.2026).

Rendert die Standbilder der Praesentation als 1280x720-Bilder im
Design-Vokabular von thumbnail.py (dunkler Grund, Amber-Akzent, Balken,
Kopf- und Fusszeile): Intro mit dem Tages-Aufhaenger, Agenda, je
Berichtsabschnitt eine Themen-Folie mit Stichpunkten und optionaler
Zahlen-Karte, eine "Numbers of the day"-Folie und ein Outro. Dazu die
Reveal-Bilder (rohes Board-Bild mit Titelbande) und die Blend-Zwischenbilder
fuer den Folienuebergang.

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

import thumbnail

B = thumbnail.BREITE
H = thumbnail.HOEHE
GRUND = thumbnail.GRUND
AKZENT = thumbnail.AKZENT
HELL = thumbnail.TEXT_HELL
GRAU = thumbnail.TEXT_GRAU
GEDIMMT = (120, 125, 142)     # inaktive Stichpunkte / Nebentext
KARTE_BG = (35, 35, 66)       # Zahlen-Karten, etwas heller als der Grund
LINIE = (60, 62, 92)
MARGIN = 64

KOPF_TEXT = "4CHAN /biz/  ·  BOARD REPORT"
INTRO_LABEL = "TODAY'S TOP STORY"
AGENDA_TITEL = "In today's report"
ZAHLEN_TITEL = "Numbers of the day"
OUTRO_TITEL = "/biz/ BOARD REPORT"
OUTRO_ZEILE1 = "New every day"
OUTRO_ZEILE2 = "Source threads and chapters in the description"

VOLLBILD_DECKUNG = 0.82       # Abdunkelung vollflaechiger Hintergruende
PUNKTE_UNTEN_MAX = 648        # Stichpunkte muessen oberhalb der Fusszeile enden
JPEG_QUALITAET = 90


@lru_cache(maxsize=32)
def _font(fett: bool, groesse: int) -> ImageFont.FreeTypeFont:
    kandidaten = (thumbnail.FONT_FETT_KANDIDATEN if fett
                  else thumbnail.FONT_NORMAL_KANDIDATEN)
    return ImageFont.truetype(thumbnail._font_pfad(kandidaten), groesse)


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


def _grund(motiv: Path | None) -> Image.Image:
    """Dunkle Grundflaeche, rechts das Motiv mit weicher Kante (wie beim
    Vorschaubild). Ohne Motiv bleibt die reine Farbflaeche."""
    bild = Image.new("RGB", (B, H), GRUND)
    if motiv is not None:
        try:
            bild.paste(thumbnail._motiv_flaeche(motiv), (B - thumbnail.MOTIV_BREITE, 0),
                       thumbnail._blende())
        except OSError:
            pass  # kaputtes Bild: Farbflaeche statt Abbruch
    return bild


def _vollbild(motiv: Path | None, deckung: float = VOLLBILD_DECKUNG,
              entsaettigen: float = 0.5) -> Image.Image:
    """Vollflaechiger Bildhintergrund, hinter GRUND abgedunkelt - Karten und
    Text dominieren, das Board-Bild gibt nur Atmosphaere."""
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


def _kopfzeile(d: ImageDraw.ImageDraw, datum: str) -> None:
    d.text((MARGIN, 42), KOPF_TEXT, font=_font(True, 26), fill=AKZENT,
           stroke_width=2, stroke_fill=GRUND)
    breite = d.textlength(datum, font=_font(False, 26))
    d.text((B - MARGIN - breite, 42), datum, font=_font(False, 26), fill=GRAU,
           stroke_width=2, stroke_fill=GRUND)
    d.line([(MARGIN, 88), (B - MARGIN, 88)], fill=LINIE, width=2)


def _fusszeile(d: ImageDraw.ImageDraw, text: str) -> None:
    d.text((MARGIN, H - 58), text, font=_font(False, 22), fill=GEDIMMT,
           stroke_width=2, stroke_fill=GRUND)


def _titelblock(d: ImageDraw.ImageDraw, titel: str, y: int, breite: int,
                groesse: int) -> int:
    """Folientitel mit Amber-Balken links; schrumpft, bis er in zwei Zeilen
    passt. Liefert die Unterkante."""
    for gr in (groesse, groesse - 6, groesse - 12):
        font = _font(True, gr)
        zeilen = _umbrechen(d, titel.upper(), font, breite)
        if len(zeilen) <= 2:
            break
    schritt = int(gr * 1.15)
    d.rectangle([MARGIN, y + 6, MARGIN + 12, y + schritt * len(zeilen) - 4],
                fill=AKZENT)
    for i, z in enumerate(zeilen):
        d.text((MARGIN + 36, y + i * schritt), z, font=font, fill=HELL,
               stroke_width=3, stroke_fill=GRUND)
    return y + schritt * len(zeilen)


def _zahlen_karte(d: ImageDraw.ImageDraw, karte: dict, x: int, y: int,
                  breite: int, hoehe: int, rahmen: bool = False) -> None:
    d.rounded_rectangle([x, y, x + breite, y + hoehe], radius=14, fill=KARTE_BG,
                        outline=AKZENT if rahmen else None,
                        width=2 if rahmen else 0)
    d.rectangle([x, y + 20, x + 8, y + hoehe - 20], fill=AKZENT)
    wert = str(karte.get("wert", ""))[:14]
    for gr in (56, 48, 40):
        if d.textlength(wert, font=_font(True, gr)) <= breite - 60:
            break
    d.text((x + 36, y + 22), wert, font=_font(True, gr), fill=AKZENT)
    d.text((x + 36, y + hoehe - 84), str(karte.get("titel", ""))[:40],
           font=_font(False, 26), fill=HELL)
    d.text((x + 36, y + hoehe - 48), str(karte.get("sub", ""))[:44],
           font=_font(False, 23), fill=GRAU)


# ------------------------------------------------------------------ Folien

def intro(hook: str, datum: str, motiv: Path | None) -> Image.Image:
    bild = _grund(motiv)
    d = ImageDraw.Draw(bild)
    _kopfzeile(d, datum)
    d.text((MARGIN, 160), INTRO_LABEL, font=_font(True, 28), fill=AKZENT,
           stroke_width=2, stroke_fill=GRUND)
    breite = 780 if motiv is not None else B - 2 * MARGIN - 40
    for gr in (62, 54, 46):
        font = _font(True, gr)
        zeilen = _umbrechen(d, hook.upper(), font, breite)
        if len(zeilen) <= 4:
            break
    schritt = int(gr * 1.16)
    y = 220
    d.rectangle([MARGIN, y + 8, MARGIN + 14, y + schritt * len(zeilen) - 6],
                fill=AKZENT)
    for i, z in enumerate(zeilen):
        d.text((MARGIN + 40, y + i * schritt), z, font=font, fill=HELL,
               stroke_width=4, stroke_fill=GRUND)
    _fusszeile(d, f"Daily report from the 4chan business board  ·  {datum}")
    return bild


def agenda(eintraege: list[str], aktiv: int, datum: str,
           motiv: Path | None) -> Image.Image:
    """Kapitel-Uebersicht; der gerade gesprochene Eintrag (aktiv, -1 = keiner)
    steht hell mit Amber-Nummer, die uebrigen gedimmt."""
    bild = _vollbild(motiv)
    d = ImageDraw.Draw(bild)
    _kopfzeile(d, datum)
    unten = _titelblock(d, AGENDA_TITEL, 124, B - 2 * MARGIN - 40, 52)
    start = unten + 34
    n = max(1, len(eintraege))
    schritt = min(54, (H - 80 - start) // n)
    gr = 32 if schritt >= 48 else 26
    for i, eintrag in enumerate(eintraege):
        y = start + i * schritt
        hell = i == aktiv
        d.text((MARGIN + 36, y), f"{i + 1:02d}", font=_font(True, gr),
               fill=AKZENT if hell else GEDIMMT,
               stroke_width=2, stroke_fill=GRUND)
        d.text((MARGIN + 106, y), eintrag[:70], font=_font(False, gr),
               fill=HELL if hell else GRAU,
               stroke_width=2, stroke_fill=GRUND)
    return bild


def reveal(titel: str, datum: str, motiv: Path) -> Image.Image:
    """Kapitelwechsel: das Board-Bild vollflaechig und unverdunkelt, darueber
    nur die Kapitel-Ueberschrift auf halbtransparenter Bande. Der Titel nutzt
    exakt die Umbruch-Geometrie von thema() (Breite 620, gleiche
    Schriftgroessen), damit er in der Ueberblendung deckungsgleich in den
    Folientitel uebergeht statt doppelt zu stehen."""
    bild = _vollbild(motiv, deckung=0.0, entsaettigen=1.0).convert("RGBA")
    d = ImageDraw.Draw(bild)
    for gr in (48, 42, 36):
        font = _font(True, gr)
        zeilen = _umbrechen(d, titel.upper(), font, 620)
        if len(zeilen) <= 2:
            break
    schritt = int(gr * 1.15)
    oben, unten = 124, 124 + schritt * len(zeilen)
    bande = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    ImageDraw.Draw(bande).rectangle([0, oben - 26, B, unten + 20],
                                    fill=(0, 0, 0, 176))
    bild = Image.alpha_composite(bild, bande)
    d = ImageDraw.Draw(bild)
    d.rectangle([MARGIN, oben + 6, MARGIN + 12, unten - 4], fill=AKZENT)
    for i, z in enumerate(zeilen):
        d.text((MARGIN + 36, oben + i * schritt), z, font=font, fill=HELL,
               stroke_width=3, stroke_fill=(0, 0, 0))
    return bild.convert("RGB")


def thema(titel: str, punkte: list[str], sichtbar: int, aktiv: int,
          karte: dict | None, fuss: str, datum: str,
          motiv: Path | None) -> Image.Image:
    """Themen-Folie: Titel, bis zu `sichtbar` Stichpunkte (der Index `aktiv`
    hell, die uebrigen gedimmt), optional die Zahlen-Karte rechts unten."""
    bild = _grund(motiv)
    d = ImageDraw.Draw(bild)
    _kopfzeile(d, datum)
    text_breite = 620 if motiv is not None else B - 2 * MARGIN - 60
    unten = _titelblock(d, titel, 124, text_breite, 48)

    # Stichpunkte: schrumpfen, bis alle in die Flaeche passen; was dann noch
    # ueberlaeuft, faellt weg (lieber weniger Punkte als Text im Anschnitt).
    for gr in (29, 26, 24):
        font = _font(False, gr)
        zeilenhoehe = int(gr * 1.38)
        y = unten + 36
        hoehe = 0
        for p in punkte:
            hoehe += len(_umbrechen(d, p, font, text_breite - 96)) * zeilenhoehe + 14
        if unten + 36 + hoehe <= PUNKTE_UNTEN_MAX:
            break
    y = unten + 36
    for i, p in enumerate(punkte[:sichtbar]):
        if y >= PUNKTE_UNTEN_MAX - zeilenhoehe:
            break
        farbe = HELL if i == aktiv else GEDIMMT
        d.rectangle([MARGIN + 36, y + 12, MARGIN + 48, y + 24],
                    fill=AKZENT if i == aktiv else GEDIMMT)
        for z in _umbrechen(d, p, font, text_breite - 96):
            d.text((MARGIN + 72, y), z, font=font, fill=farbe,
                   stroke_width=2, stroke_fill=GRUND)
            y += zeilenhoehe
        y += 14
    if karte:
        _zahlen_karte(d, karte, 764, 428, 452, 200, rahmen=True)
    _fusszeile(d, fuss)
    return bild


def zahlen(karten: list[dict], sichtbar: int, datum: str,
           motiv: Path | None) -> Image.Image:
    """Zahlen-des-Tages-Folie: bis zu vier Karten im Raster, die ersten
    `sichtbar` sind zu sehen, die zuletzt erschienene traegt den Rahmen."""
    bild = _vollbild(motiv)
    d = ImageDraw.Draw(bild)
    _kopfzeile(d, datum)
    _titelblock(d, ZAHLEN_TITEL, 124, B - 2 * MARGIN - 40, 52)
    for i, karte in enumerate(karten[:4][:sichtbar]):
        x = MARGIN + (i % 2) * 590
        y = 250 + (i // 2) * 210
        _zahlen_karte(d, karte, x, y, 560, 180, rahmen=(i == sichtbar - 1))
    _fusszeile(d, "All figures: poster claims from the source threads")
    return bild


def outro(datum: str, motiv: Path | None) -> Image.Image:
    bild = _vollbild(motiv, deckung=0.86)
    d = ImageDraw.Draw(bild)
    _kopfzeile(d, datum)
    d.text((MARGIN, 270), OUTRO_TITEL, font=_font(True, 76), fill=HELL,
           stroke_width=4, stroke_fill=GRUND)
    d.rectangle([MARGIN, 380, 560, 388], fill=AKZENT)
    d.text((MARGIN, 420), OUTRO_ZEILE1, font=_font(False, 34), fill=GRAU)
    d.text((MARGIN, 476), OUTRO_ZEILE2, font=_font(False, 28), fill=GEDIMMT)
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
