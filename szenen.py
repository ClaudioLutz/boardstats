#!/usr/bin/env python3
"""Overlay-Grafiken fuer das /biz/-Video im Szenen-Layout (v7, 16.08.2026).

Weg vom Folien-Look: Das Video besteht aus Szenen mit vollflaechigem,
langsam driftendem Board-Bild (ffmpeg zoompan); aller Text liegt als
transparente 1280x720-PNG-Overlays darueber, die ffmpeg zeitgesteuert ein-
und ausblendet. Dieses Modul rendert nur die Overlays (PIL, RGBA, Position
eingebacken) - Szenen-Timing und ffmpeg-Aufbau macht video_report.py.

Bausteine: Ecken-Bug (Serienmarke + Datum), Vignette (Lesbarkeits-Verlauf,
als Overlay statt im Hintergrund, damit sie nicht mitzoomt), Titel-Karte
(Lower Third fuer Intro/Kapitel/Zwischenthemen), persistente Themen-Karte
(Titel + auflaufende Stichpunkte, steht bis zum Themenwechsel),
Zitat-Karte im 4chan-Post-Look (blue board), Gross-Zahl-Tafel mit
Count-up-Stufen und Outro-Tafel. Farb- und Schrift-Vokabular kommt aus
thumbnail.py, gemessen und umbrochen wird mit den Helfern aus folien.py.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

import folien
import thumbnail

B = thumbnail.BREITE
H = thumbnail.HOEHE
AKZENT = thumbnail.AKZENT
HELL = thumbnail.TEXT_HELL
GRAU = thumbnail.TEXT_GRAU
GEDIMMT = (150, 155, 172)
MARGIN = 64

BUG_TEXT = "4CHAN /biz/  ·  BOARD REPORT"

# 4chan blue board (/biz/): Antwort-Karte, Rand, Name, Greentext
POST_KARTE = (214, 218, 240)
POST_RAND = (183, 197, 217)
POST_NAME = (17, 119, 67)
POST_TEXT = (30, 30, 40)
POST_GRUEN = (120, 153, 34)


def _leer() -> Image.Image:
    return Image.new("RGBA", (B, H), (0, 0, 0, 0))


def _bande(bild: Image.Image, oben: int, unten: int, alpha: int = 150) -> None:
    """Halbtransparente schwarze Bande ueber die volle Breite - gibt Text auf
    unruhigen Board-Bildern Halt, ohne das Bild ganz zu verdecken."""
    ImageDraw.Draw(bild).rectangle([0, oben, B, unten], fill=(0, 0, 0, alpha))


def bug(datum: str) -> Image.Image:
    """Ecken-Marke oben: Serienname links, Datum rechts. Liegt als eigenes
    statisches Overlay auf jeder Szene (im Hintergrund wuerde sie mitzoomen)."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    d.text((40, 30), BUG_TEXT, font=folien._font(True, 24), fill=AKZENT,
           stroke_width=2, stroke_fill=(0, 0, 0))
    breite = d.textlength(datum, font=folien._font(False, 24))
    d.text((B - 40 - breite, 30), datum, font=folien._font(False, 24),
           fill=GRAU, stroke_width=2, stroke_fill=(0, 0, 0))
    return bild


