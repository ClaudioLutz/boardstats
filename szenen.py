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

import design_tokens
import folien
import icons
import thumbnail

B = thumbnail.BREITE
H = thumbnail.HOEHE
AKZENT = thumbnail.AKZENT
HELL = thumbnail.TEXT_HELL
GRAU = thumbnail.TEXT_GRAU
GEDIMMT = design_tokens.NEUTRAL[4]
MARGIN = 64

# Serientitel im Bild (C5, 22.08.2026): "BIZ-NEWS" statt "4CHAN /biz/ ·
# BOARD REPORT". Die Slash-Schreibweise ist die 4chan-Board-Notation und
# liest sich als Herkunftsstempel; "NEWS" traegt den Genre-Entscheid
# (Datenjournalismus + Nachrichtenoptik) im Namen. Als 9 statt 30 Zeichen
# wirkt der Bug wie ein Sendermarker statt wie eine Beschriftung. In der
# Zitat-Post-Karte bleibt "/biz/" stehen - dort ist es die Herkunftsangabe
# eines echten Board-Posts, kein Serientitel.
BUG_TEXT = "BIZ-NEWS"

# 4chan blue board (/biz/): Antwort-Karte, Rand, Name, Greentext
_BOARD = design_tokens.KARTEN_THEME["board_post"]
POST_KARTE = _BOARD["bg"]
POST_RAND = _BOARD["rand"]
POST_NAME = _BOARD["name"]
POST_TEXT = _BOARD["text"]
POST_GRUEN = _BOARD["greentext"]


def _leer() -> Image.Image:
    return Image.new("RGBA", (B, H), (0, 0, 0, 0))


def _bande(bild: Image.Image, oben: int, unten: int, alpha: int = 150) -> None:
    """Halbtransparente schwarze Bande ueber die volle Breite - gibt Text auf
    unruhigen Board-Bildern Halt, ohne das Bild ganz zu verdecken."""
    ImageDraw.Draw(bild).rectangle([0, oben, B, unten], fill=(0, 0, 0, alpha))


UHR_GROESSE = 22


def bug(datum: str) -> Image.Image:
    """Ecken-Marke oben: Serienname links, Uhr-Icon + Datum rechts. Liegt
    als eigenes statisches Overlay auf jeder Szene (im Hintergrund wuerde
    sie mitzoomen)."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    d.text((40, 30), BUG_TEXT, font=folien._font(True, 24), fill=AKZENT,
           stroke_width=2, stroke_fill=(0, 0, 0))
    breite = d.textlength(datum, font=folien._font(False, 24))
    uhr = icons.icon("clock", UHR_GROESSE, GRAU)
    x_uhr = int(B - 40 - breite - UHR_GROESSE - 10)
    bild.alpha_composite(uhr, (x_uhr, 28))
    d.text((B - 40 - breite, 30), datum, font=folien._font(False, 24),
           fill=GRAU, stroke_width=2, stroke_fill=(0, 0, 0))
    return bild


def vignette() -> Image.Image:
    """Ein Hauch Abdunkelung oben (Bug-Zone). Der fruehere 320-px-Verlauf
    unten ist mit dem Designsystem vom 19.08.2026 gefallen: jeder Text steht
    auf seinem eigenen hochdeckenden Kasten bzw. seiner Bande, und der
    Verlauf dunkelte nur noch das Board-Motiv ab, ohne etwas zu tragen."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
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


