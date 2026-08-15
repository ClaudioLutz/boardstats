#!/usr/bin/env python3
"""Vertont den taeglichen /biz/-Lagebericht und laedt ihn als YouTube-Video hoch.

Eigenstaendiger vierter Pipeline-Schritt, absichtlich entkoppelt von
run_report.py: liest nur das bereits oeffentlich abgelegte
extrakte/<datum>/bericht.md (Ergebnis von bericht_zu_markdown()) und kann
daher unabhaengig scheitern, ohne den bestehenden, funktionierenden
E-Mail-Versand zu gefaehrden.

v2: der Text scrollt kontinuierlich als Untertitel-Video (.ass, per ffmpeg
libass eingebrannt), das jeweils gesprochene Wort wird farblich
hervorgehoben.

v3: dichtes Fliesstext-Layout statt einzeln durchlaufender Zeilen. Jede
Zeile hat eine feste Position im Gesamtlayout (Master-Y), Absaetze und
Ueberschriften des Berichts bleiben sichtbar (Abstand bzw. eigene
Farbe/Groesse). Die Scroll-Geschwindigkeit jeder Zeile wird aus dem lokalen
Sprechtempo abgeleitet und ueber Nachbarzeilen geglaettet - so bleiben die
Zeilenabstaende auf dem Bildschirm nahezu konstant (~ZEILENHOEHE) und es
sind viele Zeilen gleichzeitig lesbar, waehrend die gerade gesprochene
Zeile um die Leseposition herum steht. Basistext und Wort-Hervorhebung
teilen sich pro Zeile exakt dieselbe lineare Bewegung, dadurch bleibt die
Hervorhebung deckungsgleich.

v4: Darstellung wie der Markdown-Bericht selbst - linksbuendig mit festem
Rand, Fliesstext normalgewichtig, Ueberschriften fett und groesser,
Aufzaehlungen mit haengendem Einzug. Gerendert werden die Quell-Tokens des
Berichts (mit Satzzeichen), nicht die WordBoundary-Texte von edge-tts (die
sind satzzeichenlos); die gesprochenen Woerter liefern nur noch die
Zeitfenster fuer die Hervorhebung.

Seit 14.08.2026 zweisprachig: --sprache en vertont die englische Fassung
(bericht_en.md, von run_report.py per Sonnet rueckuebersetzt) mit englischer
Stimme; Layout und Zuordnung sind sprachunabhaengig. Beide Sprachen laufen
nacheinander im selben Cron (video.sh), Uploads sind oeffentlich.

v5: kein Endlos-Scroll mehr. Der Text erscheint in Happen von hoechstens
drei Zeilen am unteren Bildrand (Formatierung wie bisher: linksbuendig,
Aufzaehlungen mit haengendem Einzug, Wort-Hervorhebung per Alpha-Maske),
##-Ueberschriften stehen waehrend ihrer Sprechzeit als grosse Titelkarte
weiter oben. Dahinter laufen als Hintergrund die Bild-Anhaenge der gerade
besprochenen Threads: der Report-Lauf legt sie gesichtet unter
arbeit/motive/<datum>/ bereit (lockere Pruefung, nur Richtlinienverstoesse
fallen raus), die Zuordnung Abschnitt -> Thread kommt aus den Quell-URLs
unter jedem Berichtsabschnitt. Die Bilder laufen in voller Qualitaet;
lesbar bleibt der Text durch den dunklen Verlauf am unteren Rand (backt
thumbnail.videohintergrund ein) und die halbtransparente Bande hinter den
Titelkarten. Abschnitte ohne eigenes freigegebenes Bild ziehen reihum aus
dem Pool der uebrigen Tagesbilder; erst ein Tag ganz ohne Bilder faellt
auf ein textloses Standbild (rohes Tagesmotiv bzw. Serienbild) zurueck,
und scheitert der ganze Hintergrund-Aufbau, bleibt die bisherige
einfarbige Flaeche - kein Bildproblem darf den Upload verhindern.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import ImageFont

import thumbnail
import youtube_auth

BASE = Path(__file__).parent
EXTRAKTE = BASE / "extrakte"
VIDEO_DIR = BASE / "video"
THUMBNAIL = BASE / "assets" / "thumbnail.jpg"   # Serienbild, wenn der Tag keins hat
MOTIV_DIR = BASE / "arbeit" / "thumbs"          # Board-Bild des Tages (Report-Lauf)
HINTERGRUND_DIR = BASE / "arbeit" / "motive"    # Hintergrundbilder je Thread
THUMB_MAX_ZEICHEN = 20

SPRACHEN: dict[str, dict[str, str]] = {
    "de": {
        "bericht": "bericht.md",
        "marker": "video.json",
        "suffix": "",
        "stimme": "de-DE-KatjaNeural",
        "titel": "/biz/-Lagebericht {datum}",
        "beschreibung": (
            "Automatisierter Lagebericht aus dem 4chan-Board /biz/ (Business & "
            "Finance) vom {datum}. Diskurs-Dokumentation, keine Anlageberatung."
        ),
        "thumb_fuss": "Lagebericht {datum}",
        "quellen": "Quell-Threads (4chan loescht sie nach wenigen Tagen):",
        "kappung": ("[Text hier gekuerzt - YouTube laesst in der Beschreibung "
                    "nur 5000 Zeichen zu.]"),
    },
    "en": {
        "bericht": "bericht_en.md",
        "marker": "video_en.json",
        "suffix": "_en",
        "stimme": "en-US-JennyNeural",
        "titel": "/biz/ Situation Report {datum}",
        "beschreibung": (
            "Automated situation report from the 4chan board /biz/ (Business & "
            "Finance), {datum}. Discourse documentation, not financial advice."
        ),
        "thumb_fuss": "Situation report {datum}",
        "quellen": "Source threads (4chan deletes them after a few days):",
        "kappung": ("[Text truncated here - YouTube allows only 5000 characters "
                    "in the description.]"),
    },
}
FONT_NORMAL_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
FONT_FETT_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

# YouTube-Limit sind 5000 Zeichen; konservativ in UTF-8-Bytes gerechnet,
# damit Umlaute die Schranke nicht heimlich sprengen.
BESCHREIBUNG_MAX_BYTES = 4900
EIGENES_REPO = "github.com/ClaudioLutz"

CANVAS_W = 1280
CANVAS_H = 720
FONTSIZE = 34
ZEILENHOEHE = 44
MARGIN_LINKS = 80          # fester linker Textrand (linksbuendig wie der Bericht)
PUNKT_EINZUG = 40          # haengender Einzug fuer Aufzaehlungstext hinter dem «•»
ZEILENBREITE_MAX = CANVAS_W - 2 * MARGIN_LINKS
UNTERKANTE = CANVAS_H - 64      # Unterkante des Textblocks am unteren Bildrand
CHUNK_ZEILEN = 3                # hoechstens so viele Zeilen stehen gleichzeitig
KARTE_Y = 140                   # Oberkante der Ueberschrift-Titelkarte
KARTE_FONTSIZES = [58, 50, 44]  # Titelkarte: schrumpfen, bis sie passt
KARTE_ZEILEN_MAX = 3
KARTE_ZEILENFAKTOR = 1.22
# Der Hintergrund laeuft oben in voller Qualitaet (abgedunkelt wird nur der
# untere Verlauf fuer die Textzeilen); die Titelkarte bringt ihre Lesbarkeit
# deshalb selbst mit: eine halbtransparente schwarze Bande ueber die volle
# Breite, nur solange die Karte steht.
KARTE_BANDE_RAND = (30, 20)     # Polster oben/unten um den Kartentext
KARTE_BANDE_ALPHA = "&H50&"     # ~69 % deckend
BILD_MIN_DAUER = 8.0            # ein Hintergrundbild steht mindestens so lange
FPS = 25
FARBE_TEXT = "&H00FFFFFF&"
FARBE_AKZENT = "&H0066D1FF&"        # amber (BGR)
HINTERGRUND = "0x1a1a2e"


def font_pfad(kandidaten: list[str]) -> str:
    for f in kandidaten:
        if Path(f).exists():
            return f
    raise SystemExit(f"keiner der Font-Kandidaten gefunden: {kandidaten}")


# libass setzt die ASS-Fontsize VSFilter-kompatibel als Gesamthoehe
# (Ascent+Descent), PIL dagegen als em-Groesse - libass rendert dadurch rund
# 15 Prozent schmaler, als PIL bei gleicher Fontsize misst (DejaVu Sans,
# empirisch 0.82-0.88 je nach Wort). Nur fuer den Zeilenumbruch relevant;
# positioniert wird nichts mehr ueber PIL-Metriken.
LIBASS_BREITEN_FAKTOR = 0.855


def _breite(font: ImageFont.FreeTypeFont, text: str) -> float:
    """Erwartete libass-Renderbreite von text (PIL-Messung, kalibriert)."""
    return font.getlength(text) * LIBASS_BREITEN_FAKTOR


def fonts_laden() -> dict[str, ImageFont.FreeTypeFont]:
    # Ueberschriften brauchen keinen Eintrag: sie werden als Titelkarte mit
    # eigener, passend geschrumpfter Schrift umbrochen (karte_umbrechen).
    fliesstext = ImageFont.truetype(font_pfad(FONT_NORMAL_KANDIDATEN), FONTSIZE)
    return {"absatz": fliesstext, "punkt": fliesstext}


# ----------------------------------------------------------- Text-Bereinigung

_URL_ZEILE = re.compile(r"^(?:https?://\S+(?:\s+(?:und|and)\s+)?)+$")
_QUELLEN_ZEILE = re.compile(r"^(Quelle|Quellen|Belege|Source|Sources|Evidence):",
                            re.IGNORECASE)
# Kursive Kopfzeile unter dem Titel; "*Data as of:" ist das im
# Uebersetzungs-Prompt (run_report.py) festgelegte englische Gegenstueck.
_DATENSTAND_PREFIXE = ("*Datenstand:", "*Data as of:")


_THREAD_URL = re.compile(r"boards\.4chan\.org/biz/thread/(\d+)")


@dataclass
class Block:
    art: str  # "absatz", "ueberschrift" oder "punkt" (Aufzaehlung)
    text: str
    abschnitt: int = 0  # Index in der Abschnittsliste (je ##-Ueberschrift einer)


@dataclass
class Abschnitt:
    threads: list[str]  # Thread-IDs aus den Quell-URLs unter dem Abschnitt


def abschnitte_erzeugen(markdown: str) -> tuple[list[Block], list[Abschnitt]]:
    """Reduziert den veroeffentlichten bericht.md-Text auf das Vorlesbare.

    Markdown-Syntax (Titel, Archiv-Link, Trennlinie) kann man nicht hoeren;
    Quell-/Beleg-Zeilen und nackte Thread-URLs sind fuer einen Leser gedacht,
    der klicken kann, nicht fuer einen Zuhoerer. Das GLOSSAR ist zum
    Nachschlagen gedacht, nicht zum Anhoeren, und entfaellt komplett - es
    bleibt oeffentlich im bericht.md sichtbar. Die Blockstruktur (Absatz vs.
    ##-Ueberschrift) bleibt erhalten, damit das Video sie darstellen kann.

    Nebenher entsteht die Abschnittsliste: je ##-Ueberschrift ein Abschnitt,
    dem die Thread-IDs seiner Quell-URLs zugeordnet sind - darueber findet
    der Hintergrund die Bilder der gerade besprochenen Threads."""
    zeilen = markdown.splitlines()
    bloecke: list[Block] = []
    abschnitte = [Abschnitt(threads=[])]  # Index 0: Einleitung vor dem ersten ##
    for i, zeile in enumerate(zeilen):
        z = zeile.strip()
        if i == 0 and z.startswith("# "):
            continue
        if z.startswith("## GLOSSAR"):  # trifft auch das englische "## GLOSSARY"
            break
        for tid in _THREAD_URL.findall(z):
            if tid not in abschnitte[-1].threads:
                abschnitte[-1].threads.append(tid)
        if not z or z == "---":
            continue
        if z.startswith("[") and "](README.md)" in z:
            continue
        if z.startswith(_DATENSTAND_PREFIXE) and z.endswith("*"):
            continue
        if _URL_ZEILE.match(z):
            continue
        if _QUELLEN_ZEILE.match(z):
            continue
        if z.startswith("## "):
            abschnitte.append(Abschnitt(threads=[]))
            bloecke.append(Block("ueberschrift", z[3:], len(abschnitte) - 1))
        elif z.startswith("- "):
            bloecke.append(Block("punkt", z[2:], len(abschnitte) - 1))
        else:
            bloecke.append(Block("absatz", z, len(abschnitte) - 1))
    return bloecke, abschnitte


def bloecke_erzeugen(markdown: str) -> list[Block]:
    return abschnitte_erzeugen(markdown)[0]


def text_fuer_tts(markdown: str) -> str:
    return "\n\n".join(b.text for b in bloecke_erzeugen(markdown))


# ----------------------------------------------------------- TTS mit Wort-Zeitstempeln

@dataclass
class Wort:
    text: str
    start: float
    end: float


def tts_mit_worten(text: str, ziel_mp3: Path,
                   stimme: str = SPRACHEN["de"]["stimme"]) -> list[Wort]:
    """Vertont text und liefert dabei pro gesprochenem Wort Start/Ende (Sekunden).

    Nutzt die edge-tts-Bibliothek direkt (nicht die CLI), weil nur der
    Python-API-Stream WordBoundary-Ereignisse mit Zeitstempeln liefert."""
    import edge_tts

    async def _lauf() -> list[Wort]:
        communicate = edge_tts.Communicate(text, stimme, boundary="WordBoundary")
        worte: list[Wort] = []
        with open(ziel_mp3, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    worte.append(Wort(
                        text=chunk["text"],
                        start=chunk["offset"] / 1e7,
                        end=(chunk["offset"] + chunk["duration"]) / 1e7,
                    ))
        return worte

    return asyncio.run(_lauf())


# ----------------------------------------------------------- Wort-zu-Block-Zuordnung

def worte_zu_bloecken(worte: list[Wort], bloecke: list[Block]) -> list[list[Wort]]:
    """Uebertraegt die WordBoundary-Zeitfenster auf die Quell-Tokens der Bloecke.

    edge-tts liefert nur einen flachen Wortstrom ohne Absatzinformation, und
    die WordBoundary-Texte sind satzzeichenlos ("geworden" statt "geworden.").
    Gerendert werden deshalb die Quell-Tokens des Berichts; die gesprochenen
    Woerter liefern nur die Zeitfenster. Die Zuordnung laeuft ueber einen
    Token-Zeiger durch die Quell-Tokens (Reihenfolge ist bei TTS garantiert);
    Teilstring-Vergleich in beide Richtungen faengt Satzzeichen-Differenzen
    ab, kleiner Lookahead faengt einzelne Tokenisierungs-Abweichungen ab.
    Nicht zuordenbare gesprochene Woerter verlaengern das Fenster des zuletzt
    getroffenen Tokens; nie getroffene Tokens (z. B. von TTS zusammengezogen
    oder verschluckt) bekommen das Fenster zwischen ihren Nachbarn."""
    tokens: list[tuple[str, int]] = []
    for bi, block in enumerate(bloecke):
        for tok in block.text.split():
            tokens.append((tok, bi))

    zeiten: list[list[tuple[float, float]]] = [[] for _ in tokens]
    ti = 0
    zuletzt = 0
    for wort in worte:
        wt = wort.text.strip()
        if not wt:
            continue
        for k in range(ti, min(ti + 4, len(tokens))):
            tok, _ = tokens[k]
            if wt in tok or tok in wt:
                zuletzt = k
                ti = k + 1
                break
        else:
            k = zuletzt
        zeiten[k].append((wort.start, wort.end))

    # naechstbekannte Startzeit je Position (fuer Tokens ohne eigenes Fenster)
    naechster_start = [0.0] * len(tokens)
    ns = worte[-1].end if worte else 0.0
    for k in range(len(tokens) - 1, -1, -1):
        if zeiten[k]:
            ns = min(t for t, _ in zeiten[k])
        naechster_start[k] = ns

    ergebnis: list[list[Wort]] = [[] for _ in bloecke]
    letzte_end = 0.0
    for k, (tok, bi) in enumerate(tokens):
        if zeiten[k]:
            start = min(t for t, _ in zeiten[k])
            end = max(t for _, t in zeiten[k])
        else:
            start = letzte_end
            end = max(letzte_end, naechster_start[k])
        letzte_end = end
        ergebnis[bi].append(Wort(tok, start, end))
    return ergebnis


# ----------------------------------------------------------- Zeilenumbruch

@dataclass
class Zeile:
    worte: list[Wort]
    art: str = "absatz"
    blockanfang: bool = False

    @property
    def start(self) -> float:
        return self.worte[0].start

    @property
    def end(self) -> float:
        return self.worte[-1].end

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.worte)


def in_zeilen_umbrechen(worte: list[Wort], font: ImageFont.FreeTypeFont,
                        art: str = "absatz") -> list[Zeile]:
    max_breite = ZEILENBREITE_MAX - (PUNKT_EINZUG if art == "punkt" else 0)
    zeilen: list[Zeile] = []
    aktuell: list[Wort] = []
    for wort in worte:
        kandidat = aktuell + [wort]
        breite = _breite(font, " ".join(w.text for w in kandidat))
        if aktuell and breite > max_breite:
            zeilen.append(Zeile(aktuell, art=art))
            aktuell = [wort]
        else:
            aktuell = kandidat
    if aktuell:
        zeilen.append(Zeile(aktuell, art=art))
    if zeilen:
        zeilen[0].blockanfang = True
    return zeilen


# ----------------------------------------------------------- .ass-Untertitel

_ASS_SPECIAL = re.compile(r"([{}\\])")


def _ass_escape(text: str) -> str:
    return _ASS_SPECIAL.sub(r"\\\1", text)


def _ass_zeit(sekunden: float) -> str:
    cs = round(max(0.0, sekunden) * 100)
    h, rest = divmod(cs, 360000)
    m, rest = divmod(rest, 6000)
    s, cs = divmod(rest, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {CANVAS_W}
PlayResY: {CANVAS_H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Report,DejaVu Sans,{FONTSIZE},{FARBE_TEXT},{FARBE_TEXT},&H00000000&,&H00000000&,0,0,0,0,100,100,0,0,1,2,0,7,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


@dataclass
class Anzeige:
    """Ein Stueck Bildschirm-Text: entweder die Titelkarte einer
    ##-Ueberschrift (gross, weiter oben) oder ein Happen von hoechstens
    CHUNK_ZEILEN Fliesstext-Zeilen am unteren Bildrand. Zu jedem Zeitpunkt
    ist genau eine Anzeige sichtbar; ihr Fenster laeuft vom Start ihres
    ersten gesprochenen Worts bis zum Start der naechsten Anzeige."""
    zeilen: list[Zeile]
    art: str            # "karte" oder "text"
    fontsize: int = 0   # nur fuer Karten (geschrumpft, bis der Text passt)
    start: float = 0.0
    end: float = 0.0


def karte_umbrechen(worte: list[Wort]) -> tuple[list[Zeile], int]:
    """Ueberschrift als Titelkarte umbrechen: groesste Schrift aus
    KARTE_FONTSIZES, mit der der Text in KARTE_ZEILEN_MAX Zeilen passt."""
    pfad = font_pfad(FONT_FETT_KANDIDATEN)
    zeilen: list[Zeile] = []
    for fs in KARTE_FONTSIZES:
        font = ImageFont.truetype(pfad, fs)
        zeilen = in_zeilen_umbrechen(worte, font, "ueberschrift")
        if len(zeilen) <= KARTE_ZEILEN_MAX:
            return zeilen, fs
    return zeilen, KARTE_FONTSIZES[-1]


def anzeigen_bauen(bloecke: list[Block], block_worte: list[list[Wort]],
                   fonts: dict[str, ImageFont.FreeTypeFont]) -> list[Anzeige]:
    """Bloecke in die Anzeigefolge uebersetzen und die Fenster setzen.

    Text-Happen schneiden nie ueber Blockgrenzen: ein Absatz oder
    Aufzaehlungspunkt gehoert zusammen, auch wenn dadurch mal eine einzelne
    Zeile allein steht."""
    anzeigen: list[Anzeige] = []
    for block, worte in zip(bloecke, block_worte):
        if not worte:
            continue
        if block.art == "ueberschrift":
            zeilen, fs = karte_umbrechen(worte)
            anzeigen.append(Anzeige(zeilen, "karte", fs))
        else:
            zeilen = in_zeilen_umbrechen(worte, fonts[block.art], block.art)
            for i in range(0, len(zeilen), CHUNK_ZEILEN):
                anzeigen.append(Anzeige(zeilen[i:i + CHUNK_ZEILEN], "text"))
    for i, a in enumerate(anzeigen):
        a.start = 0.0 if i == 0 else a.zeilen[0].start
        if i > 0:
            anzeigen[i - 1].end = a.start
    if anzeigen:
        anzeigen[-1].end = anzeigen[-1].zeilen[-1].end + 2.0
    return anzeigen


def ass_erzeugen(anzeigen: list[Anzeige], ziel_ass: Path) -> None:
    """Baut das Untertitel-Skript aus der Anzeigefolge.

    Jede Zeile wird als EIN zusammenhaengender String gerendert (libass
    setzt die Wortabstaende selbst, natuerlicher Textsatz); die
    Wort-Hervorhebung ist derselbe Zeilenstring noch einmal, bei dem alle
    Woerter ausser dem gerade gesprochenen per \\alpha unsichtbar sind -
    identischer Glyphenlauf, also pixelgenau deckungsgleich. Woerter einzeln
    per PIL-Metriken zu positionieren funktioniert dagegen nicht
    zuverlaessig: PIL und libass/HarfBuzz messen pro Wort um +-2 Prozent
    unterschiedlich, was klebende oder klaffende Luecken erzeugt."""
    events: list[str] = []
    for a in anzeigen:
        if a.end - a.start < 1e-3:
            continue
        if a.art == "karte":
            stil = f"\\fs{a.fontsize}\\b1"
            schritt = int(a.fontsize * KARTE_ZEILENFAKTOR)
            y0 = KARTE_Y
            # Bande zuerst anhaengen: gleicher Layer, aber libass zeichnet
            # bei gleichem Layer in Dateireihenfolge - Text liegt darueber.
            oben = KARTE_Y - KARTE_BANDE_RAND[0]
            unten = KARTE_Y + len(a.zeilen) * schritt + KARTE_BANDE_RAND[1]
            events.append(
                f"Dialogue: 0,{_ass_zeit(a.start)},{_ass_zeit(a.end)},"
                f"Report,,0,0,0,,{{\\pos(0,0)\\p1\\bord0\\shad0\\blur6"
                f"\\1c&H000000&\\1a{KARTE_BANDE_ALPHA}}}"
                f"m 0 {oben} l {CANVAS_W} {oben} {CANVAS_W} {unten} 0 {unten}")
        else:
            stil = ""
            schritt = ZEILENHOEHE
            y0 = UNTERKANTE - len(a.zeilen) * ZEILENHOEHE
        for k, zeile in enumerate(a.zeilen):
            y = y0 + k * schritt
            links_x = MARGIN_LINKS + (PUNKT_EINZUG if zeile.art == "punkt" else 0)
            if zeile.art == "punkt" and zeile.blockanfang:
                # haengendes Aufzaehlungszeichen am linken Rand, Text eingezogen
                events.append(
                    f"Dialogue: 0,{_ass_zeit(a.start)},{_ass_zeit(a.end)},"
                    f"Report,,0,0,0,,{{\\pos({MARGIN_LINKS},{y})}}•")
            texte = [_ass_escape(w.text) for w in zeile.worte]
            events.append(
                f"Dialogue: 0,{_ass_zeit(a.start)},{_ass_zeit(a.end)},"
                f"Report,,0,0,0,,{{\\pos({links_x},{y}){stil}}}"
                + " ".join(texte))
            for i, wort in enumerate(zeile.worte):
                # ganze Zeile noch einmal, nur das aktive Wort sichtbar (Akzent)
                teile = []
                if i > 0:
                    teile.append("{\\alpha&HFF&}" + " ".join(texte[:i]) + " ")
                teile.append(f"{{\\alpha&H00&\\c{FARBE_AKZENT}}}{texte[i]}")
                if i < len(texte) - 1:
                    teile.append("{\\alpha&HFF&} " + " ".join(texte[i + 1:]))
                w_start = max(a.start, wort.start)
                w_end = max(w_start + 0.01, min(a.end, wort.end))
                events.append(
                    f"Dialogue: 1,{_ass_zeit(w_start)},{_ass_zeit(w_end)},"
                    f"Report,,0,0,0,,{{\\pos({links_x},{y}){stil}}}"
                    + "".join(teile))
    ziel_ass.write_text(ASS_HEADER + "\n".join(events) + "\n", encoding="utf-8")


# ----------------------------------------------------------- Hintergrundbilder

def motiv_zuordnung(datum: str) -> dict[str, list[Path]]:
    """Freigegebene Hintergrundbilder je Thread (Report-Lauf,
    arbeit/motive/<datum>/). Leer, wenn der Tag keine hat."""
    ordner = HINTERGRUND_DIR / datum
    try:
        threads = json.loads((ordner / "motive.json")
                             .read_text(encoding="utf-8"))["threads"]
    except (OSError, json.JSONDecodeError, KeyError):
        return {}
    aus: dict[str, list[Path]] = {}
    for tid, namen in threads.items():
        pfade = [ordner / n for n in namen if (ordner / n).exists()]
        if pfade:
            aus[str(tid)] = pfade
    return aus


def hintergrund_plan(bloecke: list[Block], block_worte: list[list[Wort]],
                     abschnitte: list[Abschnitt], datum: str, ende: float
                     ) -> list[tuple[Path | None, float]]:
    """Bildfolge fuer den Hintergrund: je Berichtsabschnitt die Bilder seiner
    Threads, gleichmaessig auf die Abschnittsdauer verteilt (aber keines
    kuerzer als BILD_MIN_DAUER). Abschnitte ohne eigenes Bild ziehen reihum
    aus dem Pool der uebrigen freigegebenen Tagesbilder (bevorzugt noch
    ungezeigte) - NICHT aus dem Vorschaubild, dessen Tages-Schlagwort passt
    dort inhaltlich nicht. Hat der Tag gar keine freigegebenen Bilder, tut
    es das rohe Tagesmotiv bzw. das statische Serienbild (beide textlos);
    None steht fuer die einfarbige Flaeche."""
    zuordnung = motiv_zuordnung(datum)
    start_von: dict[int, float] = {}
    for block, worte in zip(bloecke, block_worte):
        if worte and block.abschnitt not in start_von:
            start_von[block.abschnitt] = worte[0].start
    grenzen = sorted(start_von.items())  # (abschnitt, startzeit), chronologisch
    # Erster Durchgang: eigene Bilder je Abschnitt; None = braucht den Pool.
    roh: list[tuple[float, list[Path] | None]] = []
    gezeigt: set[Path] = set()
    for i, (nr, start) in enumerate(grenzen):
        von = 0.0 if i == 0 else start
        bis = grenzen[i + 1][1] if i + 1 < len(grenzen) else ende
        dauer = bis - von
        if dauer <= 0:
            continue
        bilder = [p for tid in abschnitte[nr].threads
                  for p in zuordnung.get(tid, [])]
        if bilder:
            bilder = bilder[:max(1, int(dauer // BILD_MIN_DAUER))]
            gezeigt.update(bilder)
        roh.append((dauer, bilder or None))
    motive = sorted(MOTIV_DIR.glob(f"{datum}.*"))
    ersatz = motive[0] if motive else (THUMBNAIL if THUMBNAIL.exists() else None)
    alle: list[Path | None] = [p for pfade in zuordnung.values() for p in pfade]
    pool = [p for p in alle if p not in gezeigt] or alle or [ersatz]
    # Zweiter Durchgang: Abschnitte ohne eigene Bilder reihum aus dem Pool.
    naechster = 0
    plan: list[tuple[Path | None, float]] = []
    for dauer, eigene in roh:
        bilder_aus: list[Path | None]
        if eigene is None:
            n = max(1, min(len(pool), int(dauer // BILD_MIN_DAUER)))
            bilder_aus = [pool[(naechster + k) % len(pool)] for k in range(n)]
            naechster += n
        else:
            bilder_aus = list(eigene)
        plan.extend((b, dauer / len(bilder_aus)) for b in bilder_aus)
    return plan


def hintergrund_liste(plan: list[tuple[Path | None, float]], arbeit: Path,
                      suffix: str) -> Path:
    """Bilder des Plans als Videohintergrund aufbereiten (thumbnail.py) und
    eine ffconcat-Liste mit den Standzeiten schreiben."""
    fertig: dict[Path | None, Path] = {}
    zeilen = ["ffconcat version 1.0"]
    for quelle, dauer in plan:
        if quelle not in fertig:
            fertig[quelle] = thumbnail.videohintergrund(
                quelle, arbeit / f"bg{suffix}_{len(fertig):02d}.jpg")
        pfad = str(fertig[quelle]).replace("\\", "/")
        zeilen += [f"file '{pfad}'", f"duration {dauer:.3f}"]
    # Eigenheit des concat-Demuxers: die letzte duration zaehlt nur, wenn
    # der letzte Eintrag noch einmal als file-Zeile wiederholt wird.
    zeilen.append(zeilen[-2])
    liste = arbeit / f"bg{suffix}.ffconcat"
    liste.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return liste


# ----------------------------------------------------------- Video-Zusammenbau

def video_erzeugen(audio_mp3: Path, ass_datei: Path, ziel_mp4: Path,
                   konkat: Path | None = None) -> None:
    ass_arg = str(ass_datei).replace("\\", "/").replace(":", r"\:")
    if konkat is not None:
        eingabe = ["-f", "concat", "-safe", "0", "-i", str(konkat)]
        vf = f"fps={FPS},ass={ass_arg}"  # Standbilder auf feste Framerate ziehen
    else:
        eingabe = ["-f", "lavfi", "-i",
                   f"color=c={HINTERGRUND}:s={CANVAS_W}x{CANVAS_H}"]
        vf = f"ass={ass_arg}"
    subprocess.run(
        ["ffmpeg", "-y", *eingabe,
         "-i", str(audio_mp3),
         "-vf", vf,
         "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(ziel_mp4)],
        check=True, timeout=1800)


# ----------------------------------------------------------- Orchestrierung

def titel_laden(tag_dir: Path, sprache: str, fallback: str) -> str:
    """Dynamischer, reisserischer Tagestitel aus titel.json (erzeugt vom
    Report-Lauf in run_report.py). Bei jedem Problem der statische
    Serientitel - ein Titelfehler darf den Upload nie verhindern."""
    pfad = tag_dir / "titel.json"
    try:
        wert = json.loads(pfad.read_text(encoding="utf-8")).get(sprache)
    except (OSError, json.JSONDecodeError, AttributeError):
        print(f"kein dynamischer Titel ({pfad}) - nehme Serientitel")
        return fallback
    if not isinstance(wert, str) or not wert.strip():
        print(f"titel.json ohne brauchbaren Eintrag {sprache!r} - nehme Serientitel")
        return fallback
    # "<" und ">" sind in YouTube-Titeln verboten, das API-Limit ist 100
    # Zeichen - defensiv nochmals bereinigen, auch wenn run_report.py das
    # schon getan hat.
    titel = re.sub(r"\s+", " ", wert.replace("<", "").replace(">", "")).strip()
    return titel[:100].rstrip()


def _thumb_aus_titel(titel: str) -> str:
    """Notbehelf, wenn titel.json kein Schlagwort fuers Vorschaubild hat:
    die grossgeschriebenen Woerter des Titels sind dessen Zuspitzung, sonst
    tun es die ersten Woerter."""
    ohne_suffix = titel.split(" | ")[0]
    woerter = [w for w in ohne_suffix.split() if len(w) > 2 and w.isupper()]
    text = " ".join(woerter or ohne_suffix.split())
    text = re.sub(r"\s+", " ", re.sub(r"[^0-9A-Za-zÄÖÜäöü %$&+.-]+", " ", text))
    aus = ""
    for wort in text.strip().upper().split()[:3]:
        if aus and len(f"{aus} {wort}") > THUMB_MAX_ZEICHEN:
            break
        aus = f"{aus} {wort}".strip()
    return aus[:THUMB_MAX_ZEICHEN].strip()


def thumb_text_laden(tag_dir: Path, sprache: str, titel: str) -> str:
    """Schlagwort fuers Vorschaubild aus titel.json (Report-Lauf), sonst aus
    dem Titel abgeleitet."""
    try:
        wert = json.loads((tag_dir / "titel.json").read_text(encoding="utf-8")
                          ).get(f"thumb_{sprache}")
    except (OSError, json.JSONDecodeError, AttributeError):
        wert = None
    if isinstance(wert, str) and wert.strip():
        return wert.strip()[:THUMB_MAX_ZEICHEN].strip().upper()
    return _thumb_aus_titel(titel)


def vorschaubild(arbeit: Path, tag_dir: Path, cfg: dict[str, str], sprache: str,
                 datum: str, titel: str) -> Path | None:
    """Vorschaubild des Tages bauen: fester Serienrahmen mit dem Schlagwort
    des Tages, als Motiv das vom Report-Lauf geprueft ausgewaehlte Board-Bild
    und sonst das statische Serienbild. Scheitert der Aufbau, wird das
    Serienbild unveraendert gesetzt - lieber statisch als gar keins."""
    motive = sorted(MOTIV_DIR.glob(f"{datum}.*"))
    motiv = motive[0] if motive else (THUMBNAIL if THUMBNAIL.exists() else None)
    text = thumb_text_laden(tag_dir, sprache, titel)
    j, m, t = datum.split("-")
    fuss = cfg["thumb_fuss"].format(datum=f"{t}.{m}.{j}" if sprache == "de"
                                    else datum)
    print(f"Vorschaubild: Schlagwort {text!r}, Motiv "
          f"{motiv.name if motiv else 'keins'}")
    try:
        return thumbnail.bauen(text, motiv,
                               arbeit / f"thumbnail{cfg['suffix']}.jpg", fuss=fuss)
    except Exception as e:
        print(f"Vorschaubild nicht gebaut ({e}) - nehme das Serienbild")
        return THUMBNAIL if THUMBNAIL.exists() else None


def thread_links(tag_dir: Path) -> list[str]:
    """Quell-Thread-URLs des Tages aus der Extrakt-Uebersicht (README.md),
    in deren Reihenfolge (absteigend nach Substanzdichte)."""
    try:
        uebersicht = (tag_dir / "README.md").read_text(encoding="utf-8")
    except OSError:
        return []
    ids: list[str] = []
    for tid in re.findall(r"\((\d{4,})\.md\)", uebersicht):
        if tid not in ids:
            ids.append(tid)
    return [f"https://boards.4chan.org/biz/thread/{t}" for t in ids]


def _bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def _fuer_beschreibung(zeile: str) -> str:
    """Eine Berichtszeile als Klartext: Markdown-Auszeichnung und jeder Verweis
    aufs eigene Repo raus, Thread-URLs bleiben stehen."""
    # Das eigene GitHub-Repo wird in der oeffentlichen Beschreibung nicht
    # verlinkt - weder als nackte URL noch als Markdown-Link auf eine Datei
    # darin. Fremde Repos bleiben stehen, sie sind inhaltlicher Beleg.
    zeile = re.sub(rf"https?://\S*{re.escape(EIGENES_REPO)}\S*", "", zeile)
    zeile = re.sub(r"\[[^\]]*\]\([^)]*\.md[^)]*\)", "", zeile)
    zeile = re.sub(r"\[([^\]]*)\]\((https?://[^)]*)\)", r"\1: \2", zeile)
    if set(zeile.strip()) <= {"-", "*", "_"} and len(zeile.strip()) >= 3:
        return ""  # horizontale Trennlinie
    zeile = re.sub(r"^#+\s*", "", zeile)          # Ueberschriften-Marker
    zeile = zeile.replace("**", "")
    if zeile.startswith("*") and zeile.rstrip().endswith("*"):
        zeile = zeile.strip().strip("*")          # kursive Kopfzeile
    # "<" und ">" sind in YouTube-Metadaten verboten (Greentext im Zitat);
    # der lange Gedankenstrich gilt in oeffentlichen Texten als KI-Marker und
    # weicht dem neutralen Bindestrich (Komma waere nicht immer grammatisch).
    zeile = zeile.replace("<", "").replace(">", "").replace("—", "-")
    return re.sub(r"[ \t]+", " ", zeile).rstrip()


def _abschnitte(markdown: str) -> list[str]:
    """Bericht in bereinigte Abschnitte schneiden (je ab einer ##-Ueberschrift),
    damit spaeter an einer Abschnittsgrenze gekappt werden kann."""
    bloecke: list[list[str]] = [[]]
    for roh in markdown.splitlines():
        if roh.startswith("# "):
            continue  # H1 wiederholt nur den Videotitel
        if roh.startswith("## "):
            bloecke.append([])
        zeile = _fuer_beschreibung(roh)
        if zeile or (bloecke[-1] and bloecke[-1][-1]):
            bloecke[-1].append(zeile)
    return [t for t in ("\n".join(b).strip() for b in bloecke) if t]


def _auf_bytes_kappen(text: str, budget: int) -> str:
    if _bytes(text) <= budget:
        return text
    aus: list[str] = []
    rest = budget
    for zeile in text.split("\n"):
        if _bytes(zeile) + 1 > rest:
            break
        aus.append(zeile)
        rest -= _bytes(zeile) + 1
    return "\n".join(aus).rstrip()


def beschreibung_bauen(tag_dir: Path, markdown: str, cfg: dict[str, str],
                       datum: str) -> str:
    """Kopfzeile + Berichtstext im Rohtext + Liste der Quell-Threads. YouTube
    laesst nur 5000 Zeichen zu, der Bericht ist gut doppelt so lang - deshalb
    wird an einer Abschnittsgrenze gekappt. Die Thread-Links bekommen ihr
    Budget vorab, sie duerfen der Kappung nie zum Opfer fallen."""
    kopf = cfg["beschreibung"].format(datum=datum)
    links = thread_links(tag_dir)
    fuss = "\n\n" + cfg["quellen"] + "\n" + "\n".join(links) if links else ""
    hinweis = "\n\n" + cfg["kappung"]
    budget = BESCHREIBUNG_MAX_BYTES - _bytes(kopf) - _bytes(fuss) - _bytes(hinweis)

    abschnitte = _abschnitte(markdown)
    genommen: list[str] = []
    rest = budget
    for abschnitt in abschnitte:
        if _bytes(abschnitt) + 2 > rest:
            break
        genommen.append(abschnitt)
        rest -= _bytes(abschnitt) + 2
    if not genommen and abschnitte:  # nicht mal der erste Abschnitt passt
        genommen = [_auf_bytes_kappen(abschnitte[0], budget)]

    text = kopf + ("\n\n" + "\n\n".join(genommen) if genommen else "")
    if len(genommen) < len(abschnitte):
        text += hinweis
    return text + fuss


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sprache", choices=sorted(SPRACHEN), default="de")
    ap.add_argument("--nur-video", action="store_true",
                    help="Video nur bauen, ohne Upload und ohne Marker (Test)")
    args = ap.parse_args()
    cfg = SPRACHEN[args.sprache]

    datum = date.today().isoformat()
    tag_dir = EXTRAKTE / datum
    bericht_pfad = tag_dir / cfg["bericht"]
    marker_pfad = tag_dir / cfg["marker"]

    if not bericht_pfad.exists():
        print(f"kein Bericht fuer {datum} unter {bericht_pfad} - nichts zu tun")
        return
    if marker_pfad.exists() and not args.nur_video:
        print(f"Video ({args.sprache}) fuer {datum} schon hochgeladen: {marker_pfad}")
        return

    markdown = bericht_pfad.read_text(encoding="utf-8")
    bloecke, abschnitte = abschnitte_erzeugen(markdown)
    text = "\n\n".join(b.text for b in bloecke)

    arbeit = VIDEO_DIR / datum
    arbeit.mkdir(parents=True, exist_ok=True)
    audio_mp3 = arbeit / f"audio{cfg['suffix']}.mp3"
    ass_datei = arbeit / f"untertitel{cfg['suffix']}.ass"
    video_mp4 = arbeit / f"video{cfg['suffix']}.mp4"

    titel = titel_laden(tag_dir, args.sprache, cfg["titel"].format(datum=datum))
    print(f"Titel: {titel}")
    bild = vorschaubild(arbeit, tag_dir, cfg, args.sprache, datum, titel)

    print(f"erzeuge Vertonung ({cfg['stimme']}) mit Wort-Zeitstempeln ...")
    worte = tts_mit_worten(text, audio_mp3, cfg["stimme"])
    print(f"{len(worte)} Woerter erkannt")

    block_worte = worte_zu_bloecken(worte, bloecke)
    anzeigen = anzeigen_bauen(bloecke, block_worte, fonts_laden())
    print(f"{len(anzeigen)} Anzeigen in {len(bloecke)} Bloecken, "
          f"{len(abschnitte)} Abschnitte")
    ass_erzeugen(anzeigen, ass_datei)

    konkat: Path | None = None
    try:
        ende = (worte[-1].end if worte else 0.0) + 5.0  # Puffer, -shortest kappt
        plan = hintergrund_plan(bloecke, block_worte, abschnitte, datum, ende)
        konkat = hintergrund_liste(plan, arbeit, cfg["suffix"])
        print(f"Hintergrund: {len(plan)} Standbilder")
    except Exception as e:
        # Ohne Hintergrund entsteht das Video wie bisher auf der Grundflaeche.
        print(f"Hintergrund nicht aufgebaut ({e}) - nehme die Grundflaeche")

    print("baue Video ...")
    video_erzeugen(audio_mp3, ass_datei, video_mp4, konkat)

    if args.nur_video:
        print(f"nur Video gebaut, kein Upload: {video_mp4}")
        return

    kurz = cfg["beschreibung"].format(datum=datum)
    try:
        beschreibung = beschreibung_bauen(tag_dir, markdown, cfg, datum)
    except Exception as e:
        # Ein Fehler beim Zusammenbau darf den Upload nie verhindern.
        print(f"Beschreibung nicht aufgebaut ({e}) - nehme nur die Kopfzeile")
        beschreibung = kurz
    print("lade auf YouTube hoch ...")
    try:
        video_id, url = youtube_auth.hochladen(video_mp4, titel, beschreibung,
                                               privacy_status="public")
    except RuntimeError as e:
        # Weist YouTube die Metadaten zurueck, scheitert schon das Oeffnen der
        # Upload-Session - dann existiert noch kein Video und ein zweiter
        # Versuch legt kein Duplikat an. Lieber mit kurzer Beschreibung
        # hochladen als den Tag ganz verlieren.
        if beschreibung == kurz or "Upload-Session" not in str(e):
            raise
        print(f"Beschreibung von YouTube abgelehnt ({e}) - zweiter Versuch "
              f"nur mit der Kopfzeile")
        video_id, url = youtube_auth.hochladen(video_mp4, titel, kurz,
                                               privacy_status="public")
    marker_pfad.write_text(json.dumps({"video_id": video_id, "url": url}, indent=2), encoding="utf-8")
    print(f"hochgeladen: {url}")

    # Ein fehlendes Vorschaubild darf den gelungenen Upload nicht entwerten -
    # thumbnails/set braucht zudem einen fuer eigene Thumbnails verifizierten
    # Kanal, sonst antwortet YouTube mit 403.
    if bild is not None:
        try:
            youtube_auth.thumbnail_setzen(video_id, bild)
            print(f"Vorschaubild gesetzt ({bild.name})")
        except (RuntimeError, OSError) as e:
            print(f"Vorschaubild nicht gesetzt: {e}")
    else:
        print(f"kein Vorschaubild gebaut und keins unter {THUMBNAIL}")


if __name__ == "__main__":
    main()