def vignette() -> Image.Image:
    """Weicher Verlauf unten (Textzone) und ein Hauch oben (Bug-Zone)."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    for y in range(400, H):
        a = int(165 * (y - 400) / (H - 400))
        d.line([(0, y), (B, y)], fill=(0, 0, 0, a))
    for y in range(0, 96):
        d.line([(0, y), (B, y)], fill=(0, 0, 0, int(110 * (1 - y / 96))))
    return bild


def titel_karte(text: str, label: str = "", quelle: str = "",
                gross: bool = True) -> Image.Image:
    """Lower Third: optionales Amber-Label, grosser Titel mit Amber-Balken,
    optionale Quellenzeile. Fuer Intro-Hook, Kapitel-Opener, Agenda-Eintraege
    und Zwischenthemen (gross=False rendert eine kleinere Stufe)."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    groessen = (56, 48, 40) if gross else (44, 38, 32)
    breite = B - 2 * MARGIN - 120
    for gr in groessen:
        font = folien._font(True, gr)
        zeilen = folien._umbrechen(d, text.upper(), font, breite)
        if len(zeilen) <= 3:
            break
    schritt = int(gr * 1.16)
    unterkante = H - (128 if quelle else 96)
    text_oben = unterkante - schritt * len(zeilen)
    label_oben = text_oben - (44 if label else 0)
    _bande(bild, label_oben - 26, H - 56, alpha=150)
    d = ImageDraw.Draw(bild)
    if label:
        d.text((MARGIN + 40, label_oben), label.upper(),
               font=folien._font(True, 26), fill=AKZENT)
    d.rectangle([MARGIN, text_oben + 8, MARGIN + 14,
                 text_oben + schritt * len(zeilen) - 6], fill=AKZENT)
    for i, z in enumerate(zeilen):
        d.text((MARGIN + 40, text_oben + i * schritt), z, font=font, fill=HELL,
               stroke_width=3, stroke_fill=(0, 0, 0))
    if quelle:
        d.text((MARGIN + 40, unterkante + 10), quelle,
               font=folien._font(False, 22), fill=GEDIMMT)
    return bild


KARTE_BREITE = 470
KARTE_OBEN = 104        # unter dem Ecken-Bug
KARTE_UNTEN_MAX = 560   # Lower Thirds laufen nie gleichzeitig mit der Karte
KARTE_ALT = (198, 203, 216)


def themen_karte(titel: str, punkte: list[str], sichtbar: int,
                 lage: str = "left") -> Image.Image:
    """Persistente Themen-Karte: Kapitel- oder Zwischenthemen-Titel mit
    auflaufenden Stichpunkten - sie steht, bis das (Sub-)Thema wechselt,
    damit das Gesprochene immer von Text gestuetzt ist. Der juengste Punkt
    ist hervorgehoben; passt der Verlauf nicht mehr in die Hoehe, werden
    die aeltesten Punkte verdraengt. Die Bildseite (lage: left/right)
    bestimmt das Drehbuch."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    x = B - MARGIN - KARTE_BREITE if lage == "right" else MARGIN
    innen = KARTE_BREITE - 34 - 24
    tf = folien._font(True, 30)
    tzeilen = folien._umbrechen(d, titel.upper(), tf, innen)[:2]
    pf = folien._font(True, 25)
    bloecke = [folien._umbrechen(d, p.upper(), pf, innen)[:2]
               for p in punkte[:max(sichtbar, 0)]]
    # von hinten so viele Punkte aufnehmen wie reinpassen (der juengste zuerst)
    h = 20 + len(tzeilen) * 38 + (18 if bloecke else 0) + 20
    anzeige: list[list[str]] = []
    for zeilen in reversed(bloecke):
        dh = len(zeilen) * 32 + 10
        if anzeige and h + dh > KARTE_UNTEN_MAX - KARTE_OBEN:
            break
        anzeige.insert(0, zeilen)
        h += dh
    unten = KARTE_OBEN + h
    d.rounded_rectangle([x, KARTE_OBEN, x + KARTE_BREITE, unten],
                        radius=12, fill=(0, 0, 0, 160))
    d.rectangle([x, KARTE_OBEN + 12, x + 8, unten - 12], fill=AKZENT)
    y = KARTE_OBEN + 20
    for z in tzeilen:
        d.text((x + 34, y), z, font=tf, fill=HELL,
               stroke_width=2, stroke_fill=(0, 0, 0))
        y += 38
    if anzeige:
        d.rectangle([x + 34, y + 4, x + 34 + 56, y + 8], fill=AKZENT)
        y += 18
    for i, zeilen in enumerate(anzeige):
        y += 10
        aktiv = i == len(anzeige) - 1
        d.rectangle([x + 34, y + 9, x + 44, y + 19],
                    fill=AKZENT if aktiv else GEDIMMT)
        for z in zeilen:
            d.text((x + 56, y), z, font=pf,
                   fill=HELL if aktiv else KARTE_ALT)
            y += 32
    return bild


def zitat_post(text: str, datum: str) -> Image.Image:
    """Board-Zitat als 4chan-Antwortkarte (blue board): heller Karton,
    gruener Anonymous-Name, Greentext-Zeilen in Boardgruen."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    font = folien._font(False, 27)
    kw = 780
    zeilen: list[str] = []
    for roh in text.splitlines() or [text]:
        zeilen += folien._umbrechen(d, roh.strip(), font, kw - 2 * 30) or [""]
    zeilen = zeilen[:7]
    zh = 38
    kh = 52 + len(zeilen) * zh + 30
    x, y = (B - kw) // 2, max(120, (H - kh) // 2 - 40)
    d.rounded_rectangle([x + 8, y + 10, x + kw + 8, y + kh + 10], radius=6,
                        fill=(0, 0, 0, 130))
    d.rounded_rectangle([x, y, x + kw, y + kh], radius=6, fill=POST_KARTE,
                        outline=POST_RAND, width=2)
    d.text((x + 30, y + 16), "Anonymous", font=folien._font(True, 26),
           fill=POST_NAME)
    kopf_w = d.textlength("Anonymous", font=folien._font(True, 26))
    d.text((x + 30 + kopf_w + 18, y + 20), f"{datum}  ·  /biz/",
           font=folien._font(False, 22), fill=(52, 52, 92))
    for i, z in enumerate(zeilen):
        farbe = POST_GRUEN if z.startswith(">") else POST_TEXT
        d.text((x + 30, y + 56 + i * zh), z, font=font, fill=farbe)
    return bild