# Randspalte (Designsystem 19.08.2026): Themen-Titel und geparkte Punkte
# bilden EINEN Kasten, der buendig an der Bildkante sitzt (nur die
# bildinneren Ecken sind gerundet). Der Titel steht oben im Kasten, darunter
# trennt eine Linie die Stichpunktliste ab. Gerendert wird die Spalte
# trotzdem als zwei Overlays - Titel-Teil (steht ab Segmentbeginn) und
# Voll-Spalte je Kartenstand -, die sich zeitlich abloesen statt zu stapeln:
# zweimal KARTE_ALPHA uebereinander waere ein sichtbarer Dunkel-Puls.
KARTE_BREITE = 470
KARTE_OBEN = 100        # Oberkante der Randspalte, unter dem Ecken-Bug
KARTE_UNTEN_MAX = 600   # Lower Thirds laufen nie gleichzeitig mit der Karte
KARTE_ALT = design_tokens.NEUTRAL[2]
KARTE_PAD_L = 42        # Einzug an der Bildkante (dort sitzt der Amber-Tab)
KARTE_PAD_R = 30
KARTE_TEXT_X = KARTE_PAD_L + 9 + 14   # Punkt-Text neben dem 9-px-Quadrat
# Textbreite im Kasten: vom Texteinzug bis zum rechten Innenrand.
KARTE_INNEN = KARTE_BREITE - KARTE_TEXT_X - KARTE_PAD_R
KARTE_PUNKT_FONT = 24
KARTE_PUNKT_ZEILE = 31
KARTE_PUNKT_LUECKE = 12
# Deckkraft der Text-Kaesten, deutlich hoeher als die frueheren 160/170: der
# Text liegt auf rohem Board-Motiv, und dessen Feinstruktur (oft Screenshots
# mit Text) frisst Kontrast. Der Kasten traegt die Lesbarkeit deshalb allein -
# das Motiv selbst bleibt unangetastet scharf (Nutzervorgabe 17.08.: der
# Hintergrund sollte nur hinter den Karten ruhig werden, nicht im ganzen Bild).
KARTE_ALPHA = 228
ECKRADIUS = 16
LINIE = design_tokens.NEUTRAL[7]

TITEL_PAD_T = 26        # Luft ueber und (im Titel-Teil) unter dem Titel


def _rail_x(lage: str) -> int:
    """Linke Kante der Randspalte: buendig an der Bildkante ihrer Seite."""
    return B - KARTE_BREITE if lage == "right" else 0


def _rail_ecken(lage: str) -> tuple[bool, bool, bool, bool]:
    """Nur die bildinneren Ecken der Spalte sind gerundet."""
    if lage == "right":
        return (True, False, False, True)
    return (False, True, True, False)


def _titel_zeilen(d: ImageDraw.ImageDraw, titel: str
                  ) -> tuple[list[str], ImageFont.FreeTypeFont, int]:
    """Titelzeilen, Schriftgrad und Zeilenschritt fuer den Spalten-Titel.

    Der Titel lebt jetzt in der 470 px schmalen Randspalte statt auf der
    vollen Bildbreite - zwei Zeilen sind der Normalfall, eine kleinere
    Stufe kauft knappe Faelle zurueck, ab drei Zeilen wird gekappt."""
    breite = KARTE_BREITE - KARTE_PAD_L - 32 - KARTE_PAD_R
    for gr in (28, 25):
        f = folien._font(True, gr)
        zeilen = folien._umbrechen(d, titel.upper(), f, breite)
        if len(zeilen) <= 2:
            return zeilen, f, gr + 6
    return zeilen[:3], f, gr + 6


def titel_unterkante(titel: str) -> int:
    """Unterkante der Randspalte, solange nur der Titel darin steht."""
    zeilen, _, schritt = _titel_zeilen(ImageDraw.Draw(_leer()), titel)
    return KARTE_OBEN + TITEL_PAD_T + len(zeilen) * schritt + TITEL_PAD_T


def _rail_kopf(bild: Image.Image, d: ImageDraw.ImageDraw, x: int,
               zeilen: list[str], f: ImageFont.FreeTypeFont,
               schritt: int) -> None:
    """Kopf der Randspalte: Amber-Tab an der Aussenkante, Lesezeichen-Icon
    und Titelzeilen. Wird von Titel-Teil und Voll-Spalte identisch
    gezeichnet, damit deren Abloesung pixelgleich und unsichtbar ist."""
    tab_x = x if x == 0 else x + KARTE_BREITE - 8
    d.rectangle([tab_x, KARTE_OBEN + TITEL_PAD_T, tab_x + 8,
                 KARTE_OBEN + TITEL_PAD_T + 40], fill=AKZENT)
    # Lesezeichen-Icon statt reinem Balken: derselbe Platz, aber als
    # Kapitelmarker sofort erkennbar statt als reines Farbfeld.
    marker = icons.icon("bookmark", 20, AKZENT)
    bild.alpha_composite(marker, (x + KARTE_PAD_L, KARTE_OBEN + TITEL_PAD_T + 7))
    for i, z in enumerate(zeilen):
        d.text((x + KARTE_PAD_L + 32, KARTE_OBEN + TITEL_PAD_T + i * schritt),
               z, font=f, fill=HELL)


