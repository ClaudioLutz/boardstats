#!/usr/bin/env python3
"""Farbtoken-System fuer thumbnail.py/folien.py/szenen.py (18.08.2026).

Vorher stand jede Verwendungsstelle auf einem isolierten Hex-Tupel
(GRUND, AKZENT, GEDIMMT, KARTE_BG, ...) ohne erkennbaren Zusammenhang -
Kontrastentscheidungen liessen sich nicht an einer Stelle nachvollziehen.
Dieses Modul strukturiert dieselben, bereits bewaehrten Farbwerte als
abgestufte Skalen im Muster von Open Color/Radix Colors (0 = hellste,
9 = dunkelste Stufe einer Familie) - bewusst OHNE die Werte selbst zu
aendern: der Umbau ist pixelgleich, nur die Herkunft jeder Farbe wird
jetzt an einer Stelle benannt statt an zehn.

Dazu ein Karten-Theme-Dict im Stil von github-readme-stats: pro
Kartentyp ein Bund aus Hintergrund-, Titel- und Wertfarbe statt
verstreuter Einzelkonstanten.
"""
from __future__ import annotations

Farbe = tuple[int, int, int]

WEISS: Farbe = (255, 255, 255)

# Neutraler Grundton: dieselbe navy-getoente Skala, die vorher als
# Einzelwerte GRUND/KARTE_BG/LINIE/GEDIMMT/TEXT_GRAU/KARTE_ALT verstreut
# waren. Stufe 9 ist die dunkelste (Basisflaeche), Stufe 1 die hellste
# (fast weisser Text auf Dunkel).
NEUTRAL: dict[int, Farbe] = {
    1: (224, 226, 234),
    2: (198, 203, 216),   # vorher szenen.KARTE_ALT - geparkte Stichpunkte
    3: (170, 175, 190),   # vorher thumbnail.TEXT_GRAU - Nebentext
    4: (150, 155, 172),   # vorher szenen.GEDIMMT - inaktive Elemente
    5: (120, 125, 142),   # vorher folien.GEDIMMT - Outro-Fusszeile
    7: (60, 62, 92),      # vorher folien.LINIE - Trennlinien
    8: (35, 35, 66),      # vorher folien.KARTE_BG - Kartenflaeche
    9: (26, 26, 46),      # vorher thumbnail.GRUND - Basisflaeche
}

# Amber-Akzent, abgestuft wie eine Open-Color-Akzentspalte (2 = hellste,
# 8 = dunkelste Stufe); Stufe 6 ist der bisherige AKZENT-Einzelwert.
AKZENT: dict[int, Farbe] = {
    2: (255, 233, 168),
    4: (255, 218, 130),
    6: (255, 209, 102),   # vorher thumbnail.AKZENT
    8: (214, 158, 46),
}

# 4chan blue board (/biz/): eigene Skala, weil das Motiv (helles Papier)
# gegen den dunklen Rest der Karten steht - als eigener Theme-Eintrag
# unten trotzdem im selben Dict-Muster gefuehrt statt als Sonderfall.
BOARD_POST: Farbe = (214, 218, 240)
BOARD_RAND: Farbe = (183, 197, 217)
BOARD_NAME: Farbe = (17, 119, 67)
BOARD_TEXT: Farbe = (30, 30, 40)
BOARD_GREENTEXT: Farbe = (120, 153, 34)

# Kartentheme-Dict (Muster github-readme-stats): pro Kartentyp ein Bund
# aus Hintergrund-, Rand-, Titel- und Wertfarbe plus Eckenradius/Padding,
# austauschbare Werte statt hart codierter Einzelfarben je Zeichenfunktion.
KARTEN_THEME: dict[str, dict] = {
    "dunkel": {
        "bg": NEUTRAL[8], "rand": AKZENT[6], "titel": WEISS,
        "wert": AKZENT[6], "sub": NEUTRAL[3], "radius": 14, "padding": 36,
    },
    "board_post": {
        "bg": BOARD_POST, "rand": BOARD_RAND, "name": BOARD_NAME,
        "text": BOARD_TEXT, "greentext": BOARD_GREENTEXT,
        "radius": 6, "padding": 30,
    },
}
