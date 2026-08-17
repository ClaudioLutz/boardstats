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

from PIL import Image, ImageDraw, ImageFont

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
KARTE_OBEN = 104        # unter dem Ecken-Bug; mit Themen-Titel oben tiefer
KARTE_UNTEN_MAX = 600   # Lower Thirds laufen nie gleichzeitig mit der Karte
KARTE_ALT = (198, 203, 216)
KARTE_INNEN = KARTE_BREITE - 34 - 24   # Textbreite im Kasten
KARTE_TEXT_X = 56       # Einzug des Punkt-Textes (neben dem Quadrat)
KARTE_PUNKT_FONT = 25
# Deckkraft der Text-Kaesten. Hoeher als die frueheren 160/170: der Text
# liegt auf rohem Board-Motiv, und dessen Feinstruktur (oft Screenshots mit
# Text) frisst Kontrast. Zusammen mit der milden Unschaerfe des Motivs
# (video_report.motiv_weich) ist das Bild noch klar erkennbar, der Text aber
# nicht mehr in Konkurrenz dazu.
KARTE_ALPHA = 198

TITEL_OBEN = 74         # unter dem Bug, dessen Text bei y=30 sitzt
TITEL_RAND = 28
TITEL_ZEILE = 48


def _titel_zeilen(d: ImageDraw.ImageDraw, titel: str
                  ) -> tuple[list[str], ImageFont.FreeTypeFont]:
    """Titelzeilen und Schriftgrad fuer den Themen-Titel oben.

    Oben ist die volle Bildbreite frei, deshalb bleibt fast jeder Titel
    einzeilig; zwei Stufen kleiner Schrift kaufen die Einzeiligkeit auch bei
    langen Titeln, bevor auf zwei Zeilen umbrochen wird."""
    breite = B - 2 * MARGIN - 2 * TITEL_RAND - 34
    for gr in (40, 34, 30):
        f = folien._font(True, gr)
        zeilen = folien._umbrechen(d, titel.upper(), f, breite)
        if len(zeilen) == 1:
            return zeilen, f
    return zeilen[:2], f


def titel_unterkante(titel: str) -> int:
    """Unterkante des Themen-Titel-Kastens - darunter beginnt die Karte."""
    zeilen, _ = _titel_zeilen(ImageDraw.Draw(_leer()), titel)
    return TITEL_OBEN + 16 + len(zeilen) * TITEL_ZEILE + 16