def themen_titel(titel: str, lage: str = "left") -> Image.Image:
    """Der Kopf der Randspalte, solange noch kein Punkt geparkt ist: der
    Kasten endet unter dem Titel. Sobald der erste Kartenstand kommt,
    loest ihn die Voll-Spalte (themen_karte) hart ab - die Titelpixel
    sind identisch, sichtbar ist nur der unten anwachsende Kasten."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    zeilen, f, schritt = _titel_zeilen(d, titel)
    x = _rail_x(lage)
    d.rounded_rectangle([x, KARTE_OBEN, x + KARTE_BREITE,
                         titel_unterkante(titel)],
                        radius=ECKRADIUS, fill=(0, 0, 0, KARTE_ALPHA),
                        corners=_rail_ecken(lage))
    _rail_kopf(bild, d, x, zeilen, f, schritt)
    return bild


def _karte_layout(d: ImageDraw.ImageDraw, titel: str, punkte: list[str],
                  sichtbar: int, lage: str
                  ) -> tuple[int, int, list[list[str]], list[int], int]:
    """Layoutrechnung der Randspalte, getrennt vom Zeichnen.

    Zurueck kommen die linke Kante, die y-Lage der Trennlinie, die
    tatsaechlich angezeigten Punkt-Bloecke, deren y-Positionen und die
    Unterkante des Kastens. Getrennt, weil zwei Aufrufer dieselbe Rechnung
    brauchen: themen_karte zum Zeichnen und karte_punkt_ziel fuer das
    Flugziel der Fokus-Karte. Die Position darf nicht aus dem vorigen Stand
    hochgerechnet werden - greift die Verdraengung, rutscht der juengste
    Punkt nach oben statt eine Zeile nach unten."""
    x = _rail_x(lage)
    tz, _, ts = _titel_zeilen(d, titel)
    trenner_y = KARTE_OBEN + TITEL_PAD_T + len(tz) * ts + 20
    punkte_oben = trenner_y + 2 + 18
    # Inter statt Space Grotesk: geparkte Stichpunkte sind Fliesstext, keine
    # Titel - dieselbe fette Display-Schrift fuer beide war genau die
    # bemaengelte fehlende Typo-Hierarchie (Titel/Stichpunkte unterschieden
    # sich nur in der Groesse).
    pf = folien._font_medium(KARTE_PUNKT_FONT)
    bloecke = [folien._umbrechen(d, p.upper(), pf, KARTE_INNEN)[:2]
               for p in punkte[:max(sichtbar, 0)]]
    # von hinten so viele Punkte aufnehmen wie reinpassen (der juengste zuerst)
    anzeige: list[list[str]] = []
    h = 0
    for zeilen in reversed(bloecke):
        dh = len(zeilen) * KARTE_PUNKT_ZEILE + KARTE_PUNKT_LUECKE
        if anzeige and punkte_oben + h + dh - KARTE_PUNKT_LUECKE + 28 \
                > KARTE_UNTEN_MAX:
            break
        anzeige.insert(0, zeilen)
        h += dh
    y = punkte_oben
    punkt_y: list[int] = []
    for zeilen in anzeige:
        punkt_y.append(y)
        y += len(zeilen) * KARTE_PUNKT_ZEILE + KARTE_PUNKT_LUECKE
    unten = (y - KARTE_PUNKT_LUECKE + 28) if anzeige \
        else titel_unterkante(titel)
    return x, trenner_y, anzeige, punkt_y, unten


def themen_karte(titel: str, punkte: list[str], sichtbar: int,
                 lage: str = "left") -> Image.Image:
    """Die volle Randspalte: Titel, Trennlinie und die persistente Liste der
    bereits geparkten Stichpunkte - sie steht, bis das (Sub-)Thema wechselt.
    Der Punkt, ueber den gerade gesprochen wird, steht nicht hier, sondern
    als fokus_punkt in der freien Bildhaelfte; er landet hier erst, wenn der
    naechste ihn ersetzt. Alle geparkten Punkte sind gleich gedimmt:
    hervorgehoben ist, was in der Mitte steht, und zwei gleichzeitige
    Hervorhebungen wuerden sich widersprechen. Passt der Verlauf nicht mehr
    in die Hoehe, werden die aeltesten Punkte verdraengt. Die Bildseite
    (lage: left/right) bestimmt das Drehbuch."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    x, trenner_y, anzeige, punkt_y, unten = _karte_layout(
        d, titel, punkte, sichtbar, lage)
    if not anzeige:
        return bild
    d.rounded_rectangle([x, KARTE_OBEN, x + KARTE_BREITE, unten],
                        radius=ECKRADIUS, fill=(0, 0, 0, KARTE_ALPHA),
                        corners=_rail_ecken(lage))
    zeilen_t, f_t, schritt_t = _titel_zeilen(d, titel)
    _rail_kopf(bild, d, x, zeilen_t, f_t, schritt_t)
    d.rectangle([x + KARTE_PAD_L, trenner_y,
                 x + KARTE_BREITE - KARTE_PAD_R, trenner_y + 2], fill=LINIE)
    pf = folien._font_medium(KARTE_PUNKT_FONT)
    for zeilen, py in zip(anzeige, punkt_y):
        d.rectangle([x + KARTE_PAD_L, py + 11, x + KARTE_PAD_L + 9, py + 20],
                    fill=GEDIMMT)
        for j, z in enumerate(zeilen):
            d.text((x + KARTE_TEXT_X, py + j * KARTE_PUNKT_ZEILE), z,
                   font=pf, fill=KARTE_ALT)
    return bild