def zahl_tafel(wert: str, titel: str, sub: str) -> Image.Image:
    """Bildschirmfuellende Zahl: der grosse Moment fuer die eine Kennzahl."""
    bild = _leer()
    _bande(bild, 208, 540, alpha=150)
    d = ImageDraw.Draw(bild)
    for gr in (128, 108, 88, 68):
        font = folien._font(True, gr)
        if d.textlength(wert, font=font) <= B - 2 * MARGIN:
            break
    d.text(((B - d.textlength(wert, font=font)) / 2, 236), wert, font=font,
           fill=AKZENT, stroke_width=4, stroke_fill=(0, 0, 0))
    tf = folien._font(True, 40)
    d.text(((B - d.textlength(titel, font=tf)) / 2, 400), titel, font=tf,
           fill=HELL)
    sf = folien._font(False, 27)
    d.text(((B - d.textlength(sub, font=sf)) / 2, 462), sub, font=sf, fill=GRAU)
    return bild


def outro_tafel() -> Image.Image:
    bild = _leer()
    _bande(bild, 220, 540, alpha=160)
    d = ImageDraw.Draw(bild)
    t = "/biz/ BOARD REPORT"
    tf = folien._font(True, 72)
    x = (B - d.textlength(t, font=tf)) / 2
    d.text((x, 260), t, font=tf, fill=HELL, stroke_width=4, stroke_fill=(0, 0, 0))
    d.rectangle([int(x), 360, int(x) + 340, 368], fill=AKZENT)
    d.text((x, 396), "New every day", font=folien._font(False, 34), fill=GRAU)
    d.text((x, 452), "Source threads and chapters in the description",
           font=folien._font(False, 26), fill=GEDIMMT)
    return bild


_ZAHL = re.compile(r"-?\d[\d,]*(?:\.\d+)?")

COUNTUP_STUFEN = (0.18, 0.42, 0.65, 0.85)


def countup_werte(wert: str) -> list[str]:
    """Zwischenstaende fuer den Zahlen-Count-up: die erste Zahl im String
    waechst in Stufen auf den Endwert, Praefix/Suffix bleiben stehen.
    Leer, wenn der Wert keine Zahl enthaelt."""
    m = _ZAHL.search(wert)
    if not m:
        return []
    roh = m.group(0)
    zahl = float(roh.replace(",", ""))
    dezimal = len(roh.split(".")[1]) if "." in roh else 0
    aus = []
    for f in COUNTUP_STUFEN:
        z = zahl * f
        s = f"{z:,.{dezimal}f}" if "," in roh else f"{z:.{dezimal}f}"
        aus.append(wert[:m.start()] + s + wert[m.end():])
    return aus


def speichern(bild: Image.Image, ziel: Path) -> Path:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel, "PNG")
    return ziel