def themen_titel(titel: str) -> Image.Image:
    """Titel des laufenden (Zwischen-)Themas als eigener Kasten oben links.

    Stand vorher in der Themen-Karte, wo er zwei Nachteile hatte: er nahm
    der Stichpunktliste Hoehe, und auf Kartenbreite umbrochen brauchte er
    fast immer zwei Zeilen. Oben traegt er den Platz, den ein laufendes
    Thema verdient, und darf dafuer kleiner sein als ein Lower Third (40
    statt 48-56). Kein Kapitel-Label: die Nummer sagt dem Zuschauer
    nichts, die Kapitelmarken in der Beschreibung tun es."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    zeilen, f = _titel_zeilen(d, titel)
    tb = max(d.textlength(z, font=f) for z in zeilen)
    kb = min(int(tb) + 34 + 2 * TITEL_RAND, B - 2 * MARGIN)
    unten = titel_unterkante(titel)
    d.rounded_rectangle([MARGIN, TITEL_OBEN, MARGIN + kb, unten],
                        radius=12, fill=(0, 0, 0, KARTE_ALPHA))
    d.rectangle([MARGIN, TITEL_OBEN + 12, MARGIN + 8, unten - 12], fill=AKZENT)
    for i, z in enumerate(zeilen):
        d.text((MARGIN + 34, TITEL_OBEN + 16 + i * TITEL_ZEILE), z, font=f,
               fill=HELL, stroke_width=2, stroke_fill=(0, 0, 0))
    return bild


def _karte_layout(d: ImageDraw.ImageDraw, punkte: list[str], sichtbar: int,
                  lage: str, oben: int
                  ) -> tuple[int, list[list[str]], list[int], int]:
    """Layoutrechnung der Themen-Karte, getrennt vom Zeichnen.

    Zurueck kommen die linke Kante, die tatsaechlich angezeigten
    Punkt-Bloecke, deren y-Positionen und die Unterkante des Kastens.
    Getrennt, weil zwei Aufrufer dieselbe Rechnung brauchen: themen_karte
    zum Zeichnen und karte_punkt_ziel fuer das Flugziel der Fokus-Karte.
    Die Position darf nicht aus dem vorigen Stand hochgerechnet werden -
    greift die Verdraengung, rutscht der juengste Punkt nach oben statt
    eine Zeile nach unten."""
    x = B - MARGIN - KARTE_BREITE if lage == "right" else MARGIN
    pf = folien._font(True, KARTE_PUNKT_FONT)
    bloecke = [folien._umbrechen(d, p.upper(), pf, KARTE_INNEN)[:2]
               for p in punkte[:max(sichtbar, 0)]]
    # von hinten so viele Punkte aufnehmen wie reinpassen (der juengste zuerst)
    h = 20 + 20
    anzeige: list[list[str]] = []
    for zeilen in reversed(bloecke):
        dh = len(zeilen) * 32 + 10
        if anzeige and h + dh > KARTE_UNTEN_MAX - oben:
            break
        anzeige.insert(0, zeilen)
        h += dh
    y = oben + 20
    punkt_y: list[int] = []
    for zeilen in anzeige:
        y += 10
        punkt_y.append(y)
        y += len(zeilen) * 32
    return x, anzeige, punkt_y, oben + h


def themen_karte(punkte: list[str], sichtbar: int, lage: str = "left",
                 oben: int = KARTE_OBEN) -> Image.Image:
    """Persistente Liste der bereits geparkten Stichpunkte - sie steht, bis
    das (Sub-)Thema wechselt. Der Punkt, ueber den gerade gesprochen wird,
    steht nicht hier, sondern als fokus_punkt in der freien Bildhaelfte; er
    landet hier erst, wenn der naechste ihn ersetzt. Alle geparkten Punkte
    sind gleich gedimmt: hervorgehoben ist, was in der Mitte steht, und
    zwei gleichzeitige Hervorhebungen wuerden sich widersprechen. Passt der
    Verlauf nicht mehr in die Hoehe, werden die aeltesten Punkte
    verdraengt. Die Bildseite (lage: left/right) bestimmt das Drehbuch, den
    oberen Rand der Themen-Titel darueber."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    x, anzeige, punkt_y, unten = _karte_layout(d, punkte, sichtbar, lage, oben)
    if not anzeige:
        return bild
    d.rounded_rectangle([x, oben, x + KARTE_BREITE, unten],
                        radius=12, fill=(0, 0, 0, KARTE_ALPHA))
    d.rectangle([x, oben + 12, x + 8, unten - 12], fill=AKZENT)
    pf = folien._font(True, KARTE_PUNKT_FONT)
    for zeilen, py in zip(anzeige, punkt_y):
        d.rectangle([x + 34, py + 9, x + 44, py + 19], fill=GEDIMMT)
        for j, z in enumerate(zeilen):
            d.text((x + KARTE_TEXT_X, py + j * 32), z, font=pf, fill=KARTE_ALT)
    return bild


def karte_punkt_ziel(punkte: list[str], sichtbar: int, lage: str = "left",
                     oben: int = KARTE_OBEN) -> tuple[int, int] | None:
    """Wo der Text des juengsten Punkts im Kartenstand `sichtbar` steht -
    das Flugziel der Fokus-Karte. Gerechnet wird mit genau dem Stand, der
    nach der Landung geschnitten wird."""
    x, anzeige, punkt_y, _ = _karte_layout(
        ImageDraw.Draw(_leer()), punkte, sichtbar, lage, oben)
    if not anzeige or not punkt_y:
        return None
    return x + KARTE_TEXT_X, punkt_y[-1]