def karte_punkt_ziel(titel: str, punkte: list[str], sichtbar: int,
                     lage: str = "left") -> tuple[int, int] | None:
    """Wo der Text des juengsten Punkts im Kartenstand `sichtbar` steht -
    das Flugziel der Fokus-Karte. Gerechnet wird mit genau dem Stand, der
    nach der Landung geschnitten wird."""
    x, _, anzeige, punkt_y, _ = _karte_layout(
        ImageDraw.Draw(_leer()), titel, punkte, sichtbar, lage)
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
                              folien._font_medium(KARTE_PUNKT_FONT),
                              KARTE_INNEN)[:2]
    return " ".join(zeilen)


def karte_passt(text: str) -> bool:
    """Ob der Stichpunkt ungekappt in die zwei Kartenzeilen passt.

    Das echte Budget eines Stichpunkts ist diese Kapazitaet, nicht eine
    Zeichenzahl: wer laenger kappt, verliert den Rest spaeter beim Parken;
    wer nach Zeichen kappt, wirft bei schmalen Woertern Platz weg."""
    return text.strip() != "" and len(folien._umbrechen(
        ImageDraw.Draw(_leer()), text.upper(),
        folien._font_medium(KARTE_PUNKT_FONT), KARTE_INNEN)) <= 2


FOKUS_BREITE = 650
FOKUS_MITTE = 318       # vertikale Mitte des Kastens: hoch genug, dass ein
                        # ein- oder zweizeiliger Kapitel-Opener darunter Platz
                        # hat (dessen Bande beginnt bei y=426), tief genug,
                        # dass die Bildmitte belebt wird und nicht der
                        # Kopfbereich. Bei einem dreizeiligen Opener (Bande ab
                        # y=362) beruehrt eine zweizeilige Fokus-Karte die
                        # Bande auf den letzten rund 24 px - verdeckt wird
                        # dabei kein Text, nur zwei dunkle Flaechen stossen
                        # aneinander.
FOKUS_PAD_L = 42        # Texteinzug (hinter dem 8-px-Amber-Balken)
FOKUS_PAD_R = 36
FOKUS_FONT = 42
FOKUS_ZEILE = 52

# Detail-Fragmente unter dem Fokus-Punkt: die Zwischenstufe zwischen dem
# 34-Zeichen-Bulletpoint und dem gesprochenen Satz. Telegrammstil, gemischte
# Schreibung (drei Zeilen VERSALIEN liest niemand in fuenf Sekunden) und in
# Inter statt der fetten Display-Schrift - der Bulletpoint darueber bleibt
# die Ueberschrift. Sie fliegen nie mit: beim Parken bleibt nur der Punkt.
# Gefuellt sind sie WEISS wie der Bulletpoint, nicht im Grau der geparkten
# Punkte (Nutzerfeedback 19.08.2026: das Grau las sich auf dem hellen
# Board-Motiv als ausgegraut, also als nicht mehr aktuell - dabei ist das
# Fragment gerade das, was in diesem Moment gesprochen wird). Die Hierarchie
# tragen Schriftschnitt, Groesse und Schreibung, nicht die Helligkeit.
#
# Seit dem Designsystem vom 19.08.2026 bilden Fokus-Punkt und Fragmente
# optisch EINEN Kasten: der Detail-Teil schliesst ohne Luecke unten an
# (nur die unteren Ecken gerundet, der Fokus-Teil verliert seine unteren),
# getrennt durch eine kurze Trennlinie statt der frueheren Strich-Marker.
# Zwei Overlays bleiben es trotzdem, weil nur der Fokus-Teil in die
# Randspalte fliegt - die Fragmente sind dann schon ausgeblendet.
DETAIL_MAX = 3          # mehr Fragmente konkurrieren mit dem Board-Motiv
DETAIL_FONT = 24
DETAIL_ZEILE = 33
DETAIL_ABSTAND = 10     # Luft zwischen zwei Fragmenten
DETAIL_TRENNER = 3      # Hoehe der kurzen Trennlinie unter dem Fokus-Titel
DETAIL_OBEN = 16        # Luft Trennlinie -> erstes Fragment
DETAIL_UNTEN = 30

# Untere Grenze des Stapels aus Fokus-Kasten und Detail-Kasten. Grosszuegig,
# weil waehrend der Fokus-Karte kein Lower Third laeuft: Zwischenthema, Zitat
# und Kennzahl bekommen eigene Szenen ohne Fokus-Karte, und den Kapitel-Opener
# haelt video_report.py von den Fragmenten frei (dort steht der Punkt allein,
# also zentriert wie bisher). Bleibt die Vignette, gegen die der Kasten mit
# KARTE_ALPHA ohnehin selbst antritt.
STAPEL_UNTEN_MAX = 580
STAPEL_OBEN_MIN = 112   # unter dem Ecken-Bug, falls kein Titel darueber steht


def _detail_bloecke(d: ImageDraw.ImageDraw, fragmente: list[str]
                    ) -> tuple[list[list[str]], ImageFont.FreeTypeFont]:
    f = folien._font_medium(DETAIL_FONT)
    breite = FOKUS_BREITE - FOKUS_PAD_L - FOKUS_PAD_R
    return ([folien._umbrechen(d, s.strip(), f, breite)[:2]
             for s in (fragmente or [])[:DETAIL_MAX] if s.strip()], f)


def _detail_hoehe(bloecke: list[list[str]]) -> int:
    return (DETAIL_TRENNER + DETAIL_OBEN
            + sum(len(b) * DETAIL_ZEILE for b in bloecke)
            + DETAIL_ABSTAND * (len(bloecke) - 1)
            + DETAIL_UNTEN) if bloecke else 0


def _stapel(d: ImageDraw.ImageDraw, text: str, detail: list[str] | None,
            lage: str, oben_min: int = STAPEL_OBEN_MIN) -> tuple:
    """Geometrie von Fokus-Kasten und Detail-Kasten in einem Zug.

    Beide Kaesten sind eigene Overlays (der Fokus-Punkt fliegt, das Detail
    nicht), sitzen aber ohne Luecke uebereinander und wirken als ein
    Kasten - also rechnet eine Funktion fuer beide, und beide Aufrufer
    muessen dieselben Argumente reichen.

    Ohne Detail bleibt die Lage des Fokus-Kastens exakt die alte (zentriert
    auf FOKUS_MITTE). Mit Detail wandert der Stapel so weit nach oben, wie
    er Hoehe braucht - aber nie ueber `oben_min`. Passt er dann immer noch
    nicht, fallen Fragmente von hinten weg, statt ueberzulaufen."""
    x = MARGIN if lage == "right" else B - MARGIN - FOKUS_BREITE
    ff = folien._font(True, FOKUS_FONT)
    zeilen = folien._umbrechen(d, text.upper(), ff,
                               FOKUS_BREITE - FOKUS_PAD_L - FOKUS_PAD_R)[:3]
    bloecke, df = _detail_bloecke(d, detail or [])

    def h_fokus(mit_detail: bool) -> int:
        # Mit Detail-Teil endet der Fokus-Teil 22 px unter dem Titel (dort
        # uebernimmt die Trennlinie), allein traegt er 30 px Fussluft.
        return 32 + len(zeilen) * FOKUS_ZEILE + (22 if mit_detail else 30)

    while bloecke and (oben_min + h_fokus(True) + _detail_hoehe(bloecke)
                       > STAPEL_UNTEN_MAX):
        bloecke.pop()
    h_f = h_fokus(bool(bloecke))
    h_d = _detail_hoehe(bloecke)
    gesamt = h_f + h_d
    oben = FOKUS_MITTE - gesamt // 2
    if h_d:
        oben = max(oben_min, min(oben, STAPEL_UNTEN_MAX - gesamt))
    return x, oben, zeilen, ff, h_f, bloecke, df, h_d