def karte_text(text: str) -> str:
    """Der Stichpunkt so, wie ihn die Themen-Karte zeigt: auf die
    Kartenbreite umbrochen und auf zwei Zeilen gekappt.

    Die Fokus-Karte in der Bildmitte hat deutlich mehr Platz. Ohne diese
    Kappung stuende dort Text, der beim Parken in der Karte wegfaellt -
    das Parken waere dann ein sichtbarer Informationsverlust."""
    zeilen = folien._umbrechen(ImageDraw.Draw(_leer()), text.upper(),
                              folien._font(True, KARTE_PUNKT_FONT),
                              KARTE_INNEN)[:2]
    return " ".join(zeilen)


FOKUS_BREITE = 620
FOKUS_MITTE = 318       # vertikale Mitte des Kastens: hoch genug, dass ein
                        # ein- oder zweizeiliger Kapitel-Opener darunter Platz
                        # hat (dessen Bande beginnt bei y=426), tief genug,
                        # dass die Bildmitte belebt wird und nicht der
                        # Kopfbereich. Bei einem dreizeiligen Opener (Bande ab
                        # y=362) beruehrt eine zweizeilige Fokus-Karte die
                        # Bande auf den letzten rund 24 px - verdeckt wird
                        # dabei kein Text, nur zwei dunkle Flaechen stossen
                        # aneinander.
FOKUS_RAND = 28
FOKUS_ZEILE = 44


def fokus_punkt(text: str, lage: str = "left") -> tuple[Image.Image, int, int]:
    """Der Stichpunkt, ueber den gerade gesprochen wird: gross in der
    freien Bildhaelfte gegenueber der Themen-Karte. Danach fliegt er in
    die Karte und parkt dort (video_report._lage).

    Zurueck kommen Bild und die Textecke im 1280x720-Raster, damit der
    Renderer das Flugziel aus der Kartenposition ableiten kann - bewegt
    wird das zugeschnittene Overlay, dessen Ecke nicht die Textecke ist.

    Der Kasten ist mitgezeichnet: die Karte sitzt auf rohem Board-Motiv,
    und heller Text ohne Grund darunter ist genau der Lesbarkeitsfehler,
    den das Layout sonst vermeidet."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    x = MARGIN if lage == "right" else B - MARGIN - FOKUS_BREITE
    f = folien._font(True, 34)
    zeilen = folien._umbrechen(d, text.upper(), f,
                               FOKUS_BREITE - 2 * FOKUS_RAND)[:3]
    h = 24 + len(zeilen) * FOKUS_ZEILE + 24
    oben = FOKUS_MITTE - h // 2
    d.rounded_rectangle([x, oben, x + FOKUS_BREITE, oben + h],
                        radius=14, fill=(0, 0, 0, KARTE_ALPHA))
    d.rectangle([x, oben + 14, x + 6, oben + h - 14], fill=AKZENT)
    for i, z in enumerate(zeilen):
        d.text((x + FOKUS_RAND, oben + 24 + i * FOKUS_ZEILE), z, font=f,
               fill=HELL, stroke_width=2, stroke_fill=(0, 0, 0))
    return bild, x + FOKUS_RAND, oben + 24


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


def speichern(bild: Image.Image, ziel: Path) -> tuple[Path, int, int]:
    """Overlay ablegen, zugeschnitten auf seine sichtbaren Pixel.

    Zurueck kommen Pfad und die linke obere Ecke im 1280x720-Raster, damit
    ffmpeg das Bild wieder an seinen Platz legt (overlay=x:y). Der Zuschnitt
    hat zwei Gruende: ffmpeg blendet dann nur die Kartenflaeche statt eines
    Vollbilds (gemessen 9.8 s statt 15.9 s pro 30 s Video), und bewegen laesst
    sich ueberhaupt nur ein zugeschnittenes Overlay - ein vollflaechiges PNG
    steht immer schon ueberall. Vollflaechige Overlays wie die Vignette
    liefert getbbox() unveraendert zurueck, die bleiben also bei 0/0."""
    kasten = bild.getbbox()
    if kasten is None:      # ganz leeres Overlay: unveraendert ablegen
        x, y = 0, 0
    else:
        x, y = kasten[0], kasten[1]
        bild = bild.crop(kasten)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel, "PNG")
    return ziel, x, y