def fokus_punkt(text: str, lage: str = "left",
                detail: list[str] | None = None,
                oben_min: int = STAPEL_OBEN_MIN
                ) -> tuple[Image.Image, int, int]:
    """Der Stichpunkt, ueber den gerade gesprochen wird: gross in der
    freien Bildhaelfte gegenueber der Themen-Karte. Danach fliegt er in
    die Karte und parkt dort (video_report._lage).

    Zurueck kommen Bild und die Textecke im 1280x720-Raster, damit der
    Renderer das Flugziel aus der Kartenposition ableiten kann - bewegt
    wird das zugeschnittene Overlay, dessen Ecke nicht die Textecke ist.

    Der Kasten ist mitgezeichnet: die Karte sitzt auf rohem Board-Motiv,
    und heller Text ohne Grund darunter ist genau der Lesbarkeitsfehler,
    den das Layout sonst vermeidet.

    `detail` steht nicht in diesem Bild - es verschiebt nur die Lage, damit
    der Detail-Kasten darunter Platz hat (siehe detail_karte)."""
    bild = _leer()
    d = ImageDraw.Draw(bild)
    x, oben, zeilen, f, h, bloecke, _, _ = _stapel(d, text, detail, lage,
                                                   oben_min)
    # Mit Detail-Teil ist dieser Kasten nur die obere Haelfte des optischen
    # Ein-Kasten-Stapels: die unteren Ecken bleiben eckig, der Detail-Teil
    # schliesst buendig an und rundet unten ab.
    ecken = (True, True, False, False) if bloecke else (True,) * 4
    d.rounded_rectangle([x, oben, x + FOKUS_BREITE, oben + h],
                        radius=ECKRADIUS, fill=(0, 0, 0, KARTE_ALPHA),
                        corners=ecken)
    d.rectangle([x, oben + 26, x + 8,
                 oben + h - (0 if bloecke else 26)], fill=AKZENT)
    for i, z in enumerate(zeilen):
        d.text((x + FOKUS_PAD_L, oben + 32 + i * FOKUS_ZEILE), z, font=f,
               fill=HELL, stroke_width=2, stroke_fill=(0, 0, 0))
    return bild, x + FOKUS_PAD_L, oben + 32


def detail_teile(text: str, detail: list[str], lage: str = "left",
                 oben_min: int = STAPEL_OBEN_MIN
                 ) -> tuple[list[Image.Image], list[Image.Image]] | None:
    """Der Detail-Kasten in Aufbaustufen: je Fragment ein Kasten und die
    Zeile, die dann hinzukommt.

    Die Fragmente erscheinen nicht gemeinsam, sondern jedes dann, wenn sein
    Inhalt gesprochen wird (video_report._detail_zeiten). Der Kasten waechst
    dabei mit: ein Kasten in Endhoehe stuende zwei Drittel leer da und laese
    sich als Darstellungsfehler (Render-Probe 19.08.2026). Die Stufen loesen
    einander hart ab statt ineinander zu blenden - zwei Kaesten uebereinander
    ergaeben zweimal KARTE_ALPHA, einen sichtbaren Dunkel-Puls. Der Sprung
    ist nur die Unterkante; die neue Textzeile blendet weich auf.

    Nach OBEN waechst der Kasten nie: seine Oberkante und der Fokus-Punkt
    darueber stehen fest, deshalb rechnet die Geometrie IMMER mit der vollen
    Fragmentliste - auch fuer die Kappung in _stapel. None, wenn nichts zu
    zeigen ist."""
    mass = ImageDraw.Draw(_leer())
    x, oben, _, _, h_f, bloecke, f, _ = _stapel(mass, text, detail, lage,
                                                oben_min)
    if not bloecke:
        return None
    d_oben = oben + h_f
    kaesten: list[Image.Image] = []
    zeilen_bilder: list[Image.Image] = []
    y = d_oben + DETAIL_TRENNER + DETAIL_OBEN
    for i, zeilen in enumerate(bloecke):
        kasten = _leer()
        dk = ImageDraw.Draw(kasten)
        k_unten = d_oben + _detail_hoehe(bloecke[:i + 1])
        # Untere Haelfte des Ein-Kasten-Stapels: oben eckig (dort schliesst
        # der Fokus-Teil an), unten gerundet. Amber-Balken und Trennlinie
        # gehoeren zum Kasten, nicht zu den Zeilen - sie stehen ab dem
        # ersten Fragment. PIL zeichnet die Endkoordinate inklusiv, der
        # Fokus-Teil endet also AUF d_oben - eine Zeile tiefer beginnen,
        # sonst verdoppelt die Naht ihr Alpha zu einer dunklen Linie.
        dk.rounded_rectangle([x, d_oben + 1, x + FOKUS_BREITE, k_unten],
                             radius=ECKRADIUS, fill=(0, 0, 0, KARTE_ALPHA),
                             corners=(False, False, True, True))
        dk.rectangle([x, d_oben + 1, x + 8, k_unten - 26], fill=AKZENT)
        dk.rectangle([x + FOKUS_PAD_L, d_oben + 1,
                      x + FOKUS_PAD_L + 56, d_oben + DETAIL_TRENNER],
                     fill=LINIE)
        kaesten.append(kasten)
        bild = _leer()
        dz = ImageDraw.Draw(bild)
        for j, z in enumerate(zeilen):
            dz.text((x + FOKUS_PAD_L, y + j * DETAIL_ZEILE), z,
                    font=f, fill=HELL)
        zeilen_bilder.append(bild)
        y += len(zeilen) * DETAIL_ZEILE + DETAIL_ABSTAND
    return kaesten, zeilen_bilder


def detail_karte(text: str, detail: list[str], lage: str = "left",
                 oben_min: int = STAPEL_OBEN_MIN) -> Image.Image | None:
    """Der fertige Detail-Kasten mit allen Fragmenten - das Bild, das am
    Ende der Standzeit steht.

    Im Video wird er aus seinen Teilen aufgebaut (detail_teile); diese
    Funktion setzt die letzte Stufe mit allen Zeilen zusammen und ist damit
    die Vorlage, gegen die sich die Teile pruefen lassen. None, wenn nichts
    zu zeigen ist."""
    teile = detail_teile(text, detail, lage, oben_min)
    if teile is None:
        return None
    kaesten, zeilen_bilder = teile
    bild = kaesten[-1]
    for zeile in zeilen_bilder:
        bild.alpha_composite(zeile)
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


def _zahl_richtung(wert: str) -> str | None:
    """Trend-Icon nur, wenn der Zahlenwert selbst ein Vorzeichen traegt
    ('-15%', '+300%') - das liest ein Vorzeichen ab, das im Text schon
    steht, statt ein Trendurteil ueber eine unbelegte Board-Behauptung zu
    erfinden. Unsignierte Zahlen ('300%') bleiben ohne Icon."""
    m = _ZAHL.search(wert)
    if not m:
        return None
    if m.group(0).startswith("-"):
        return "trending-down"
    if m.start() > 0 and wert[m.start() - 1] == "+":
        return "trending-up"
    return None


def zahl_tafel(wert: str, titel: str, sub: str) -> Image.Image:
    """Bildschirmfuellende Zahl: der grosse Moment fuer die eine Kennzahl.

    Designsystem 19.08.2026: die Zahl darf dramatisch sein - 200 px Mono
    statt 128, dafuer eine hoehere Bande (154-574), die dem Moment die
    ganze Bildmitte gibt. Titel in VERSALIEN darunter, Quellenzeile zuletzt."""
    bild = _leer()
    _bande(bild, 154, 574, alpha=166)
    d = ImageDraw.Draw(bild)
    for gr in (200, 160, 128, 96):
        font = folien._font_mono(gr)
        if d.textlength(wert, font=font) <= B - 2 * MARGIN - 140:
            break
    breite_wert = d.textlength(wert, font=font)
    richtung = _zahl_richtung(wert)
    icon_groesse = int(gr * 0.48)
    icon_luecke = 26 if richtung else 0
    x0 = (B - breite_wert - icon_groesse - icon_luecke) / 2 \
        if richtung else (B - breite_wert) / 2
    wert_oben = 296 - gr // 2
    if richtung:
        farbe_icon = AKZENT if richtung == "trending-up" else GEDIMMT
        ic = icons.icon(richtung, icon_groesse, farbe_icon)
        bild.alpha_composite(
            ic, (int(x0), int(wert_oben + (gr - icon_groesse) / 2)))
        x0 += icon_groesse + icon_luecke
    d.text((x0, wert_oben), wert, font=font, fill=AKZENT, stroke_width=4,
           stroke_fill=(0, 0, 0))
    tf = folien._font(True, 44)
    t = titel.upper()
    d.text(((B - d.textlength(t, font=tf)) / 2, 442), t, font=tf, fill=HELL)
    sf = folien._font(False, 24)
    d.text(((B - d.textlength(sub, font=sf)) / 2, 512), sub, font=sf, fill=GRAU)
    return bild


def zahlen_uebersicht(karten: list[dict]) -> Image.Image:
    """Alle Tageszahlen auf einen Blick, als stille Tafel.

    Gegenstueck zu zahl_tafel(): seit 21.08.2026 werden nur noch
    ZAHLEN_GESPROCHEN der vier TL;DR-Zahlen vorgelesen, weil vier
    gesprochene Zahlensaetze rund 30 s vor der ersten Story kosteten. Im
    BILD sollen trotzdem alle vier stehen - lesen geht schneller als
    hoeren. Deshalb eine Zeilentafel statt vier weiterer Count-up-Momente:
    sie braucht keine eigene Sprechzeit."""
    bild = _leer()
    _bande(bild, 150, 574, alpha=176)
    d = ImageDraw.Draw(bild)
    wf = folien._font_mono(52)
    tf = folien._font(True, 26)
    sf = folien._font(False, 22)
    # Werte-Spalte an der breitesten Zahl ausrichten, damit die Titel eine
    # gemeinsame Kante bekommen - sonst franst die Tafel rechts aus.
    breite = max((d.textlength(str(k.get("wert") or ""), font=wf)
                  for k in karten[:4]), default=0.0)
    for i, k in enumerate(karten[:4]):
        y = 186 + i * 98
        d.text((MARGIN + 24, y), str(k.get("wert") or ""), font=wf,
               fill=AKZENT, stroke_width=3, stroke_fill=(0, 0, 0))
        x = MARGIN + 24 + breite + 40
        d.text((x, y + 6), str(k.get("titel") or "").upper(), font=tf,
               fill=HELL)
        sub = str(k.get("sub") or "")
        if sub:
            d.text((x, y + 44), sub, font=sf, fill=GRAU)
    return bild


def outro_tafel(frage: str = "") -> Image.Image:
    """Abbinder: fast schwarzer Grund (das Motiv scheint nur noch als
    Ahnung durch), Serientitel linksbuendig mit Amber-Linie darunter -
    das ruhige Ende statt einer weiteren zentrierten Tafel.

    `frage` ist die offene Cliffhanger-Frage fuer morgen (seit
    21.08.2026). Sie steht als Letztes im Bild und bleibt bis zum
    Schlussframe stehen - der einzige Grund, den der Zuschauer bekommt,
    morgen wiederzukommen. Ohne Frage bleibt die Tafel wie zuvor."""
    bild = _leer()
    _bande(bild, 0, H, alpha=219)
    d = ImageDraw.Draw(bild)
    d.text((MARGIN, 252), BUG_TEXT, font=folien._font(True, 84),
           fill=HELL)
    d.rectangle([MARGIN, 376, MARGIN + 548, 386], fill=AKZENT)
    if frage:
        # Die Frage nimmt den Platz der Zeile "New every day" ein: zwei
        # Versprechen untereinander verwaessern beide, und die Frage ist
        # das staerkere - sie sagt konkret, was morgen auf dem Spiel steht.
        ff = folien._font(True, 38)
        for i, z in enumerate(folien._umbrechen(d, frage, ff,
                                                B - 2 * MARGIN)[:2]):
            d.text((MARGIN, 420 + i * 46), z, font=ff, fill=AKZENT)
        d.text((MARGIN, 522), "Answered in tomorrow's report",
               font=folien._font(False, 28), fill=GRAU)
    else:
        d.text((MARGIN, 420), "New every day", font=folien._font(False, 34),
               fill=GRAU)
        d.text((MARGIN, 478), "Source threads and chapters in the description",
               font=folien._font(False, 28), fill=design_tokens.NEUTRAL[5])
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
