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

Seit 16.08.2026 nur noch englisch: die ganze Pipeline (Extrakte, Bericht,
Titel, Folien) entsteht in run_report.py direkt auf Englisch, bericht.md IST
die englische Fassung - eine deutsche existiert nicht mehr. Die SPRACHEN-
Struktur bleibt als ein Eintrag bestehen (Marker video_en.json und Suffix _en
unveraendert, damit Alt-Tage und Doppel-Upload-Schutz weiter stimmen).

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

v6 (16.08.2026): Praesentationsmodus. Liegt extrakte/<datum>/folien.json
(vom Report-Lauf per Sonnet aus dem Bericht verdichtet: je Abschnitt
Folientitel, Stichpunkte mit Anker-Phrasen, optionale Zahlen-Karte, dazu
vier "Numbers of the day"), wird das Video als Folien-Praesentation gebaut:
Intro mit dem Tages-Aufhaenger, Agenda, je Abschnitt beim Kapitelwechsel
das rohe Board-Bild vollflaechig mit der Ueberschrift (Reveal, solange die
Ueberschrift gesprochen wird), dann weiche Ueberblendung zur Themen-Folie,
deren Stichpunkte synchron zur Rede aufleuchten (Zeitpunkt ueber die
Anker-Phrase in den Wort-Zeitstempeln), am Ende Zahlen-Folie und Outro.
Alle Zustaende sind PIL-Standbilder (folien.py), umgeschaltet ueber die
ffconcat-Liste - auf diesem Pfad wird kein ASS-Text mehr eingebrannt, das
Wort-Karaoke entfaellt. Gesprochen wird weiterhin der ganze Berichtstext,
ergaenzt um Rahmen-Saetze (Intro, Agenda-Aufzaehlung, Zahlen, Outro).
Ohne folien.json oder bei jedem Fehler im Folien-Aufbau entsteht das Video
im bisherigen v5-Text-Layout - die Praesentation darf den Upload nie
verhindern.

v7 (16.08.2026, Nutzerwunsch "es sieht zu fest nach PowerPoint aus"):
Szenen-Layout statt Folien. Traegt folien.json die Version 2, ist sie ein
Drehbuch: je Abschnitt Stichpunkt-Momente (moeglichst je Satz einer),
optionale Zwischenthemen, ein Board-Zitat und eine Kennzahl, alles mit
Anker-Phrasen im Berichtstext. Das Video besteht dann aus Szenen mit
vollflaechigem, langsam zoomendem Board-Bild (ffmpeg zoompan, je Szene ein
eigener kleiner ffmpeg-Lauf, am Ende per concat zusammengefuegt); aller
Text liegt als transparente PNG-Overlays (szenen.py) darueber und blendet
zeitgesteuert ein und aus: Kapitel-Opener als Lower Third, der Titel des
laufenden Themas oben, darunter eine persistente Karte mit den geparkten
Stichpunkten (Bildseite bestimmt das Drehbuch), die steht, bis das Thema
oder Zwischenthema wechselt, dazu der Stichpunkt, ueber den gerade
gesprochen wird, gross in der freien Bildhaelfte: er steht dort, bis der
naechste ihn abloest, und fliegt dann in die Karte, wo er als Listeneintrag
parkt (Nutzerwunsch 17.08. abends, "damit haben wir den toten Platz lebendig
gemacht") - keine Sprechsekunde ohne Text im Bild (Nutzeranforderung
17.08.) -, Zitate als 4chan-Post-Karte,
Kennzahlen als Gross-Zahl mit Count-up. Gesprochen wird
unveraendert der ganze Berichtstext samt Rahmen-Saetzen. Scheitert der
Szenen-Aufbau, greift v5; folien.json ohne Version faellt auf die
v6-Folien zurueck - kein Layout-Problem darf den Upload verhindern.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import re
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape as xml_escape

from PIL import ImageFont

import folien
import klip_katalog
import run_report as rr
import szenen
import thumbnail
import youtube_auth

BASE = Path(__file__).parent
EXTRAKTE = BASE / "extrakte"
VIDEO_DIR = BASE / "video"
THUMBNAIL = BASE / "assets" / "thumbnail.jpg"   # Serienbild, wenn der Tag keins hat
MOTIV_DIR = BASE / "arbeit" / "thumbs"          # Board-Bild des Tages (Report-Lauf)
HINTERGRUND_DIR = BASE / "arbeit" / "motive"    # Hintergrundbilder je Thread
THUMB_MAX_ZEICHEN = 20

# Dieser Lauf haengt selbst nicht an 4chan (einziger Netzzugriff ist Google
# TTS), wohl aber am Bericht - und der entsteht auch dann, wenn der Crawl
# seit Tagen nichts Neues holt: dann stehen alle Threads auf "unchanged
# since the last run", und das Video waere ein frisch betitelter Aufguss auf
# altem Datenstand. Der Bericht nennt seinen Datenstand in der Kopfzeile,
# also wird er hier gegen die Uhr geprueft.
#
# 20 Stunden als Grenze: der Bericht um 07:35 nutzt den 07:20-Snapshot (rund
# eine Stunde alt). Faellt nur der Morgencrawl aus, ist es der 20:20 vom
# Vorabend, um 08:10 also knapp 12 Stunden - das soll durchgehen. Faellt
# zusaetzlich der Vorabend aus, bleibt 13:20 vom Vortag mit knapp 19
# Stunden, was gerade noch passiert; ein ganzer ausgefallener Tag (07:20
# vom Vortag, knapp 25 Stunden) blockt.
DATENSTAND_MAX_H = 20.0
ZURICH = ZoneInfo("Europe/Zurich")
DATENSTAND_RE = re.compile(
    r"Data as of:\s*(\d{1,2})\.(\d{1,2})\.(\d{4})[\s,]+(\d{1,2}):(\d{2})", re.I)


def datenstand_alter_h(markdown: str) -> float | None:
    """Alter des Datenstands in Stunden aus der Kopfzeile des Berichts.

    None, wenn die Zeile fehlt oder unlesbar ist: sie wird vom Modell
    geschrieben, und ein Formatwechsel dort darf die Serie nicht anhalten -
    dann laeuft der Tag wie vorher ungeprueft durch (mit Warnung)."""
    m = DATENSTAND_RE.search(markdown)
    if not m:
        return None
    tag, monat, jahr, stunde, minute = (int(g) for g in m.groups())
    try:
        stand = datetime(jahr, monat, tag, stunde, minute, tzinfo=ZURICH)
    except ValueError:
        return None
    return (datetime.now(ZURICH) - stand).total_seconds() / 3600

SPRACHEN: dict[str, dict[str, str]] = {
    "en": {
        "bericht": "bericht.md",
        "marker": "video_en.json",
        "suffix": "_en",
        "stimme": "en-US-AriaNeural",
        # Studio klingt deutlich natuerlicher als Neural2, kennt aber kein
        # <mark> - die Zeitachse baut der Studio-Pfad unten selbst. Scheitert
        # Studio (Quota, Netz), springt die Vertonung auf die Marken-Stimme
        # und erst danach auf edge-tts.
        # Seit 20.08.2026 die weibliche Studio-O statt Studio-Q (Hoervergleich
        # aller en-US-Klassen, research/stimmproben/). Die Ersatzkette zieht
        # mit: gemessene Grundfrequenz 190.5 Hz bei Studio-O, 193.5 Hz bei
        # Neural2-G, 196.7 Hz bei AriaNeural - ein Ausfalltag klingt damit
        # nicht ploetzlich maennlich.
        "google_stimme": "en-US-Studio-O",
        "google_stimme_marken": "en-US-Neural2-G",
        "titel": "/biz/ Situation Report {datum}",
        "beschreibung": (
            "Situation report from the 4chan board /biz/ (Business & "
            "Finance), {datum}. Discourse documentation, not financial advice."
        ),
        "thumb_fuss": "Situation report {datum}",
        "quellen": "Source threads (4chan deletes them after a few days):",
        "kappung": ("[Text truncated here - YouTube allows only 5000 characters "
                    "in the description.]"),
        "kapitel_intro": "Intro",
        # Serien-Playlist des Kanals; jedes hochgeladene Video wird dort
        # angehaengt (playlistItems.insert, deckt der force-ssl-Scope).
        # Kein Geheimnis - die Playlist ist oeffentlich.
        "playlist": "PLE-UMRGn6d6g",
    },
}
# Feste Serien-Tags je Sprache; dazu kommen beim Upload die Tagesthemen
# (##-Ueberschriften und Titel-Schlagwort). Tags wirken bei YouTube nur noch
# schwach, kosten aber nichts.
FESTE_TAGS: dict[str, list[str]] = {
    "en": ["4chan", "biz", "crypto", "bitcoin", "stocks", "stock market",
           "finance", "investing", "market report"],
}
TAGS_MAX_ZEICHEN = 450   # YouTube deckelt die Gesamtliste bei 500 Zeichen
# Die ersten drei Hashtags der Beschreibung zeigt YouTube klickbar ueber
# dem Videotitel.
HASHTAG_ZEILE = "#4chan #biz #crypto"
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
# Das Kompositions-Raster bleibt bei 1280x720 (Fonts/Positionen ueberall im
# Rendering sind darauf abgestimmt); erst beim finalen Mux fuer YouTube wird
# auf 1080p hochskaliert. Gleiches Seitenverhaeltnis (16:9), also reine
# Vergroesserung ohne Crop/Padding.
YOUTUBE_W = 1920
YOUTUBE_H = 1080
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

# Links MITTEN im Fliesstext: die Zeilenfilter oben fangen nur reine
# URL-/Quellen-Zeilen; eingeklammerte oder nackte URLs im Satz wuerden vom
# TTS Buchstabe fuer Buchstabe vorgelesen (Nutzerfeedback 17.08.).
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_INLINE_URL = re.compile(r"\(\s*(?:https?://|www\.)[^)]*\)"
                         r"|(?:https?://|www\.)\S+")


# Das Board flucht, das Video nicht: die f-Wort-Familie wird ueberall ersetzt,
# wo Text ins Video geht - Sprechtext, Bildtext, Fusszeile, Titel, Beschreibung
# und Vorschaubild (Nutzerauftrag 17.08.2026). Der Bericht selbst sollte dank
# der Zitat-Regel im Synthese-Prompt (run_report.py) schon sauber sein; das
# hier ist das Netz darunter, denn ein Prompt garantiert nichts.
#
# Ton und Bild bekommen bewusst DASSELBE Ersatzwort mit derselben Wortzahl:
# worte_zu_bloecken ordnet die TTS-Zeitfenster per Teilstring-Vergleich den
# Quell-Tokens zu, eine im Bild anders zensierte Form (geschriebenes "f***ed"
# gegen gesprochenes "screwed") wuerde diese Zuordnung verschieben.
_ERSATZ = {
    "motherfucker": "jerk", "motherfuckers": "jerks",
    "clusterfuck": "mess", "clusterfucks": "messes",
    "fuckery": "nonsense", "fucker": "idiot", "fuckers": "idiots",
    "fucking": "freaking", "fuckin": "freakin",
    # "fucks" wird zu "effs" ("zero effs given"): das ist die aussprechbare
    # Form des geschriebenen "fs" - als "fs" wuerde die Stimme Buchstaben
    # aufzaehlen (Nutzervorgabe 17.08.2026).
    "fucked": "screwed", "fucks": "effs", "fuck": "hell",
    "cunt": "jerk", "cunts": "jerks",
}
# Laengste Alternative zuerst, sonst nimmt "fuck" den abgeleiteten Formen den
# Treffer weg. "shit" fehlt absichtlich: "shitcoin" ist auf /biz/ ein
# Fachbegriff, und das Wort ist auf YouTube unschaedlich.
_DERB = re.compile(r"\b(" + "|".join(sorted(_ERSATZ, key=len, reverse=True))
                   + r")\b", re.I)


def entschaerft(text: str) -> str:
    """Derbe Woerter durch harmlose gleicher Wortzahl ersetzen.

    Die Schreibweise des Originals bleibt erhalten (FUCKS -> SCREWS,
    Fucking -> Freaking), damit CAPS-Zuspitzungen in Titeln nicht auffallen."""
    def ersetze(m: re.Match[str]) -> str:
        roh = m.group(0)
        neu = _ERSATZ[roh.lower()]
        if roh.isupper() and len(roh) > 1:
            return neu.upper()
        return neu.capitalize() if roh[0].isupper() else neu
    return _DERB.sub(ersetze, text)


def _ohne_links(text: str) -> str:
    """Blocktext ohne Links: Markdown-Links auf ihren Linktext reduziert,
    URLs entfernt, danach Leerraum vor Satzzeichen geglaettet. Hier greift
    auch entschaerft(): jeder gesprochene und im v5-Layout gezeigte Text
    laeuft durch diese Funktion."""
    t = _MD_LINK.sub(r"\1", text)
    t = _INLINE_URL.sub("", t)
    t = re.sub(r"\s{2,}", " ", t)
    return entschaerft(re.sub(r"\s+([.,;:!?])", r"\1", t).strip())


@dataclass
class Block:
    art: str  # "absatz", "ueberschrift" oder "punkt" (Aufzaehlung)
    text: str
    abschnitt: int = 0  # Index in der Abschnittsliste (je ##-Ueberschrift einer)
    # Rolle im Praesentationsmodus ("intro", "agenda_kopf", "agenda", "zahl_kopf",
    # "zahl", "outro"); leer fuer Berichtsbloecke. Die art bleibt immer eine der
    # drei Render-Arten, damit der ASS-Ersatzpfad jeden Block darstellen kann.
    rolle: str = ""


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
    der Hintergrund die Bilder der gerade besprochenen Threads.

    Der Sammelabschnitt "Still true from yesterday" faellt seit 21.08.2026
    ebenfalls weg (rr.ist_still_true). Er stand als letztes Kapitel im
    Video - eine Aufzaehlung von Themen, zu denen es nichts Neues gibt,
    genau dort, wo ohnehin am wenigsten Zuschauer uebrig sind. Im
    bericht.md bleibt er stehen: gelesen ist er nuetzlich, gehoert ist er
    toter Ton."""
    zeilen = markdown.splitlines()
    bloecke: list[Block] = []
    abschnitte = [Abschnitt(threads=[])]  # Index 0: Einleitung vor dem ersten ##
    ueberspringen = False
    for i, zeile in enumerate(zeilen):
        z = zeile.strip()
        if i == 0 and z.startswith("# "):
            continue
        if z.startswith("## GLOSSAR"):  # trifft auch das englische "## GLOSSARY"
            break
        if z.startswith("## "):
            ueberspringen = rr.ist_still_true(z)
            if ueberspringen:
                print(f"Video: Abschnitt {z[3:].strip()!r} nicht vertont "
                      f"(steht weiterhin im Bericht)")
        if ueberspringen:
            continue
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
            t = _ohne_links(z[3:])
            if t:
                bloecke.append(Block("ueberschrift", t, len(abschnitte) - 1))
        elif z.startswith("- "):
            t = _ohne_links(z[2:])
            if t:
                bloecke.append(Block("punkt", t, len(abschnitte) - 1))
        else:
            t = _ohne_links(z)
            if t:
                bloecke.append(Block("absatz", t, len(abschnitte) - 1))
    return bloecke, abschnitte


def bloecke_erzeugen(markdown: str) -> list[Block]:
    return abschnitte_erzeugen(markdown)[0]


def ton_text(bloecke: list[Block]) -> str:
    """Blocktext fuer die Vertonung; der Trenner kodiert die Pausenlaenge.

    Die Zahl der Zeilenumbrueche kodiert die Pausenlaenge (siehe
    _pause_fuer_trenner): vier vor jeder Kapitel-Ueberschrift, drei vor jedem
    Agenda-Eintrag, sonst zwei. Ueber die Blockstruktur laufen nur diese
    Entscheidungen, damit die Blocktexte selbst unberuehrt bleiben:
    worte_zu_bloecken teilt sie wieder per split() auf und darf die Trenner
    nie sehen.

    Die Agenda-Pause kauft Lesezeit genau dort, wo die Standzeit einer Folie
    allein am Sprechtempo haengt: jeder "COMING UP"-Eintrag stand nur 2.1-2.4s
    fuer rund 30 Zeichen (21-23 cps, Pacing-Messung 19.08.2026)."""
    teile: list[str] = []
    for i, b in enumerate(bloecke):
        if i:
            teile.append("\n\n\n\n" if b.art == "ueberschrift"
                         else "\n\n\n" if b.rolle == "agenda" else "\n\n")
        teile.append(b.text)
    return "".join(teile)


def text_fuer_tts(markdown: str) -> str:
    return ton_text(bloecke_erzeugen(markdown))


# ----------------------------------------------------------- TTS mit Wort-Zeitstempeln

@dataclass
class Wort:
    text: str
    start: float
    end: float


def edge_tts_mit_worten(text: str, ziel_mp3: Path, stimme: str) -> list[Wort]:
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


# Google Cloud TTS (Neural2): bessere Stimmen als edge-tts, Wort-Zeitstempel
# ueber SSML-<mark>-Tags (enableTimePointing, nur in v1beta1). Der API-Key
# liegt bewusst ausserhalb des oeffentlichen Repos, analog zu den
# YouTube-Credentials.
GOOGLE_TTS_KEY = Path.home() / ".config" / "boardstats" / "google_tts_key.txt"
GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
GOOGLE_SSML_MAX_BYTES = 4000    # API-Limit 5000 Bytes je Aufruf, Marks zaehlen mit
GOOGLE_SPRECHRATE = 1.15        # schneller wirkt draengender; die <break>-
                                # Pausen sind Festzeiten und skalieren NICHT mit
GOOGLE_ABSATZ_PAUSE = "600ms"   # edge-tts pausierte an Absatzgrenzen von selbst
# Lange Pause vor jeder Kapitel-Ueberschrift (im Studio-Pfad als Stille, im
# Marken-Pfad als SSML-<break>). Sie ist nicht Kosmetik: das
# Szenen-Layout laesst den letzten Stichpunkt eines Themas in die Karte
# fliegen und die vollstaendige Liste danach stehen (LETZT_HALT). Dieser Halt
# braucht Stille in der Tonspur - ohne sie muesste der Punkt mitten im
# letzten gesprochenen Satz wegfliegen. Zweitnutzen: der Themenwechsel mit
# Kreuzblende bekommt Luft, statt auf dem letzten Wort zu passieren.
GOOGLE_KAPITEL_PAUSE = "2500ms"
# Pause nach jedem Agenda-Satz ("Coming up"): die Agenda-Folie steht genau so
# lange wie ihr Ansagesatz gesprochen wird, ihre Lesezeit haengt also allein
# am Sprechtempo. Diese Pause verlaengert sie, ohne den Text zu kuerzen.
GOOGLE_AGENDA_PAUSE = "1200ms"


def _pause_fuer_trenner(trenner: str) -> str:
    """Pausenlaenge aus der Zahl der Zeilenumbrueche im Trenner (ton_text
    setzt sie): vier oder mehr = Kapitelgrenze, drei = Agenda-Eintrag, zwei =
    gewoehnliche Absatzgrenze. Beide Vertonungspfade (Marken und Studio)
    lesen sie hier."""
    if len(trenner) > 3:
        return GOOGLE_KAPITEL_PAUSE
    return GOOGLE_AGENDA_PAUSE if len(trenner) > 2 else GOOGLE_ABSATZ_PAUSE

# Google gewaehrt das Gratiskontingent je Stimmklasse und Kalendermonat
# (Studio 1 Mio. Zeichen, Neural2 und Chirp 3 je 1 Mio., Wavenet/Standard
# 4 Mio.). Ueberschritten wird nicht gesperrt, sondern abgerechnet.
#
# Das Cloud-Budget des Rechnungskontos ("TTS ueber Gratiskontingent", 5 CHF,
# Schwellen 20/50/100 %) kann erst anschlagen, wenn schon Kosten entstanden
# sind - im Gratisbereich sind sie null. Diese Buchhaltung ist die Warnung
# DAVOR: sie kennt nur den eigenen Verbrauch, sieht ihn aber vollstaendig
# und bevor er etwas kostet. Ablage unter arbeit/, also ausserhalb des
# oeffentlichen Repos.
TTS_VERBRAUCH = BASE / "arbeit" / "tts_verbrauch.json"
TTS_FREI_PRO_MONAT = 1_000_000
TTS_WARN_ANTEIL = 0.7     # ab hier warnt der Lauf im Log
TTS_MONATE_BEHALTEN = 6


def _ch(n: int) -> str:
    """Zahl mit Apostroph als Tausendertrenner - nur fuer Log-Ausgaben an
    den Betreiber, das oeffentliche Produkt bleibt bei englischen Kommas."""
    return f"{n:,}".replace(",", "'")


def _stimm_klasse(stimme: str) -> str:
    """Kontingent-Klasse einer Stimme - die Gratismengen gelten je Klasse,
    nicht je Stimme (en-US-Studio-Q und en-US-Studio-O teilen also eine)."""
    for klasse in ("Studio", "Chirp3", "Chirp", "Neural2", "Wavenet",
                   "Polyglot", "News", "Casual"):
        if klasse in stimme:
            return klasse
    return "Standard"


def verbrauch_buchen(stimme: str, zeichen: int) -> None:
    """Abgerechnete Zeichen des Monats fortschreiben und bei Annaeherung an
    das Gratiskontingent warnen.

    Buchhaltung ist Beiwerk: jeder Fehler hier wird gemeldet und
    verschluckt, denn die Vertonung ist zu diesem Zeitpunkt schon bezahlt
    und das Video soll trotzdem entstehen."""
    klasse = _stimm_klasse(stimme)
    monat = date.today().strftime("%Y-%m")
    try:
        try:
            daten = json.loads(TTS_VERBRAUCH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            daten = {}
        if not isinstance(daten, dict):
            daten = {}
        stand = daten.setdefault(monat, {})
        stand[klasse] = int(stand.get(klasse, 0)) + zeichen
        # Nur die letzten Monate behalten - aeltere sind abgerechnet und
        # interessieren niemanden mehr.
        daten = {m: daten[m] for m in sorted(daten, reverse=True)[:TTS_MONATE_BEHALTEN]}
        TTS_VERBRAUCH.parent.mkdir(parents=True, exist_ok=True)
        TTS_VERBRAUCH.write_text(
            json.dumps(daten, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        anteil = stand[klasse] / TTS_FREI_PRO_MONAT
        print(f"  {klasse}-Kontingent {monat}: {_ch(stand[klasse])} von "
              f"{_ch(TTS_FREI_PRO_MONAT)} Zeichen ({anteil:.1%})")
        if anteil >= TTS_WARN_ANTEIL:
            print(f"  WARNUNG: Gratiskontingent {klasse} zu {anteil:.0%} "
                  f"aufgebraucht, noch "
                  f"{_ch(TTS_FREI_PRO_MONAT - stand[klasse])} Zeichen frei")
    except Exception as e:  # noqa: BLE001
        print(f"  Verbrauchsbuchhaltung fehlgeschlagen ({e})")


def _mp3_dauer(pfad: Path) -> float:
    aus = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(pfad)],
        capture_output=True, text=True, check=True)
    return float(aus.stdout.strip())


def _ssml_gruppen(text: str) -> list[tuple[str, list[str]]]:
    """Zerlegt den Berichtstext in SSML-Stuecke unter dem API-Byte-Limit.

    Jedes Quell-Token bekommt ein <mark> davor; Absatzgrenzen werden zu
    <break>-Pausen. Gruppen brechen bevorzugt an Absatzgrenzen, notfalls
    mitten im Absatz (die Mark-Nummern zaehlen je Gruppe ab 0).

    Die Pausenlaenge steht im Trenner (_pause_fuer_trenner). Eine Pause an
    Index 0 ist erlaubt und gewollt -
    faellt eine Gruppengrenze mit einer Kapitelgrenze zusammen, bliebe der
    Halt sonst genau dort aus, wo das Layout mit ihm rechnet."""
    gruppen: list[tuple[str, list[str]]] = []
    tokens: list[str] = []
    pausen: dict[int, str] = {}
    bytes_offen = 0

    def abschliessen() -> None:
        nonlocal bytes_offen
        if not tokens:
            return
        teile = []
        for i, tok in enumerate(tokens):
            if i in pausen:
                teile.append(f'<break time="{pausen[i]}"/>')
            teile.append(f'<mark name="w{i}"/>{xml_escape(tok)}')
        gruppen.append(("<speak>" + " ".join(teile) + "</speak>", tokens.copy()))
        tokens.clear()
        pausen.clear()
        bytes_offen = 0

    # re.split mit Gruppe behaelt die Trenner: [Absatz, Trenner, Absatz, ...]
    stuecke = re.split(r"(\n{2,})", text)
    absaetze = [(stuecke[0], "")] + [
        (stuecke[i + 1], _pause_fuer_trenner(stuecke[i]))
        for i in range(1, len(stuecke) - 1, 2)]
    for absatz, pause in absaetze:
        offen = pause
        for tok in absatz.split():
            kosten = len(xml_escape(tok).encode()) + 22  # Token + Mark-Tag
            if tokens and bytes_offen + kosten > GOOGLE_SSML_MAX_BYTES:
                abschliessen()
            # Erst hier, nach einem moeglichen Gruppenbruch: sonst haengt die
            # Pause am Ende der alten Gruppe, wo ihr Index kein Token mehr
            # trifft, und faellt still aus.
            if offen:
                pausen[len(tokens)] = offen
                offen = ""
            tokens.append(tok)
            bytes_offen += kosten
    abschliessen()
    return gruppen


def _google_anfrage(body: bytes, schluessel: str) -> dict:
    fehler: Exception | None = None
    for versuch in range(3):
        try:
            req = urllib.request.Request(
                GOOGLE_TTS_URL, data=body,
                headers={"Content-Type": "application/json",
                         "X-Goog-Api-Key": schluessel})
            with urllib.request.urlopen(req, timeout=120) as antwort:
                return json.loads(antwort.read())
        except Exception as e:  # noqa: BLE001 - Netz/Quota: kurz warten, nochmal
            fehler = e
            time.sleep(3 * (versuch + 1))
    raise RuntimeError(f"Google TTS nach 3 Versuchen gescheitert: {fehler}")


def google_tts_mit_worten(text: str, ziel_mp3: Path, stimme: str) -> list[Wort]:
    """Vertont per Google Cloud TTS und liefert pro Quell-Token Start/Ende.

    Timepoints liefern nur Startzeiten; das Wortende ist der Start des
    Folgeworts, das letzte Wort einer Gruppe endet am Gruppenende. Die
    MP3-Stuecke (gleiche CBR-Kodierung) werden aneinandergehaengt, den
    Zeitversatz je Gruppe liefert ffprobe auf der wachsenden Datei."""
    schluessel = GOOGLE_TTS_KEY.read_text(encoding="utf-8").strip()
    sprache = "-".join(stimme.split("-")[:2])
    worte: list[Wort] = []
    ziel_mp3.write_bytes(b"")
    versatz = 0.0
    gruppen = _ssml_gruppen(text)
    # Abgerechnet wird hier die SSML-Laenge, nicht die Textlaenge: die Marks
    # zaehlen mit und verdreifachen sie (gemessen 32'242 statt 7'878).
    zeichen = 0
    for nr, (ssml, tokens) in enumerate(gruppen, 1):
        body = json.dumps({
            "input": {"ssml": ssml},
            "voice": {"languageCode": sprache, "name": stimme},
            "audioConfig": {"audioEncoding": "MP3",
                            "speakingRate": GOOGLE_SPRECHRATE},
            "enableTimePointing": ["SSML_MARK"],
        }).encode()
        daten = _google_anfrage(body, schluessel)
        with open(ziel_mp3, "ab") as f:
            f.write(base64.b64decode(daten["audioContent"]))
        marken = {t["markName"]: float(t["timeSeconds"])
                  for t in daten.get("timepoints", [])}
        starts: list[float] = []
        for i in range(len(tokens)):
            vorher = starts[-1] if starts else 0.0
            starts.append(max(vorher, marken.get(f"w{i}", vorher)))
        gesamt = _mp3_dauer(ziel_mp3)
        for i, tok in enumerate(tokens):
            ende = starts[i + 1] if i + 1 < len(tokens) else gesamt - versatz
            worte.append(Wort(tok, versatz + starts[i],
                              versatz + max(ende, starts[i])))
        versatz = gesamt
        zeichen += len(ssml)
        print(f"  Google TTS {nr}/{len(gruppen)}: {len(tokens)} Tokens, "
              f"{gesamt:.1f}s gesamt")
    verbrauch_buchen(stimme, zeichen)
    return worte


# -------------------------------------------------- Studio-Stimmen (ohne Marks)
# Studio-Stimmen klingen natuerlicher als Neural2, kennen aber kein <mark>:
# die API lehnt es mit HTTP 400 ab ("`<mark>` tags are not currently supported
# by Studio voices"), und ohne Marks kommt eine leere timepoints-Liste zurueck
# (am 17.08.2026 gegen die API geprueft, fuer Chirp3-HD ebenso). Die Zeitachse
# entsteht deshalb selbst: jeder Satz wird einzeln synthetisiert, die Stuecke
# werden als rohes PCM aneinandergesetzt, die Pausen als Stille eingerechnet.
# Damit sind die SATZGRENZEN sample-exakt - und genau dort haengen die Anker
# des Szenen-Layouts (ein Stichpunkt je Satz). Die Wortzeiten innerhalb eines
# Satzes werden nach Zeichenlaenge interpoliert; feiner braucht sie nur der
# Untertitel-Umbruch innerhalb eines langen Satzes.
#
# Drei Messungen tragen diesen Aufbau (17.08.2026, en-US-Studio-Q):
#   - Satzweise synthetisiert dauert ein Absatz 36.83s, in einem Stueck
#     36.98s: Studio verliert satzweise praktisch nichts.
#   - Vor-/Nachlaufstille eines Einzelclips 0-30ms vorn, 60-80ms hinten -
#     kein Trimmen noetig, es addiert sich nichts auf.
#   - speakingRate wirkt (27.53s -> 25.34s bei 1.15), das Byte-Limit ist
#     dasselbe wie sonst (5000).
# Der zuerst gepruefte Weg - Absatz in einem Stueck und Satzgrenzen per
# silencedetect an eingefuegten <break>-Marken wiederfinden - ist verworfen:
# ein Doppelpunkt erzeugt schon 0.49s Stille, ein 500-ms-<break> nur 0.56s.
# Auf dieser Schwelle darf das Layout-Timing nicht stehen.
# PCM statt MP3, weil MP3-Frames beim Aneinanderhaengen padden; bei rund 90
# Stuecken waere die Drift sekundengross. Und "text" statt "ssml": ohne Marks
# braucht es kein SSML mehr, also zaehlen nur die echten Sprechzeichen zur
# Abrechnung (7'878 statt 32'242 je Bericht).
#
# Prosodie: Was Studio-Q an SSML annimmt, ist am 19.08.2026 gegen die Live-API
# gemessen (en-US-Studio-Q, derselbe Satz je Probe):
#   <prosody rate>    ok   4.47s -> 4.97s bei rate="85%"
#   <prosody volume>  ok
#   <break>           ok   4.47s -> 4.88s bei 400ms
#   <say-as>, <s>     ok
#   <prosody pitch>   HTTP 400 "`<prosody>` tags do not currently support
#                     `pitch` attributes for Studio voices"
#   <emphasis>        HTTP 400 "`<emphasis>` tags are not currently supported
#                     by Studio voices"
# Betonung gibt es also nicht - der Ersatz ist Verlangsamung. Und Pausen
# kommen weiter als PCM-Stille zwischen den Stuecken, nicht als <break>:
# Stille zwischen zwei Aufrufen ist sample-exakt, ein <break> innerhalb eines
# Satzes verschoebe die interpolierten Wortzeiten des Untertitels.
# SSML wird nur fuer die Saetze gesendet, die es brauchen; alle anderen gehen
# weiter als "text" durch. Sonst zaehlten die Tags in jedem Satz zur
# Abrechnung (der Marken-Pfad kostet mit Tags 32'242 statt 7'878 Zeichen).
STUDIO_KAPITEL_RATE = "92%"  # erster Satz nach einer Kapitelgrenze
STUDIO_ZAHL_RATE = "88%"     # harte Zahlen, Ersatz fuer das fehlende <emphasis>
STUDIO_POINTE_PAUSE = 0.45   # Stille vor dem Schlusssatz eines Absatzes
STUDIO_POINTE_AB = 3         # ... erst ab so vielen Saetzen im Absatz
# Was als harte Zahl gilt: Prozente, Geldbetraege und Groessenordnungen. Eine
# blosse Jahreszahl, ein Datum oder eine Aktenzeichen-Nummer wird bewusst nicht
# verlangsamt. Die Groessenordnungen stehen laengste zuerst, sonst greift das
# kurze "m" in "million" und die Stimme spricht "$303 m" und dann "illion".
_GROESSE = r"(?:billion|million|trillion|bn|tn|[kKmM])"
ZAHL_HART = re.compile(
    r"[$€£]\s?\d[\d.,]*(?:\s?" + _GROESSE + r")?\b"
    # Kein \b hinter dem Prozentzeichen: es ist selbst kein Wortzeichen, die
    # Grenze faende sich nie und "2%" fiele durch.
    r"|\d[\d.,]*\s?%"
    r"|\d[\d.,]*\s?percent(?:age points?)?\b"
    r"|\d[\d.,]*\s?" + _GROESSE + r"\b"
    r"|\d[\d.,]*x\b")

STUDIO_SR = 24000            # LINEAR16-Abtastrate
STUDIO_SATZ_PAUSE = 0.20     # eigene Stille zwischen Saetzen eines Absatzes
STUDIO_SATZ_MIN = 45         # kuerzere Fragmente an den Vorgaenger haengen
STUDIO_MAX_BYTES = 4000      # API-Limit 5000 Bytes je Aufruf
# Nach diesen Woertern ist ein Punkt kein Satzende.
STUDIO_ABKUERZUNGEN = frozenset((
    "u.s.", "e.g.", "i.e.", "vs.", "mr.", "mrs.", "ms.", "dr.", "prof.",
    "no.", "inc.", "corp.", "co.", "ltd.", "llc.", "etc.", "approx.",
    "est.", "jr.", "sr.", "st.", "fig.", "vol.", "cf.", "al.",
))


def _pause_sekunden(angabe: str) -> float:
    """"600ms" -> 0.6 (die Pausen sind fuer den SSML-Pfad als Text notiert)."""
    return float(angabe.removesuffix("ms")) / 1000.0


def _saetze_teilen(absatz: str) -> list[str]:
    """Zerlegt einen Absatz in Saetze, ohne an Abkuerzungen zu zerbrechen.

    Getrennt wird nur, wenn nach dem Satzzeichen ein Grossbuchstabe, eine
    Ziffer oder ein Anfuehrungszeichen folgt und das Wort davor keine
    Abkuerzung und keine Initiale ist. Der Bericht ist voll von Zahlen wie
    "$4,467.80" und Kuerzeln wie "U.S." - ein naiver Split an ". " zerlegt
    genau die."""
    grenzen: list[int] = []
    for m in re.finditer(r"[.!?…][\"')\]”]*\s+", absatz):
        woerter = absatz[:m.start() + 1].split()
        letztes = woerter[-1].lower() if woerter else ""
        danach = absatz[m.end():m.end() + 1]
        initiale = len(letztes) == 2 and letztes[0].isalpha()
        if letztes in STUDIO_ABKUERZUNGEN or initiale:
            continue
        if danach and not (danach.isupper() or danach.isdigit()
                           or danach in "\"'“($"):
            continue
        grenzen.append(m.end())

    roh: list[str] = []
    vorher = 0
    for g in grenzen:
        roh.append(absatz[vorher:g].strip())
        vorher = g
    rest = absatz[vorher:].strip()
    if rest:
        roh.append(rest)

    saetze: list[str] = []
    for s in roh:
        if saetze and len(s) < STUDIO_SATZ_MIN:
            saetze[-1] = f"{saetze[-1]} {s}"
        else:
            saetze.append(s)
    return saetze or [absatz.strip()]


def _bytes_kappen(satz: str) -> list[str]:
    """Zerlegt einen ueberlangen Satz an Wortgrenzen unter das API-Limit."""
    if len(satz.encode()) <= STUDIO_MAX_BYTES:
        return [satz]
    happen: list[str] = []
    offen: list[str] = []
    breite = 0
    for tok in satz.split():
        kosten = len(tok.encode()) + 1
        if offen and breite + kosten > STUDIO_MAX_BYTES:
            happen.append(" ".join(offen))
            offen, breite = [], 0
        offen.append(tok)
        breite += kosten
    if offen:
        happen.append(" ".join(offen))
    return happen


@dataclass(frozen=True)
class Stueck:
    """Ein Sprechstueck: der Klartext (er allein zaehlt fuer die Zeitachse und
    fuer die Untertitel), die Stille davor, und optional eine SSML-Fassung, die
    statt des Klartexts an die API geht. gewichte verschiebt die Wortzeiten
    innerhalb des Satzes: ein verlangsamter Token dauert laenger, als seine
    Zeichenzahl vermuten laesst."""
    text: str
    pause: float
    ssml: str | None = None
    gewichte: tuple[float, ...] = ()


def _zahlen_hervorheben(satz: str) -> tuple[str | None, tuple[float, ...]]:
    """Umschliesst harte Zahlen mit <prosody rate>. Studio-Stimmen lehnen
    <emphasis> ab (HTTP 400, am 19.08.2026 gemessen), also ist Verlangsamung
    der Ersatz - eine langsam gesprochene Zahl hebt sich genauso ab."""
    treffer = list(ZAHL_HART.finditer(satz))
    if not treffer:
        return None, ()
    teile: list[str] = []
    pos = 0
    for m in treffer:
        teile.append(xml_escape(satz[pos:m.start()]))
        teile.append(f'<prosody rate="{STUDIO_ZAHL_RATE}">'
                     f'{xml_escape(m.group())}</prosody>')
        pos = m.end()
    teile.append(xml_escape(satz[pos:]))

    faktor = 100 / float(STUDIO_ZAHL_RATE.rstrip("%"))
    gewichte: list[float] = []
    lauf = 0
    for tok in satz.split():
        start = satz.index(tok, lauf)
        lauf = start + len(tok)
        beruehrt = any(m.start() < lauf and start < m.end() for m in treffer)
        gewichte.append(faktor if beruehrt else 1.0)
    return "<speak>" + "".join(teile) + "</speak>", tuple(gewichte)


def _studio_stuecke(text: str) -> list[Stueck]:
    """Liefert je Sprechstueck den Klartext, die Stille davor und optional SSML.

    Die Pausenlaenge steckt wie im Marken-Pfad im Trenner
    (_pause_fuer_trenner; ton_text setzt ihn).

    Drei Eingriffe in die Prosodie, alle nur dort, wo sie etwas tragen:
    der erste Satz nach einer Kapitelgrenze laeuft langsamer (der Zuhoerer
    hat gerade das Thema gewechselt), harte Zahlen laufen langsamer statt
    betont, und vor dem Schlusssatz eines laengeren Absatzes steht eine
    laengere Stille."""
    teile = re.split(r"(\n{2,})", text)
    kapitel_pause = _pause_sekunden(GOOGLE_KAPITEL_PAUSE)
    absaetze = [(teile[0], 0.0)] + [
        (teile[i + 1], _pause_sekunden(_pause_fuer_trenner(teile[i])))
        for i in range(1, len(teile) - 1, 2)]
    # Der Trenner steht VOR der Ueberschrift, die Ueberschrift ist also selbst
    # der Absatz mit der langen Pause. Eine Ueberschrift ist oft ein einziges
    # Wort ("CRYPTO") - dort traegt die Verlangsamung wenig. Gemeint ist die
    # Kapiteleroeffnung, also zaehlt der Absatz danach mit.
    echte = [(a, p) for a, p in absaetze if a.strip()]
    eroeffnung: set[int] = set()
    for k, (_, p) in enumerate(echte):
        if p >= kapitel_pause:
            eroeffnung.update((k, k + 1))

    stuecke: list[Stueck] = []
    for k, (absatz, pause) in enumerate(echte):
        saetze = _saetze_teilen(absatz)
        for i, satz in enumerate(saetze):
            happen = _bytes_kappen(satz)
            for j, teil in enumerate(happen):
                if j:
                    vor = 0.0            # gekappter Satz laeuft ohne Bruch weiter
                elif i:
                    vor = (STUDIO_POINTE_PAUSE
                           if i == len(saetze) - 1 and len(saetze) >= STUDIO_POINTE_AB
                           else STUDIO_SATZ_PAUSE)
                else:
                    vor = pause
                # Kapiteleroeffnung: nur der erste Satz, und nur ungekappt -
                # ein zerlegter Satz waere sonst halb langsam, halb nicht.
                if i == 0 and j == 0 and len(happen) == 1 and k in eroeffnung:
                    kapitel_ssml = (f'<speak><prosody rate="{STUDIO_KAPITEL_RATE}">'
                                    f'{xml_escape(teil)}</prosody></speak>')
                    stuecke.append(Stueck(teil, vor, kapitel_ssml))
                    continue
                ssml, gewichte = _zahlen_hervorheben(teil)
                stuecke.append(Stueck(teil, vor, ssml, gewichte))
    return stuecke


def _wav_nutzlast(roh: bytes) -> bytes:
    """Schneidet den RIFF-Kopf ab; LINEAR16 kommt als vollstaendige WAV-Datei."""
    if not roh.startswith(b"RIFF"):
        return roh
    pos = 12
    while pos + 8 <= len(roh):
        kennung = roh[pos:pos + 4]
        laenge = int.from_bytes(roh[pos + 4:pos + 8], "little")
        if kennung == b"data":
            nutz = roh[pos + 8:pos + 8 + laenge] if laenge else roh[pos + 8:]
            return nutz[:len(nutz) - len(nutz) % 2]
        pos += 8 + laenge + (laenge & 1)
    raise RuntimeError("LINEAR16-Antwort ohne data-Chunk")


def _studio_pcm(stueck: Stueck, stimme: str, schluessel: str) -> bytes:
    sprache = "-".join(stimme.split("-")[:2])
    eingabe = ({"ssml": stueck.ssml} if stueck.ssml else {"text": stueck.text})
    body = json.dumps({
        "input": eingabe,
        "voice": {"languageCode": sprache, "name": stimme},
        "audioConfig": {"audioEncoding": "LINEAR16",
                        "sampleRateHertz": STUDIO_SR,
                        "speakingRate": GOOGLE_SPRECHRATE},
    }).encode()
    return _wav_nutzlast(base64.b64decode(
        _google_anfrage(body, schluessel)["audioContent"]))


def _worte_verteilen(satz: str, start: float, ende: float,
                     faktoren: tuple[float, ...] = ()) -> list[Wort]:
    """Verteilt die gemessene Satzdauer nach Zeichenlaenge auf die Tokens.

    faktoren streckt einzelne Tokens: wurde eine Zahl per <prosody rate>
    verlangsamt, braucht sie mehr Zeit, als ihre Zeichenzahl hergibt. Ohne
    diese Korrektur wandert der Fehler in die Untertitel des Satzes."""
    tokens = satz.split()
    if not tokens:
        return []
    gewicht: list[float] = [len(t) + 1 for t in tokens]
    if len(faktoren) == len(tokens):
        gewicht = [g * f for g, f in zip(gewicht, faktoren)]
    gesamt = sum(gewicht)
    worte: list[Wort] = []
    lauf = start
    for tok, g in zip(tokens, gewicht):
        dauer = (ende - start) * g / gesamt
        worte.append(Wort(tok, lauf, lauf + dauer))
        lauf += dauer
    letztes = worte[-1]
    worte[-1] = Wort(letztes.text, letztes.start, ende)   # Rundung auffangen
    return worte


def _pcm_zu_mp3(pcm: bytes, ziel_mp3: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(STUDIO_SR),
         "-ac", "1", "-i", "pipe:0", "-b:a", "192k", str(ziel_mp3)],
        input=pcm, check=True)


def studio_tts_mit_worten(text: str, ziel_mp3: Path, stimme: str) -> list[Wort]:
    """Vertont satzweise und baut die Zeitachse sample-exakt selbst auf."""
    schluessel = GOOGLE_TTS_KEY.read_text(encoding="utf-8").strip()
    stuecke = _studio_stuecke(text)
    puffer = bytearray()
    worte: list[Wort] = []
    zeichen = 0
    for nr, st in enumerate(stuecke, 1):
        puffer += b"\x00\x00" * round(st.pause * STUDIO_SR)
        start = len(puffer) / 2 / STUDIO_SR
        puffer += _studio_pcm(st, stimme, schluessel)
        ende = len(puffer) / 2 / STUDIO_SR
        worte.extend(_worte_verteilen(st.text, start, ende, st.gewichte))
        # Abgerechnet wird, was gesendet wurde - bei SSML also samt Tags.
        zeichen += len(st.ssml or st.text)
        if nr % 15 == 0 or nr == len(stuecke):
            print(f"  Studio TTS {nr}/{len(stuecke)} Saetze, {ende:.1f}s, "
                  f"{zeichen} abgerechnete Zeichen")
    _pcm_zu_mp3(bytes(puffer), ziel_mp3)
    verbrauch_buchen(stimme, zeichen)
    return worte


def _ohne_marken(stimme: str) -> bool:
    """Stimmfamilien, die keine SSML-Mark-Timepoints liefern."""
    return "Studio" in stimme or "Chirp" in stimme


def tts_mit_worten(text: str, ziel_mp3: Path, cfg: dict[str, str]) -> list[Wort]:
    """Google Cloud TTS, wenn der API-Key hinterlegt ist, sonst edge-tts.

    Die Fallback-Kette haelt den Cron-Lauf am Leben: scheitert die
    eingestellte Stimme (Netz, Quota, ffmpeg), wird die Marken-Stimme
    versucht und erst danach edge-tts - abgebrochen wird nie."""
    if GOOGLE_TTS_KEY.exists():
        stimmen = [cfg["google_stimme"]]
        ersatz = cfg.get("google_stimme_marken")
        if ersatz and ersatz not in stimmen:
            stimmen.append(ersatz)
        for stimme in stimmen:
            try:
                if _ohne_marken(stimme):
                    print(f"Vertonung: Google TTS satzweise ({stimme})")
                    return studio_tts_mit_worten(text, ziel_mp3, stimme)
                print(f"Vertonung: Google TTS ({stimme})")
                return google_tts_mit_worten(text, ziel_mp3, stimme)
            except Exception as e:  # noqa: BLE001
                print(f"Google TTS mit {stimme} fehlgeschlagen ({e})")
    print(f"Vertonung: edge-tts ({cfg['stimme']})")
    return edge_tts_mit_worten(text, ziel_mp3, cfg["stimme"])


def ton_holen(text: str, ziel_mp3: Path, cfg: dict[str, str],
              cache: bool) -> list[Wort]:
    """Vertonung besorgen, im Testpfad aus dem Cache neben der MP3.

    Am Layout wird in mehreren Renderlaeufen gearbeitet, waehrend Text und
    Stimme unveraendert bleiben; jeder Lauf kostet sonst wieder die vollen
    rund 8'500 abgerechneten TTS-Zeichen. GELESEN wird der Cache nur mit
    --nur-video und nur, wenn Text und Stimme bitgleich sind - der
    Cron-Lauf vertont also immer frisch. GESCHRIEBEN wird er seit 20.08.2026
    immer: shorts.py schneidet die Tages-Shorts entlang genau dieser
    Wort-Zeitstempel aus der fertigen Tonspur, und ohne die Datei bliebe ihm
    nur die groebere SRT-Naeherung."""
    pfad = ziel_mp3.with_suffix(".worte.json")
    schluessel = hashlib.sha1(
        f"{cfg['google_stimme']}|{cfg['stimme']}|{text}".encode()).hexdigest()
    if cache and ziel_mp3.exists() and pfad.exists():
        try:
            d = json.loads(pfad.read_text("utf-8"))
            if d.get("schluessel") == schluessel:
                worte = [Wort(str(w[0]), float(w[1]), float(w[2]))
                         for w in d["worte"]]
                print(f"Vertonung aus dem Cache: {len(worte)} Woerter "
                      f"({pfad.name})")
                return worte
            print("Ton-Cache passt nicht zum Text - vertone neu")
        except (OSError, ValueError, TypeError, KeyError, IndexError) as e:
            print(f"Ton-Cache unbrauchbar ({e}) - vertone neu")
    worte = tts_mit_worten(text, ziel_mp3, cfg)
    try:
        pfad.write_text(json.dumps(
            {"schluessel": schluessel,
             "worte": [[w.text, w.start, w.end] for w in worte]}), "utf-8")
    except OSError as e:
        print(f"Ton-Cache nicht geschrieben ({e})")
    return worte


# ----------------------------------------------------------- SRT-Untertitel

def _srt_zeit(sekunden: float) -> str:
    ms = max(0, round(sekunden * 1000))
    h, rest = divmod(ms, 3_600_000)
    m, rest = divmod(rest, 60_000)
    s, ms = divmod(rest, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _satz_cues(worte: list[Wort], max_zeichen: int = 84
               ) -> list[tuple[float, float, str]]:
    """Gruppiert Wort-Zeitstempel zu satzweisen Haeppchen (Start, Ende, Text):
    Cues brechen an Satzenden, an hoerbaren Pausen und spaetestens bei
    max_zeichen. Gemeinsame Grundlage fuer die SRT-Untertitel (srt_erzeugen)
    und die Fallback-Bullets gegen Text-Luecken (_luecken_fuellen)."""
    cues: list[tuple[float, float, str]] = []
    gruppe: list[Wort] = []

    def abschliessen() -> None:
        if not gruppe:
            return
        text = " ".join(w.text for w in gruppe)
        cues.append((gruppe[0].start, gruppe[-1].end, text))
        gruppe.clear()

    for i, w in enumerate(worte):
        gruppe.append(w)
        laenge = sum(len(x.text) + 1 for x in gruppe) - 1
        naechstes = worte[i + 1] if i + 1 < len(worte) else None
        satzende = w.text.rstrip("\"'»«)]").endswith((".", "!", "?", ":", "…"))
        pause = naechstes is not None and naechstes.start - w.end > 0.45
        voll = naechstes is not None and \
            laenge + 1 + len(naechstes.text) > max_zeichen
        if (satzende and laenge >= 24) or pause or voll:
            abschliessen()
    abschliessen()
    return cues


def srt_erzeugen(worte: list[Wort], ziel: Path) -> int:
    """Baut aus den Wort-Zeitstempeln der Vertonung eine SRT-Untertiteldatei.

    Eigene Untertitel statt der YouTube-Automatik: die Zeitstempel stammen
    direkt aus der TTS und die Cues brechen an Satzenden, an hoerbaren Pausen
    und spaetestens bei zwei Untertitelzeilen - satzweise, ruhige
    Einblendungen statt wortweisem Gestotter. Gibt die Cue-Anzahl zurueck."""
    cues = _satz_cues(worte)
    zeilen: list[str] = []
    for nr, (start, ende, text) in enumerate(cues, 1):
        if len(text) > 42:
            # an dem Leerzeichen brechen, das der Mitte am naechsten liegt
            luecken = [i for i, z in enumerate(text) if z == " "]
            if luecken:
                mitte = min(luecken, key=lambda i: abs(i - len(text) // 2))
                text = text[:mitte] + "\n" + text[mitte + 1:]
        ende = max(ende, start + 1.2)      # sehr kurze Cues etwas stehen lassen
        if nr < len(cues):
            ende = min(ende, cues[nr][0])  # nie in den naechsten Cue ragen
        zeilen.append(f"{nr}\n{_srt_zeit(start)} --> {_srt_zeit(ende)}\n{text}\n")
    ziel.write_text("\n".join(zeilen), encoding="utf-8")
    return len(cues)


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

MOTIV_RUECKGRIFF = 7   # so viele Tage zurueck darf die Kulisse notfalls stammen
_quelle_gemeldet: set[str] = set()


def _motive_brauchbar(ordner: Path) -> dict | None:
    """Sichtpruefungs-Ergebnis eines Tages, aber nur wenn es wirklich Bilder
    benennt: threads nicht leer und mindestens eine genannte Datei liegt da.
    Ein leeres oder verwaistes motive.json zaehlt nicht - sonst gilt der Tag
    als versorgt und der Rueckgriff greift nicht."""
    try:
        daten = json.loads((ordner / "motive.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    threads = daten.get("threads")
    if not isinstance(threads, dict) or not threads:
        return None
    for namen in threads.values():
        if isinstance(namen, list) and any((ordner / str(n)).exists()
                                           for n in namen):
            return daten
    return None


def motiv_quelle(datum: str) -> tuple[Path, dict] | None:
    """Ordner und motive.json, aus denen die Kulisse dieses Videos kommt.

    Normalfall ist der eigene Tag. Scheitert dessen Sichtpruefung, wird der
    juengste Tag der letzten MOTIV_RUECKGRIFF Tage genommen, dessen Bilder
    schon einmal freigegeben und gezeigt wurden. Wiederholte Bilder von
    gestern sind unschoen, ein Video aus einem einzigen Bild ist ein Fehler -
    genau das passierte am 18.08.2026, als ein doppelt beschriebenes Bildpaar
    die Freigabe aller 36 Tagesbilder kippte und alle 70 Szenen mit dem
    Vorschaubild-Motiv liefen. Ungepruefte Downloads kommen nie infrage: die
    Zuordnung entsteht ausschliesslich aus einem motive.json.

    Die Thread-Nummern eines fremden Tages passen auf keinen Abschnitt des
    heutigen Berichts - der Szenenbau zieht die Bilder dann reihum aus dem
    Pool statt thread-treu, was fuer eine Kulisse voellig genuegt."""
    eigen = HINTERGRUND_DIR / datum
    daten = _motive_brauchbar(eigen)
    if daten is not None:
        return eigen, daten
    try:
        tag = date.fromisoformat(datum)
    except ValueError:
        return None
    for zurueck in range(1, MOTIV_RUECKGRIFF + 1):
        alt_dir = HINTERGRUND_DIR / (tag - timedelta(days=zurueck)).isoformat()
        daten = _motive_brauchbar(alt_dir)
        if daten is not None:
            if datum not in _quelle_gemeldet:
                _quelle_gemeldet.add(datum)
                print(f"WARNUNG: keine freigegebenen Hintergrundbilder fuer "
                      f"{datum} - Kulisse kommt aus {alt_dir.name}")
            return alt_dir, daten
    if datum not in _quelle_gemeldet:
        _quelle_gemeldet.add(datum)
        print(f"WARNUNG: keine freigegebenen Hintergrundbilder fuer {datum} "
              f"und keine aus den letzten {MOTIV_RUECKGRIFF} Tagen - das "
              f"Video laeuft mit dem Tagesmotiv als einziger Kulisse")
    return None


def motiv_werte(datum: str) -> dict[str, dict]:
    """Bewertungen der Sichtpruefung je Bilddatei (bildlich/unterhaltung/
    themen, 1-5; seit 16.08.2026 in motive.json). Leer bei alten Tagen ohne
    Bewertungen - dann zaehlt jedes Bild als neutrale 3. Kommt aus demselben
    Tag wie die Bilder selbst (siehe motiv_quelle)."""
    quelle = motiv_quelle(datum)
    if quelle is None:
        return {}
    werte = quelle[1].get("werte")
    return werte if isinstance(werte, dict) else {}


def motiv_typen(datum: str) -> dict[str, str]:
    """Dateiname -> "animiert"/"standbild" aus motive.json (siehe
    motiv_werte). Leer bei alten Tagen ohne das Feld - dann gilt jedes Bild
    implizit als Standbild, der Video-Lauf rendert es wie bisher."""
    quelle = motiv_quelle(datum)
    if quelle is None:
        return {}
    typ = quelle[1].get("typ")
    return typ if isinstance(typ, dict) else {}


def motiv_poster_pfade(datum: str) -> dict[str, Path]:
    """Dateiname -> Posterframe-Pfad fuer animierte Motive (siehe
    motiv_werte, Feld "poster"); leer bei Standbildern und bei alten Tagen
    ohne das Feld."""
    quelle = motiv_quelle(datum)
    if quelle is None:
        return {}
    ordner, daten = quelle
    poster = daten.get("poster")
    if not isinstance(poster, dict):
        return {}
    return {name: ordner / str(datei) for name, datei in poster.items()
            if (ordner / str(datei)).exists()}


def _bild_wert(werte: dict[str, dict], name: str, schluessel: str) -> int:
    try:
        roh = (werte.get(name) or {}).get(schluessel)
        return max(1, min(5, int(roh))) if roh is not None else 3
    except (TypeError, ValueError, AttributeError):
        return 3


def _bild_rang(werte: dict[str, dict], name: str) -> int:
    """Sortierwert eines Hintergrundbildes: die Bildlichkeit (echtes Motiv
    statt Text-Screenshot) zaehlt doppelt, dazu der Unterhaltungswert.

    Die Themennaehe fliesst absichtlich NICHT ein - sie hat am 17.08.2026
    Kurstabellen und Suchergebnis-Screenshots vor Memes gesetzt, weil solche
    Textwaende thematisch perfekt passen und als Kulisse trotzdem nichts
    hergeben."""
    return (2 * _bild_wert(werte, name, "bildlich")
            + _bild_wert(werte, name, "unterhaltung"))


def _ist_textwand(werte: dict[str, dict], name: str) -> bool:
    """Bild ist ueberwiegend Text - Screenshot einer Artikel- oder
    Suchergebnisseite, Chatverlauf, Kurstabelle. Als Kulisse nur die letzte
    Wahl (Nutzerwunsch 17.08.2026: Hintergruende, die nicht nur Text sind).

    Kennt die Sichtpruefung des Tages die Bildlichkeit noch nicht (Tage vor
    dem 18.08.2026), bleibt der Unterhaltungswert 1 das einzige Signal.
    Geprueft wird die Anwesenheit des Rohschluessels, nicht sein Wert: ein
    fehlendes Feld liest _bild_wert als neutrale 3, und ein starkes Motiv mit
    unterhaltung=1 (schoenes, aber langweiliges Foto) darf keine Textwand
    sein."""
    unterhaltung = _bild_wert(werte, name, "unterhaltung")
    roh = werte.get(name)
    if not isinstance(roh, dict) or "bildlich" not in roh:
        return unterhaltung <= 1
    return _bild_wert(werte, name, "bildlich") <= 2 and unterhaltung <= 2


def thread_titel(datum: str) -> dict[str, str]:
    """Thread-Titel je Thread-ID aus den Extrakt-Seiten des Tages: deren H1
    traegt den Original-Betreff. Fuer die Fusszeile der Themen-Folien -
    lesbarer als die nackte Thread-Nummer. Fehlt die Seite oder der Titel,
    bleibt die Nummer der Fallback."""
    titel: dict[str, str] = {}
    for pfad in sorted((EXTRAKTE / datum).glob("*.md")):
        if not pfad.stem.isdigit():
            continue
        try:
            kopf = pfad.read_text(encoding="utf-8").lstrip("﻿ \n") \
                       .splitlines()[0]
        except (OSError, IndexError):
            continue
        if kopf.startswith("# "):
            # Betreffzeilen enthalten gern URLs - fuer die Folie wertlos.
            text = re.sub(r"https?://\S+", "", kopf[2:])
            text = entschaerft(re.sub(r"\s+", " ", text).strip(" -·|"))
            if text:
                titel[pfad.stem] = text
    return titel


def motiv_zuordnung(datum: str) -> dict[str, list[Path]]:
    """Freigegebene Hintergrundbilder je Thread (Report-Lauf,
    arbeit/motive/<datum>/), je Thread absteigend nach Bildrang sortiert
    (Motive vor Textwaenden). Leer nur, wenn auch der Rueckgriff auf die
    Vortage nichts findet (siehe motiv_quelle)."""
    quelle = motiv_quelle(datum)
    if quelle is None:
        return {}
    ordner, daten = quelle
    threads = daten["threads"]
    # Bewertungen aus derselben Datei wie die Bilder, nicht aus motiv_werte():
    # bei einem Rueckgriff darf beides nicht aus verschiedenen Tagen kommen.
    rohwerte = daten.get("werte")
    werte = rohwerte if isinstance(rohwerte, dict) else {}
    aus: dict[str, list[Path]] = {}
    for tid, namen in threads.items():
        namen = sorted(namen, key=lambda n: (-_bild_rang(werte, n), n))
        pfade = [ordner / n for n in namen if (ordner / n).exists()]
        if pfade:
            aus[str(tid)] = pfade
    return aus


class MotivWahl:
    """Zustand der Kulissen-Motivwahl: frisches eigenes Thread-Bild vor
    frischem Pool-Bild vor Wiederholung. Aus szenen_bauen (v7) extrahiert,
    damit shorts.py exakt dieselbe Kapitel-Zuordnung rechnen kann - Story i
    im Short traegt so dasselbe Motiv wie Kapitel i im Hauptvideo (die
    Kapitel-Reservierung ist dort der erste Pool-Zugriff auf frischem
    Zustand, eine frische MotivWahl liefert also identische Ergebnisse)."""

    def __init__(self, datum: str) -> None:
        self.zuteilung = motiv_zuordnung(datum)
        self.werte = motiv_werte(datum)
        motive = sorted(MOTIV_DIR.glob(f"{datum}.*"))
        self.tages_motiv: Path | None = motive[0] if motive else None
        self.pool: list[Path] = sorted(
            {p for pfade in self.zuteilung.values() for p in pfade},
            key=lambda p: (-_bild_rang(self.werte, p.name), p.name))
        self.pool_i = 0
        self.verwendet: set[Path] = set()

    def pool_bild(self, nur_frisch: bool = False) -> Path | None:
        if not self.pool:
            return None if nur_frisch else self.tages_motiv
        for k in range(len(self.pool)):
            p = self.pool[(self.pool_i + k) % len(self.pool)]
            if p not in self.verwendet:
                self.pool_i = (self.pool_i + k + 1) % len(self.pool)
                self.verwendet.add(p)
                return p
        if nur_frisch:
            return None
        self.pool_i += 1
        return self.pool[(self.pool_i - 1) % len(self.pool)]

    def eigenes_bild(self, eigene: list[Path]) -> Path | None:
        """Erstes noch nicht gezeigtes eigenes Bild des Abschnitts; reine
        Textwaende verlieren diesen Heimvorteil (siehe _ist_textwand)."""
        for p in eigene:
            if _ist_textwand(self.werte, p.name):
                continue
            if p not in self.verwendet:
                self.verwendet.add(p)
                return p
        return None

    def kapitel_reservieren(self, abschnitte: list[Abschnitt],
                            nrs: list[int]
                            ) -> tuple[list[list[Path]], list[Path | None]]:
        """Kapitel-Motive vorab reservieren, in Berichtsreihenfolge (die
        Agenda-Vorschau des Hauptvideos nutzt sie mit, ohne selbst frische
        Bilder zu verbrauchen - wie in v6)."""
        kapitel_eigene: list[list[Path]] = []
        kapitel_motive: list[Path | None] = []
        for nr in nrs:
            eigene = [p for tid in abschnitte[nr].threads
                      for p in self.zuteilung.get(tid, [])]
            kapitel_eigene.append(eigene)
            kapitel_motive.append(self.eigenes_bild(eigene)
                                  or self.pool_bild(nur_frisch=True)
                                  or (eigene[0] if eigene
                                      else self.pool_bild()))
        return kapitel_eigene, kapitel_motive


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
    None steht fuer die einfarbige Flaeche.

    Dieser v6-Fallback rendert Motive per PIL als reine Standbild-Pipeline
    (folien.py) - ein animiertes Motiv (GIF/WebM/MP4) wird deshalb hier
    immer durch sein Posterframe ersetzt, nie roh durchgereicht."""
    typen = motiv_typen(datum)
    poster_pfade = motiv_poster_pfade(datum)
    zuordnung = {
        tid: [poster_pfade.get(p.name, p) if typen.get(p.name) == "animiert"
              else p for p in pfade]
        for tid, pfade in motiv_zuordnung(datum).items()
    }
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


# ----------------------------------------------------------- Praesentationsmodus (v6)

# Gesprochene Rahmen-Saetze der Praesentation. Nur englisch: die Praesentation
# laeuft vorerst nur fuer das englische Video.
PRAES_INTRO = "This is the 4chan business board report for {datum_lang}."
# Der Titel-Aufhaenger kauft den Klick, also muss ihn die Eroeffnung auch
# einloesen - und zwar als ERSTES gesprochenes Wort. Bis 21.08.2026 stand
# "Today's top story:" davor; das sind rund 1.5 s Ansage vor der Zahl, in
# genau dem Fenster, in dem die Abbruchkurve am steilsten faellt. Der Hook
# selbst eroeffnet jetzt, die Titel-Karte der Szene traegt das Label
# ("TODAY'S TOP STORY") weiterhin im Bild.
PRAES_HOOK = "{hook}"
PRAES_AGENDA = "Coming up:"
AGENDA_TEASER = 3        # so viele Kapitel nennt die Agenda (von sieben)
TOKENS_PRO_S = 2.50      # gemessene Sprechrate ohne Pausen: Studio-Q satzweise
                         # 2.53 (Neural2-J war 2.30). Studio-O spricht denselben
                         # Absatz 2.5 % schneller (23.6 s statt 24.2 s), was die
                         # Schaetzung minim zu lang macht - unter der Aufloesung
                         # eines Rahmensatzes. Zaehlt nur fuer die
                         # Vorspann-Schaetzung: greift der Fallback auf
                         # Neural2, wird der Vorspann etwas kurz geschaetzt -
                         # das kostet hoechstens einen Rahmensatz.
INTRO_BODEN = 11.5       # Sekunden; darunter wird der Vorspann gestreckt
INTRO_DECKEL = 15.0      # Sekunden; darueber wird er gekuerzt. Bis 21.08.2026
                         # gab es nur den Boden und keine Decke - der Vorspann
                         # wuchs von 29.6 s (20.08.) ueber 37.0 s auf 48.9 s im
                         # produktiven Lauf vom 21.08. Gegen die gemessene
                         # Abbruchkurve (50 % weg nach 1:08) verbrannte er
                         # damit drei Viertel der mittleren Verweildauer,
                         # bevor der erste Kapitelinhalt begann. Der Boden hat
                         # Vorrang: er sichert die YouTube-Kapitelregel
                         # (Kapitel 1 nicht vor 10 s), die Decke greift nur
                         # oberhalb davon.
ZAHLEN_GESPROCHEN = 2    # so viele der vier TL;DR-Zahlen werden VORGELESEN;
                         # im Bild stehen weiterhin alle vier (siehe
                         # zahlen_szenen). Vier gesprochene Zahlensaetze
                         # kosteten allein rund 30 s vor der ersten Story.
ZAHL_SATZ_WORTE = 12     # laengere Zahlensaetze werden am Satzende gekappt:
                         # das Feld "satz" war unbegrenzt und produktiv voll
                         # ausgeschriebene Fliesssaetze ("one dollar and fifty
                         # three cents") sind die Hauptursache des
                         # 48.9-s-Vorspanns gewesen - nicht die Anzahl Zahlen.
# Ueberleitung in den TL;DR-Zahlenblock direkt nach dem Cold Open (seit
# 20.08.2026 vorne statt am Videoende - die Analytics zeigten eine
# Abbruchwand bei 1:08, die Agenda-Teaser-Strecke ist dafuer entfallen).
# Bewusst ohne Zahlwort: gesprochen werden ZAHLEN_GESPROCHEN, im Bild stehen
# vier - eine Ansage, die sich auf eine Anzahl festlegt, waere fuer eine der
# beiden Seiten falsch.
PRAES_ZAHLEN = "Today's numbers."
ZAHLEN_LABEL = "Today's numbers"   # dieselbe Ansage als Bild-Karte
# Schluss-Beat vor dem Abbinder: staerkstes Board-Zitat, dann die offene
# Frage fuer morgen. Der Abbinder selbst ist seit 21.08.2026 auf einen Satz
# gekuerzt (vorher drei) - er ist die Stelle, an der ohnehin niemand mehr
# zuhoert, und jede Sekunde dort geht der Cliffhanger-Frage verloren.
PRAES_ZITAT = 'Last word from the board: "{zitat}"'
PRAES_OUTRO = "That's the board report. Sources in the description."
# Rollen, die das letzte Kapitel beenden: der erste dieser Bloecke NACH der
# letzten Kapitel-Ueberschrift markiert, wo der Kapitelrumpf aufhoert.
# "zahl_kopf" steht nur bei einer Blockliste alter Ordnung dort (Zahlen am
# Ende), der Schluss-Beat und das Outro immer.
SCHLUSS_ROLLEN = ("zahl_kopf", "schluss_zitat", "schluss_frage", "outro")
KAPITELNAME_MAX = 44     # Zeichen im YouTube-Kapitelnamen. Der Prompt fordert
                         # 40 fuer die Ueberschrift; die vier Zeichen Luft
                         # fangen ab, dass der Player sonst mitten im Wort
                         # abschneidet.
MONATE_EN = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]
BLEND_SCHRITTE = 6       # Zwischenbilder je Ueberblendung Reveal -> Folie
BLEND_DAUER = 0.08       # Standzeit je Zwischenbild (Sekunden)
PUNKT_MIN_ABSTAND = 0.8  # Stichpunkte erscheinen nie dichter als so


def _datum_lang(datum: str) -> str:
    j, m, t = datum.split("-")
    return f"{MONATE_EN[int(m) - 1]} {int(t)}, {j}"


def folien_laden(tag_dir: Path) -> dict | None:
    """folien.json des Report-Laufs (Folientitel, Stichpunkte, Zahlen je
    Abschnitt). None bei jedem Problem - dann faellt das Video auf das
    v5-Text-Layout zurueck."""
    pfad = tag_dir / "folien.json"
    try:
        # entschaerft() laeuft ueber den Rohtext, damit es jeden Textwert der
        # verschachtelten Struktur trifft (Folientitel, Stichpunkte, Zitate)
        # ohne sie durchlaufen zu muessen; die Feldnamen sind englische
        # Bezeichner und von der Wortliste nicht betroffen.
        daten = json.loads(entschaerft(pfad.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as e:
        print(f"keine brauchbare folien.json ({e}) - Text-Layout")
        return None
    if (not isinstance(daten, dict)
            or not isinstance(daten.get("abschnitte"), list)
            or not daten["abschnitte"]):
        print("folien.json ohne Abschnitte - Text-Layout")
        return None
    return daten


_NORM = re.compile(r"[^0-9a-zäöü$% ]+")


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", _NORM.sub(" ", text.lower())).strip()


def folien_zuordnen(fdaten: dict, bloecke: list[Block]) -> dict[int, dict]:
    """Folien-Abschnitte den Berichtsabschnitten zuordnen: erst ueber die
    (normalisierte) Ueberschrift, Rest der Reihe nach. Nicht zuordenbare
    Berichtsabschnitte bekommen spaeter eine Folie ohne Stichpunkte."""
    koepfe = [(b.abschnitt, _norm_text(b.text)) for b in bloecke
              if b.art == "ueberschrift"]
    # Der Drehbuch-Eintrag zum Sammelabschnitt "Still true from yesterday"
    # muss raus: seit 21.08.2026 wird dieser Abschnitt nicht mehr vertont,
    # also gibt es keinen Kopf, der ihn per Ueberschrift aufnimmt. Ueber den
    # "Rest der Reihe nach"-Pfad unten landeten seine zwei Stichworte sonst
    # in einem echten Kapitel, sobald ein anderes seinen Heading-Match
    # verfehlt - und das Kapitel liefe mit fremden Bullets.
    eintraege = [a for a in fdaten["abschnitte"]
                 if isinstance(a, dict) and a.get("titel")
                 and not rr.ist_still_true(str(a.get("ueberschrift") or ""))]
    nach_kopf = {_norm_text(str(a.get("ueberschrift", ""))): a for a in eintraege}
    aus: dict[int, dict] = {}
    for nr, kopf in koepfe:
        if kopf in nach_kopf:
            aus[nr] = nach_kopf.pop(kopf)
    uebrig = [a for a in eintraege if a in nach_kopf.values()]
    for nr, _ in koepfe:
        if nr not in aus and uebrig:
            aus[nr] = uebrig.pop(0)
    return aus


def _folien_titel(zuordnung: dict[int, dict], bloecke: list[Block],
                  nr: int) -> str:
    if nr in zuordnung:
        return str(zuordnung[nr]["titel"]).strip()
    for b in bloecke:
        if b.art == "ueberschrift" and b.abschnitt == nr:
            return b.text.capitalize()
    return ""


def _hook_gesprochen(hook: str) -> str:
    """Der Titel-Aufhaenger als sprechbarer Satz.

    Geaendert wird nur die Interpunktion: der Doppelpunkt des Hooks wird zum
    Komma, weil PRAES_HOOK schon einen fuehrt, und am Ende steht ein
    Satzzeichen. Die Grossschreibung bleibt, wie der Titel sie hat - gemessen
    am 17.08.2026 spricht Google TTS (Neural2-J) "IMPOSSIBLE" und
    "Impossible" gleich lang, buchstabiert also nichts, und Kuerzel wie NVDA
    erkennt es von selbst (0.70 s gegen 0.29 s fuer GOLD).

    Ein Klammer-Ticker ("Moderna (MRNA) PUMPS") faellt fuer die Sprechfassung
    weg: gesprochen ist er nur die Wiederholung des Firmennamens - im Titel
    steht er seit dem Frontloading (20.08.2026) fuer die Suche."""
    hook = re.sub(r"\s*\([A-Z0-9.]{1,6}\)", "", hook)
    satz = re.sub(r"\s+", " ", hook.replace(":", ",")).strip()
    satz = re.sub(r"\s+([,.])", r"\1", satz).rstrip(",;:- ")
    if satz and satz[-1] not in ".!?":
        satz += "."
    return satz


def _zahl_satz(karte: dict) -> str:
    """Der gesprochene Satz einer TL;DR-Zahl, auf Vorspann-Mass gekappt.

    Das Drehbuch-Feld "satz" ist Modelltext und war bis 21.08.2026 in der
    Laenge unbegrenzt - produktiv standen dort voll ausgeschriebene
    Fliesssaetze, die den Vorspann auf 48.9 s trieben. Gekappt wird in zwei
    Stufen: erst auf den ERSTEN Satz (mehr als einer ist im Vorspann nie
    gemeint), dann auf ZAHL_SATZ_WORTE Woerter. Das Kappen laesst die Zahl
    selbst unberuehrt, weil sie am Satzanfang steht."""
    roh = str(karte.get("satz")
              or f"{karte.get('titel', '')}: {karte.get('wert', '')}").strip()
    erster = re.split(r"(?<=[.!?])\s+", roh)[0].strip() if roh else ""
    worte = erster.split()
    if len(worte) > ZAHL_SATZ_WORTE:
        erster = " ".join(worte[:ZAHL_SATZ_WORTE]).rstrip(",;:- ")
    if erster and erster[-1] not in ".!?":
        erster += "."
    return erster


def praesentations_bloecke(bloecke: list[Block], zuordnung: dict[int, dict],
                           fdaten: dict, datum: str,
                           hook: str = "") -> list[Block]:
    """Das gesprochene Skript der Praesentation: Rahmen-Saetze plus der
    unveraenderte Berichtstext. Jeder Rahmen-Satz ist ein eigener Block, damit
    seine Zeitfenster die Folienwechsel steuern; die art bleibt "absatz",
    damit der ASS-Ersatzpfad dieselben Bloecke rendern kann.

    hook ist der Aufhaenger des Tagestitels; er eroeffnet den Intro-Block,
    damit die ersten Sekunden den Klick einloesen statt mit Datum und
    Inhaltsverzeichnis zu beginnen. Leer bleibt er beim statischen
    Serientitel, der keinen Aufhaenger hat.

    Direkt nach dem Cold Open kommt der TL;DR-Zahlenblock (zahl_kopf +
    hoechstens vier zahl-Bloecke): die Analytics-Messung vom 19./20.08.2026
    zeigte eine Abbruchwand bei 1:08 (50 % der Zuschauer weg bei 11 min
    Laufzeit) - die vier Kennzahlen sind der dichteste Inhalt des Tages und
    gehoeren deshalb in dieses Fenster, nicht ans Ende. Die fruehere
    Agenda-Teaser-Strecke ("Coming up" + AGENDA_TEASER Kapitel) entfaellt
    dafuer; am Videoende werden die Zahlen NICHT wiederholt. Nur wenn
    folien.json keine brauchbaren zahlen traegt, laeuft als Fallback die
    alte Agenda-Strecke (gemessen am 17.08.2026: erster Inhaltssatz bei
    34.7 s, davon 22.5 s Rahmen - deshalb nur AGENDA_TEASER Kapitel statt
    aller sieben).

    Der Serien-Satz mit Datum ist nur noch ein Boden: Kapitel 1 muss
    mindestens 10 s nach Videobeginn liegen, sonst laesst kapitel_bauen
    seine Marke fallen. Mit vier Zahlen-Saetzen vorne ist der Boden
    faktisch tot (der TL;DR-Block spricht allein rund 30 s), aber er bleibt
    als Sicherung: im Agenda-Fallback mit knappem Hook ("GOLD BREAKS
    $5,000", rund 2 s) reicht der Rest sonst nicht. Geschaetzt wird vor der
    Vertonung, weil die Blockliste vor ihr feststehen muss - mit der
    gemessenen Sprechrate, den Absatzpausen und der langen Kapitelpause."""
    aus: list[Block] = []
    satz = _hook_gesprochen(hook)
    karten = [k for k in fdaten.get("zahlen") or []
              if isinstance(k, dict) and k.get("wert")][:4]
    if karten:
        # TL;DR-Pfad: Blockgrenze vor dem Zahlen-Kopf und vor jeder Zahl
        # kostet GOOGLE_ABSATZ_PAUSE, die zur ersten Kapitel-Ueberschrift
        # GOOGLE_KAPITEL_PAUSE.
        zahl_saetze = [_zahl_satz(k) for k in karten[:ZAHLEN_GESPROCHEN]]

        def schaetzen() -> float:
            worte = sum(len(t.split())
                        for t in [PRAES_HOOK.format(hook=satz) if satz else "",
                                  PRAES_ZAHLEN, *zahl_saetze])
            return (worte / TOKENS_PRO_S
                    + _pause_sekunden(GOOGLE_ABSATZ_PAUSE)
                    * (1 + len(zahl_saetze))
                    + _pause_sekunden(GOOGLE_KAPITEL_PAUSE))

        # Decke durchsetzen: der letzte gesprochene Zahlensatz faellt weg,
        # solange der Vorspann zu lang bleibt - seine Karte steht im Bild
        # weiterhin (zahlen_szenen zeigt alle vier, unabhaengig davon, wie
        # viele davon vorgelesen werden). Ein Zahlensatz ist immer der
        # letzte, der geopfert wird: ohne ihn bliebe der Zahlen-Kopf eine
        # Ansage ohne Inhalt.
        geschaetzt = schaetzen()
        while geschaetzt > INTRO_DECKEL and len(zahl_saetze) > 1:
            weg = zahl_saetze.pop()
            geschaetzt = schaetzen()
            print(f"Vorspann geschaetzt ueber {INTRO_DECKEL:.0f}s - "
                  f"Zahlensatz {weg[:40]!r} nur noch im Bild, jetzt "
                  f"{geschaetzt:.1f}s")
        rahmen = [PRAES_HOOK.format(hook=satz) if satz else "",
                  PRAES_ZAHLEN, *zahl_saetze]
    else:
        # Fallback ohne Zahlen: die alte Agenda-Teaser-Strecke.
        nummern = [b.abschnitt for b in bloecke if b.art == "ueberschrift"]
        zahl_saetze = []
        titel_saetze = [_folien_titel(zuordnung, bloecke, nr).rstrip(".") + "."
                        for nr in nummern[:AGENDA_TEASER]]
        # Die Blockgrenze vor dem Agenda-Kopf kostet GOOGLE_ABSATZ_PAUSE, die
        # vor jedem Agenda-Eintrag GOOGLE_AGENDA_PAUSE, die zur ersten
        # Kapitel-Ueberschrift GOOGLE_KAPITEL_PAUSE.
        rahmen = [PRAES_HOOK.format(hook=satz) if satz else "",
                  PRAES_AGENDA, *titel_saetze]
        geschaetzt = (sum(len(t.split()) for t in rahmen) / TOKENS_PRO_S
                      + _pause_sekunden(GOOGLE_ABSATZ_PAUSE)
                      + _pause_sekunden(GOOGLE_AGENDA_PAUSE) * len(titel_saetze)
                      + _pause_sekunden(GOOGLE_KAPITEL_PAUSE))
    if not satz or geschaetzt < INTRO_BODEN:
        # format() bewusst nur auf der eigenen Konstante: der Hook ist
        # Modelltext und darf geschweifte Klammern enthalten.
        rahmen[0] = (f"{rahmen[0]} "
                     f"{PRAES_INTRO.format(datum_lang=_datum_lang(datum))}"
                     ).strip()
        print(f"Vorspann geschaetzt {geschaetzt:.1f}s - Serien-Satz bleibt "
              f"drin, damit Kapitel 1 nicht unter 10s rutscht")
    aus.append(Block("absatz", rahmen[0], 0, rolle="intro"))
    if karten:
        aus.append(Block("absatz", PRAES_ZAHLEN, 0, rolle="zahl_kopf"))
        for z in zahl_saetze:
            aus.append(Block("absatz", z, 0, rolle="zahl"))
    else:
        aus.append(Block("absatz", PRAES_AGENDA, 0, rolle="agenda_kopf"))
        for t in titel_saetze:
            aus.append(Block("absatz", t, 0, rolle="agenda"))
    aus.extend(bloecke)
    # Schluss-Beat vor dem Abbinder (21.08.2026): das staerkste Board-Zitat
    # des Tages und eine offene Frage fuer morgen. Bis dahin endete das Video
    # mit dem Sammelabschnitt der unveraenderten Themen - der schwaechsten
    # Stelle des Berichts an der auffaelligsten Stelle des Videos. Beide
    # Felder sind optional; fehlt eines, faellt nur es weg.
    schluss = fdaten.get("schluss")
    schluss = schluss if isinstance(schluss, dict) else {}
    zitat = str(schluss.get("zitat") or "").strip()
    frage = str(schluss.get("frage") or "").strip()
    if zitat:
        aus.append(Block("absatz", PRAES_ZITAT.format(zitat=zitat.strip('"')),
                         0, rolle="schluss_zitat"))
    if frage:
        aus.append(Block("absatz", frage, 0, rolle="schluss_frage"))
    aus.append(Block("absatz", PRAES_OUTRO, 0, rolle="outro"))
    return aus


def zahlen_vorne(bloecke: list[Block]) -> bool:
    """True, wenn der TL;DR-Zahlenblock vor dem ersten Kapitel steht (die
    Blockfolge seit 20.08.2026). False im Agenda-Fallback ohne Zahlen und
    bei einer Blockliste alter Ordnung (Zahlen am Ende) - die Renderpfade
    bleiben damit fuer beide Ordnungen korrekt."""
    for b in bloecke:
        if b.rolle == "zahl_kopf":
            return True
        if b.art == "ueberschrift":
            return False
    return False


def _anker_spanne(anker: str, worte: list[Wort]) -> tuple[float, float] | None:
    """Start- und Endzeit der Anker-Phrase im Wortstrom des Abschnitts
    (normalisierter Folgenvergleich); None, wenn die Phrase nicht vorkommt."""
    ziel = [t for t in (_norm_text(w) for w in anker.split()) if t]
    if not ziel:
        return None
    toks = [_norm_text(w.text) for w in worte]
    for i in range(len(toks) - len(ziel) + 1):
        if toks[i:i + len(ziel)] == ziel:
            return worte[i].start, worte[i + len(ziel) - 1].end
    return None


def _anker_zeit(anker: str, worte: list[Wort]) -> float | None:
    """Startzeit der Anker-Phrase; None, wenn die Phrase nicht vorkommt."""
    spanne = _anker_spanne(anker, worte)
    return None if spanne is None else spanne[0]


def _satz_ende(worte: list[Wort], ab: float) -> float | None:
    """Ende des Satzes, in dem die Zeit `ab` liegt.

    Erstes Wort ab dieser Zeit, das auf ein Satzzeichen endet und keine
    Abkuerzung ist (STUDIO_ABKUERZUNGEN - sonst endete der Satz mitten in
    "U.S." oder "vs."). None, wenn bis zum Abschnittsende keins folgt."""
    for w in worte:
        if w.end < ab:
            continue
        blank = w.text.rstrip("\"'»«)]”").lower()
        if blank.endswith((".", "!", "?", "…")) \
                and blank not in STUDIO_ABKUERZUNGEN \
                and not re.fullmatch(r"[a-z]\.", blank):
            return w.end
    return None


def _punkt_zeiten(punkte: list[dict], worte: list[Wort], von: float,
                  bis: float) -> list[float]:
    """Erscheinungszeit je Stichpunkt: bevorzugt der Fundort seiner
    Anker-Phrase, Luecken werden gleichmaessig interpoliert, und die Folge
    bleibt monoton mit Mindestabstand."""
    roh: list[float | None] = [_anker_zeit(str(p.get("anker", "")), worte)
                               for p in punkte]
    if roh and roh[0] is None:
        roh[0] = von + 0.6  # erster Punkt frueh, mit dem ersten Satz
    for i, wert in enumerate(roh):
        if wert is not None:
            continue
        vor = von
        for j in range(i - 1, -1, -1):
            frueher = roh[j]
            if frueher is not None:
                vor = frueher
                break
        nach = max(bis - 2.0, vor)
        schritte = 2
        for j in range(i + 1, len(roh)):
            spaeter = roh[j]
            if spaeter is not None:
                nach, schritte = spaeter, j - (i - 1)
                break
        roh[i] = vor + (nach - vor) / max(1, schritte)
    aus: list[float] = []
    for wert in roh:
        t = wert if wert is not None else von
        if aus:
            t = max(t, aus[-1] + PUNKT_MIN_ABSTAND)
        aus.append(min(max(t, von), max(bis - 0.5, von)))
    return aus


LUECKE_MAX = 10.0  # laengste Stille einer Story-Strecke ohne neuen Stichpunkt,
                   # sonst Fallback-Bullet aus dem naechsten gesprochenen Satz -
                   # sonst blieben lange Redestrecken (Einzelwerte, Zitate ohne
                   # eigenen Stichpunkt) ohne jede Textstuetze im Bild
                   # (Nutzerfeedback 18.08.2026: fast eine Minute Geplapper
                   # ohne Text bei den Einzelwerten in "Memory stocks").
                   # War 16.0 bis 19.08.2026: die Pacing-Messung fand danach
                   # weiter 15-20s Stillstand (Bild UND Ton standen im
                   # Target-Fenster bei 80 wpm zusammen still), weil die
                   # Schwelle die Luecke zwischen Stichpunkt-ERSCHEINUNGS-
                   # zeiten misst, nicht die Standzeit des Fokus-Kastens.


def _detail_liste(punkt: dict) -> list[str]:
    """Die Stichwort-Fragmente eines Stichpunkts, wie szenen.detail_karte sie
    erwartet. Das Feld ist optional: Drehbuecher vor dem 19.08.2026 haben es
    nicht, und die Fallback-Bullets aus _luecken_fuellen tragen keins - beide
    liefern hier eine leere Liste und laufen unveraendert weiter."""
    roh = punkt.get("detail")
    if isinstance(roh, str):
        roh = [roh]
    if not isinstance(roh, list):
        return []
    return [str(s).strip() for s in roh if str(s).strip()]


# Woerter, die keinen Zeitbezug stiften: sie stehen in fast jedem Satz, ein
# Treffer auf ihnen zeigt das Fragment irgendwo statt dort, wo sein Inhalt
# gesprochen wird.
DETAIL_STOPP = frozenset("""
and are as at but by for from has have his her in into is it its no not of
on one or over per than that the their this to under was were with you your
about after all also any been being can could down had he how just like made
make more most new now only other out said say says she some such then there
these they up very what when which who will would
""".split())
DETAIL_FENSTER = 8       # so viele Woerter weit darf ein Fragment im
                         # gesprochenen Text auseinanderliegen und noch als
                         # eine Fundstelle gelten
DETAIL_SELTEN = 2        # ein einzelnes Wort taugt nur als Fundstelle, wenn
                         # es im Abschnitt hoechstens so oft faellt - sonst
                         # trifft es irgendeines seiner Vorkommen
DETAIL_VERSATZ = 0.7     # Mindestabstand zweier Fragment-Einblendungen: sie
                         # sollen nacheinander erscheinen, nicht gemeinsam


def _detail_tokens(fragment: str) -> list[str]:
    """Die Woerter eines Fragments, die einen Zeitbezug stiften koennen:
    ohne Fuellwoerter, und kurze nur, wenn sie Ziffern tragen ("22%", "5b")."""
    return [t for t in _norm_text(fragment).split()
            if t not in DETAIL_STOPP
            and (len(t) >= 3 or any(z.isdigit() for z in t))]


def _detail_fundort(fragment: str, worte: list[Wort]) -> float | None:
    """Wann im Wortstrom der Inhalt dieses Fragments gesprochen wird.

    Kein Folgenvergleich wie bei den Ankern (_anker_spanne): die Fragmente
    sind verdichtete Stichworte, "CAFC order 8-17-2026" steht im Text als "a
    CAFC order dated 8-17-2026". Gesucht wird deshalb die Stelle, an der die
    meisten Fragment-Woerter dicht beieinander fallen. Ein einzelnes Wort
    reicht nur, wenn es im Abschnitt selten ist. None, wenn nichts passt."""
    ziel = set(_detail_tokens(fragment))
    if not ziel:
        return None
    # Ein gesprochenes Wort kann mehrere Tokens tragen: "$12.50" wird zu
    # "12 50", "8-17-2026" zu "8 17 2026". Verglichen wird deshalb je Wort
    # eine Token-MENGE, nicht ein String - sonst faende ein Fragment mit
    # "$12.50" seine eigene Zahl nicht wieder.
    toks = [set(_norm_text(w.text).split()) for w in worte]
    treffer = [i for i, t in enumerate(toks) if t & ziel]
    if not treffer:
        return None
    bester: tuple[int, int] | None = None
    for i in treffer:
        fenster = {t for j in treffer if i <= j < i + DETAIL_FENSTER
                   for t in toks[j] & ziel}
        if bester is None or len(fenster) > bester[0]:
            bester = (len(fenster), i)
    assert bester is not None
    anzahl, start = bester
    if anzahl < 2:
        # Ein-Wort-Fundstelle: nur belastbar, wenn das Wort selten faellt.
        if len(treffer) > DETAIL_SELTEN:
            return None
    return worte[start].start


def _detail_zeiten(fragmente: list[str], worte: list[Wort], von: float,
                   bis: float) -> list[float]:
    """Einblendzeit je Fragment innerhalb der Standzeit des Fokus-Punkts.

    Bevorzugt der Fundort im gesprochenen Text, Luecken gleichmaessig
    dazwischen. Danach zwei Korrekturen, die den Fundort ueberstimmen
    duerfen: die Reihenfolge im Kasten steht fest (ein Fragment kann nicht
    ueber einem frueheren erscheinen), und jedes braucht seine Lesezeit vor
    dem Ende - das letzte zuerst, sonst blitzt es beim Abflug nur auf."""
    roh: list[float | None] = [_detail_fundort(f, worte) for f in fragmente]
    roh = [None if t is None or not von - 0.4 <= t <= bis else t for t in roh]
    for i, wert in enumerate(roh):
        if wert is not None:
            continue
        vor = von
        for j in range(i - 1, -1, -1):
            frueher = roh[j]
            if frueher is not None:
                vor = frueher
                break
        nach, schritte = bis, len(roh) - i + 1
        for j in range(i + 1, len(roh)):
            spaeter = roh[j]
            if spaeter is not None:
                nach, schritte = spaeter, j - i + 1
                break
        roh[i] = vor + (nach - vor) / max(1, schritte)
    zeiten = [max(von, t if t is not None else von) for t in roh]
    for i in range(1, len(zeiten)):      # Reihenfolge des Kastens erzwingen
        zeiten[i] = max(zeiten[i], zeiten[i - 1] + DETAIL_VERSATZ)
    rest = 0.0                           # Lesezeit von hinten freihalten
    for i in range(len(zeiten) - 1, -1, -1):
        rest += detail_frag_boden(fragmente[i])
        zeiten[i] = max(von, min(zeiten[i], bis - rest))
    return zeiten


# Woerter, auf denen ein gekappter Stichpunkt nie enden darf: sie kuendigen
# an, was gerade weggefallen ist ("... USD IN"), und lesen sich als Fehler.
BULLET_FUELLWORT = {
    "A", "AN", "AND", "AS", "AT", "BUT", "BY", "FOR", "FROM", "IN", "INTO",
    "IS", "ITS", "OF", "ON", "OR", "OVER", "PER", "THAN", "THAT", "THE",
    "THEIR", "THIS", "TO", "UNDER", "WITH",
    "I.E", "E.G",   # Einleitungen; der Schluss-Strip frisst ihnen den Punkt
}
BULLET_KLAUSEL = ",;:-–—"      # Satzzeichen, an denen ein Schnitt sauber liegt
BULLET_KLAUSEL_MIN = 0.6       # so viel des Platzes muss die Klausel fuellen
# Laengenziel, knapp ueber den 38 Zeichen der vom Modell verfassten Stichworte.
# Nicht die Kartenkapazitaet ausreizen: zwei volle Kartenzeilen fassen rund 80
# Zeichen, und ein 80-Zeichen-Prefix des gesprochenen Satzes ist ein
# eingebrannter Untertitel - genau das, was im Bild nicht stehen soll.
BULLET_MAX = 42


def _luecken_bullet(satz: str) -> str:
    """Kurzform eines gesprochenen Satzes als Fallback-Stichpunkt: Grossbuch-
    staben, gekappt auf das, was die Themen-Karte zeigen kann - derselbe Stil
    wie die vom Modell verfassten Stichworte, nur ohne redaktionelle
    Zuspitzung.

    Gekappt wird am Wort, bevorzugt an einer Klausel-Grenze; bleibt nur ein
    Schnitt mitten im Satzteil, endet der Punkt mit einer Auslassung statt auf
    einem Fuellwort. Laengenziel ist BULLET_MAX, die Kartenkapazitaet
    (szenen.karte_passt) nur die harte Grenze dahinter - sie auszureizen
    ergaebe Untertitel statt Stichpunkte."""
    text = re.sub(r"[\"“”«»]", "", satz)
    text = re.sub(r"^[-–—.,;:!?'…\s]+", "", text.strip())
    text = re.sub(r"[.,;:!?'…\s]+$", "", text).upper()
    if not text:
        return ""
    worte = text.split()

    def ohne_fuellwoerter(bis_wort: int) -> int:
        while bis_wort > 1 and \
                worte[bis_wort - 1].strip(BULLET_KLAUSEL) in BULLET_FUELLWORT:
            bis_wort -= 1
        return bis_wort

    if len(text) <= BULLET_MAX and szenen.karte_passt(text):
        # ganz drin - nur ein Fuellwort am Schluss verraet, dass schon der
        # Satz-Cue mitten im Satzteil endete; dann Auslassung statt Fuellwort
        voll = ohne_fuellwoerter(len(worte))
        if voll == len(worte):
            return text
        return " ".join(worte[:voll]).rstrip(BULLET_KLAUSEL + " ") + " …"
    # laengster Wort-Prefix innerhalb des Laengenziels
    n = 0
    while n < len(worte) and len(" ".join(worte[:n + 1])) <= BULLET_MAX:
        n += 1
    if n == 0:                          # ein einzelnes Wort sprengt das Ziel
        return szenen.karte_text(worte[0][:BULLET_MAX])
    # Klausel-Grenze im Prefix bevorzugen, solange sie den Platz gut fuellt
    grenze = ohne_fuellwoerter(max(
        (i for i in range(1, n + 1) if worte[i - 1][-1] in BULLET_KLAUSEL),
        default=0))
    if grenze >= max(1, round(n * BULLET_KLAUSEL_MIN)):
        return " ".join(worte[:grenze]).rstrip(BULLET_KLAUSEL + " ")
    # sonst: Fuellwoerter am Ende weg, Auslassung als Kappungsmarke anhaengen
    n = ohne_fuellwoerter(n)
    kurz = " ".join(worte[:n]).rstrip(BULLET_KLAUSEL + " ")
    while n > 1 and not szenen.karte_passt(f"{kurz} …"):
        n -= 1
        kurz = " ".join(worte[:n]).rstrip(BULLET_KLAUSEL + " ")
    return f"{kurz} …"


def _luecken_fuellen(stich: list[dict], zeiten: list[float],
                      gewaehlt: list[tuple[float, float, str, dict]],
                      worte: list[Wort], von: float, bis: float
                      ) -> tuple[list[dict], list[float]]:
    """Ergaenzt Stichpunkte um Fallback-Bullets aus den Satz-Cues der
    Vertonung, wo eine Story-Strecke (kein Zwischenthema/Zitat/Kennzahl)
    laenger als LUECKE_MAX ohne neuen Stichpunkt bliebe. Die Zeitpunkte
    stammen direkt aus den Wort-Zeitstempeln, nicht aus einer Anker-Suche -
    _punkt_zeiten muss vorher gelaufen sein, dies ist ein zweiter Durchgang
    obendrauf."""
    gedeckt = sorted({von, bis} | set(zeiten) |
                      {t for tz, ebis, _, _ in gewaehlt for t in (tz, ebis)})
    saetze = _satz_cues(worte)
    zusatz_zeit: list[float] = []
    zusatz_stich: list[dict] = []
    for a, b in zip(gedeckt, gedeckt[1:]):
        if b - a <= LUECKE_MAX:
            continue
        marke = a
        for cs, _, satz in saetze:
            if cs <= marke + LUECKE_MAX * 0.6 or cs >= b - 1.0:
                continue
            kurz = _luecken_bullet(satz)
            if not kurz:
                continue
            zusatz_zeit.append(cs)
            zusatz_stich.append({"text": kurz})
            marke = cs
    if not zusatz_zeit:
        return stich, zeiten
    kombi = sorted(zip(zeiten + zusatz_zeit, stich + zusatz_stich),
                    key=lambda p: p[0])
    aus_zeit: list[float] = []
    aus_stich: list[dict] = []
    for t, p in kombi:
        if aus_zeit:
            t = max(t, aus_zeit[-1] + PUNKT_MIN_ABSTAND)
        aus_zeit.append(t)
        aus_stich.append(p)
    return aus_stich, aus_zeit


def folien_konkat(bloecke: list[Block], block_worte: list[list[Wort]],
                  abschnitte: list[Abschnitt], zuordnung: dict[int, dict],
                  fdaten: dict, hook: str, datum: str, arbeit: Path,
                  suffix: str, ende: float) -> Path:
    """Alle Folien-Zustaende rendern und als zeitgesteuerte ffconcat-Liste
    schreiben. Jeder Zustand (Reveal, Blend-Zwischenbild, Folie mit n
    sichtbaren Stichpunkten, ...) ist ein eigenes Standbild; die Startzeiten
    kommen aus den Wort-Zeitstempeln der zugehoerigen Bloecke."""
    zuteilung = motiv_zuordnung(datum)
    werte = motiv_werte(datum)
    motive = sorted(MOTIV_DIR.glob(f"{datum}.*"))
    tages_motiv = motive[0] if motive else None
    # Pool = alle freigegebenen Tagesbilder, die staerksten Motive zuerst.
    # `verwendet` haelt fest, was schon eine Folie traegt - jede Folie soll
    # ein frisches Bild bekommen, solange der Tag welche hergibt.
    pool: list[Path] = sorted(
        {p for pfade in zuteilung.values() for p in pfade},
        key=lambda p: (-_bild_rang(werte, p.name), p.name))
    pool_i = 0
    verwendet: set[Path] = set()

    def pool_bild(nur_frisch: bool = False) -> Path | None:
        """Naechstes Pool-Bild, bevorzugt eines, das noch auf keiner Folie
        war; sind alle durch, geht es reihum weiter (ausser nur_frisch)."""
        nonlocal pool_i
        if not pool:
            return None if nur_frisch else tages_motiv
        for k in range(len(pool)):
            p = pool[(pool_i + k) % len(pool)]
            if p not in verwendet:
                pool_i = (pool_i + k + 1) % len(pool)
                verwendet.add(p)
                return p
        if nur_frisch:
            return None
        pool_i += 1
        return pool[(pool_i - 1) % len(pool)]

    def eigenes_bild(eigene: list[Path]) -> Path | None:
        """Erstes noch nicht gezeigtes eigenes Bild des Abschnitts. Reine
        Textwaende bekommen diesen Heimvorteil nicht - sie kommen erst zum
        Zug, wenn der Tagespool kein frisches Motiv mehr hergibt."""
        for p in eigene:
            if _ist_textwand(werte, p.name):
                continue
            if p not in verwendet:
                verwendet.add(p)
                return p
        return None

    nr_bild = 0
    ereignisse: list[tuple[Path, float]] = []

    def zeigen(bild, zeit: float) -> Path:
        nonlocal nr_bild
        pfad = folien.speichern(bild, arbeit / f"folie{suffix}_{nr_bild:03d}.jpg")
        nr_bild += 1
        ereignisse.append((pfad, zeit))
        return pfad

    def start_von(index: int) -> float:
        return block_worte[index][0].start if block_worte[index] else 0.0

    # Rollen-Bloecke einsammeln (Reihenfolge ist die der Erzeugung)
    agenda_idx = [i for i, b in enumerate(bloecke) if b.rolle == "agenda"]
    zahl_idx = [i for i, b in enumerate(bloecke) if b.rolle == "zahl"]
    eintraege = [bloecke[i].text.rstrip(".") for i in agenda_idx]

    # Kapitel und ihre Motive VOR Intro/Agenda bestimmen: die Agenda zeigt
    # beim Aufleuchten eines Eintrags das Motiv des zugehoerigen Kapitels
    # als Vorschau und verbraucht so selbst keine frischen Bilder.
    koepfe = [(i, b.abschnitt) for i, b in enumerate(bloecke)
              if b.art == "ueberschrift" and not b.rolle]
    kapitel_eigene: list[list[Path]] = []
    kapitel_motive: list[Path | None] = []
    for _, nr in koepfe:
        # Frisches eigenes Bild vor frischem Pool-Bild vor Wiederholung -
        # mehrere Abschnitte desselben Threads teilen sich so kein Motiv mehr.
        eigene = [p for tid in abschnitte[nr].threads
                  for p in zuteilung.get(tid, [])]
        kapitel_eigene.append(eigene)
        kapitel_motive.append(eigenes_bild(eigene)
                              or pool_bild(nur_frisch=True)
                              or (eigene[0] if eigene else pool_bild()))
    titel_map = thread_titel(datum)

    # Intro und Agenda
    intro_motiv = tages_motiv or pool_bild()
    zeigen(folien.intro(hook, datum, intro_motiv), 0.0)
    agenda_motiv = pool_bild(nur_frisch=True) or tages_motiv
    kopf_idx = next((i for i, b in enumerate(bloecke)
                     if b.rolle == "agenda_kopf"), None)
    if kopf_idx is not None:
        zeigen(folien.agenda(eintraege, -1, datum, agenda_motiv),
               start_von(kopf_idx))
    for k, i in enumerate(agenda_idx):
        m = kapitel_motive[k] if k < len(kapitel_motive) else None
        zeigen(folien.agenda(eintraege, k, datum, m or agenda_motiv),
               start_von(i))

    # Zahlen des Tages: seit 20.08.2026 als TL;DR direkt nach dem Cold Open
    # (vorne), bei einer Blockliste alter Ordnung wie frueher vor dem Outro.
    # Die Ereignisliste muss chronologisch bleiben (die ffconcat-Zeiten
    # unten werden monoton geklemmt), deshalb entscheidet die Blockfolge,
    # wo dieser Aufruf faellt.
    karten = [k for k in fdaten.get("zahlen") or []
              if isinstance(k, dict) and k.get("wert")][:4]
    zk_idx = next((i for i, b in enumerate(bloecke) if b.rolle == "zahl_kopf"),
                  None)
    zahlen_motiv: Path | None = None

    def zahlen_folien() -> None:
        nonlocal zahlen_motiv
        zahlen_motiv = pool_bild()
        if zk_idx is not None and karten:
            zeigen(folien.zahlen(karten, 0, datum, zahlen_motiv),
                   start_von(zk_idx))
            genutzt = zahl_idx[:len(karten)]
            for j, i in enumerate(genutzt):
                # Beim letzten gesprochenen Zahlensatz klappen die restlichen
                # Karten mit auf: gesprochen werden seit 21.08.2026 nur
                # ZAHLEN_GESPROCHEN, im Bild stehen weiterhin alle.
                sichtbar = len(karten) if j + 1 == len(genutzt) else j + 1
                zeigen(folien.zahlen(karten, sichtbar, datum, zahlen_motiv),
                       start_von(i))

    vorne = zahlen_vorne(bloecke)
    if vorne:
        zahlen_folien()

    # Abschnitte: Reveal (Ueberschrift-Sprechzeit) -> Blend -> Stichpunkte.
    # Der Index-Filter schuetzt davor, den vorgezogenen TL;DR-Block als
    # Kapitel-Schluss zu treffen.
    letzter_kopf = koepfe[-1][0] if koepfe else -1
    schluss = next((start_von(i) for i, b in enumerate(bloecke)
                    if i > letzter_kopf
                    and b.rolle in SCHLUSS_ROLLEN and block_worte[i]),
                   ende)
    for k, (kopf, nr) in enumerate(koepfe):
        kopf_start = start_von(kopf)
        naechster = start_von(koepfe[k + 1][0]) if k + 1 < len(koepfe) else schluss
        rumpf_idx = [i for i, b in enumerate(bloecke)
                     if b.abschnitt == nr and not b.rolle
                     and b.art != "ueberschrift"]
        rumpf_worte = [w for i in rumpf_idx for w in block_worte[i]]
        rumpf_start = rumpf_worte[0].start if rumpf_worte else kopf_start + 2.0

        eintrag = zuordnung.get(nr, {})
        titel = _folien_titel(zuordnung, bloecke, nr) or bloecke[kopf].text
        punkte = [p for p in eintrag.get("punkte") or []
                  if isinstance(p, dict) and p.get("text")]
        karte = eintrag.get("karte") if isinstance(eintrag.get("karte"), dict) \
            else None
        eigene = kapitel_eigene[k]
        motiv = kapitel_motive[k]
        # Fusszeile: Thread-Titel statt nackter Nummer (Nummer nur, wenn die
        # Extrakt-Seite fehlt); die Fusszeile ist klein, also kappen.
        quelle = (titel_map.get(abschnitte[nr].threads[0])
                  or f"thread {abschnitte[nr].threads[0]}") \
            if abschnitte[nr].threads else ""
        if len(quelle) > 60:
            quelle = quelle[:59].rstrip() + "…"
        fuss = (f"Source: {quelle}  ·  " if quelle else "") + \
               f"Chapter {k + 1} of {len(koepfe)}"

        def folie(sichtbar: int, aktiv: int, m: Path | None):
            return folien.thema(titel, [str(p["text"]) for p in punkte],
                                sichtbar, aktiv, karte, fuss, datum, m)

        eigen_i = 0

        def punkt_motiv(aktuell: Path | None) -> Path | None:
            """Motivwechsel beim Aufleuchten eines Stichpunkts: frisches
            eigenes Thread-Bild vor frischem Pool-Bild vor Rotation durch die
            eigenen; gibt es nichts anderes, bleibt das aktuelle stehen. Die
            Rotation kommt erst nach dem Pool, weil in ihr auch die
            zurueckgestellten Textwaende des Threads stecken."""
            nonlocal eigen_i
            p = eigenes_bild(eigene) or pool_bild(nur_frisch=True)
            if p is not None:
                return p
            # Ist der Tagespool durch, wird wiederholt - dann lieber ein
            # Motiv zweimal als eine Textwand einmal.
            wieder = [p for p in eigene
                      if not _ist_textwand(werte, p.name)] or eigene
            if len(wieder) >= 2:
                for _ in range(len(wieder)):
                    kandidat = wieder[eigen_i % len(wieder)]
                    eigen_i += 1
                    if kandidat != aktuell:
                        return kandidat
            return aktuell

        if motiv is not None:
            reveal_bild = folien.reveal(titel, datum, motiv)
            zeigen(reveal_bild, kopf_start)
            blend_start = max(kopf_start + 0.4,
                              rumpf_start - BLEND_SCHRITTE * BLEND_DAUER)
            for s, zw in enumerate(folien.blend(reveal_bild,
                                                folie(0, -1, motiv),
                                                BLEND_SCHRITTE)):
                zeigen(zw, blend_start + s * BLEND_DAUER)
        zeigen(folie(0, -1, motiv), rumpf_start)
        zeiten = _punkt_zeiten(punkte, rumpf_worte, rumpf_start, naechster)
        akt = motiv
        for j, t in enumerate(zeiten):
            akt = punkt_motiv(akt)
            zeigen(folie(j + 1, j, akt), t)

    # Zahlen des Tages (nur bei alter Ordnung noch hier) und Outro
    if not vorne:
        zahlen_folien()
    outro_idx = next((i for i, b in enumerate(bloecke) if b.rolle == "outro"),
                     None)
    if outro_idx is not None:
        zeigen(folien.outro(datum, tages_motiv or zahlen_motiv), start_von(outro_idx))

    # Ereignisse in eine ffconcat-Liste uebersetzen: streng monoton steigend,
    # jede Folie steht bis zum Start der naechsten.
    zeiten_liste: list[float] = []
    for _, t in ereignisse:
        zeiten_liste.append(max(t, (zeiten_liste[-1] + 1 / FPS)
                                if zeiten_liste else 0.0))
    zeilen = ["ffconcat version 1.0"]
    for k, (pfad, _) in enumerate(ereignisse):
        bis = zeiten_liste[k + 1] if k + 1 < len(zeiten_liste) \
            else max(ende, zeiten_liste[k] + 1.0)
        p = str(pfad).replace("\\", "/")
        zeilen += [f"file '{p}'", f"duration {bis - zeiten_liste[k]:.3f}"]
    zeilen.append(zeilen[-2])  # concat-Eigenheit: letzte duration braucht Echo
    liste = arbeit / f"folien{suffix}.ffconcat"
    liste.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print(f"Praesentation: {nr_bild} Folienbilder, {len(koepfe)} Kapitel")
    return liste


# ------------------------------------------------- Szenen-Praesentation (v7)

ZOOM_HUB = 0.10          # Zoomweg je Szene: 10 % rein oder raus, kaum merklich
STORY_MAX = 20.0         # spaetestens dann wechselt die Story-Szene das Motiv
OPENER_MIN = 4.0         # Mindest-Standzeit des Kapitel-Openers: kurze
                         # Ueberschriften ("BOARD LIFE") sind in unter einer
                         # Sekunde gesprochen, der Titel muss trotzdem lesbar
                         # stehen (Nutzerfeedback 17.08.)
OPENER_QUELLE_MIN = 6.0  # mit Quellzeile ist der Opener 84-119 Zeichen lang
                         # (22-31 cps gemessen 19.08.2026, die Quellzeile fiel
                         # faktisch weg). Er darf ohnehin bis naechster-0.5
                         # laufen; der Preis sind spaeter einsetzende
                         # Detail-Kaesten beim ersten Stichpunkt (det_von)
ZITAT_MAX = 12.0         # Hoechstdauer der Zitat-Szene
ZITAT_NACHLAUF = 1.5     # so lange steht die Karte noch, nachdem der zitierte
                         # Satz zu Ende gesprochen ist
ZITAT_MIN = 4.0          # Lesezeit-Boden: kuerzer als das darf keine Karte
                         # stehen, auch wenn ihr Satz frueher endet
STORY_REST_MIN = 2.5     # kuerzere Story-Reststuecke ziehen kein frisches
                         # Motiv, sondern laufen auf dem der Vorszene weiter;
                         # SZENE_MIN_FRAMES ist nur ein technischer Boden,
                         # dies der gestalterische
ZWISCHEN_MAX = 6.0       # Hoechstdauer eines Zwischenthema-Openers
KARTE_MAX = 9.0          # Hoechstdauer der Kennzahl-Szene im Kapitel
EREIGNIS_ABSTAND = 4.0   # Ruhe zwischen zwei Sonderszenen
SZENE_MIN_FRAMES = 8     # kuerzer darf keine Szene sein (0,32 s)
COUNTUP_TAKT = 0.16      # Standzeit je Count-up-Stufe


@dataclass
class Overlay:
    png: Path
    start: float          # Sekunden, global; wird beim Rendern relativiert
    ende: float
    fade: float = 0.35    # 0.0 = harter Schnitt (Count-up-Stufen)
    x: int = 0            # Lage im 1280x720-Raster (szenen.speichern schneidet zu)
    y: int = 0
    einflug: str = ""     # "", "links", "rechts", "unten": Richtung, aus der
                          # die Karte hereinfaehrt (nur beim ersten Erscheinen)
    ausblenden: bool = False   # setzt nur der Renderer: Overlay endet in
                               # dieser Szene und darf weich weggehen
    einblenden: bool = True    # setzt nur der Renderer: Overlay beginnt in
                               # dieser Szene (sonst laeuft es weiter und
                               # darf an der Naht nicht neu aufblenden)
    weiter: bool = False       # dieses Stueck ist an einer Szenengrenze
                               # abgeschnitten und laeuft dort weiter: es darf
                               # an der Naht nicht ausblenden
    flug_ab: float | None = None   # ab dieser Zeit fliegt das Overlay nach
    flug_x: int = 0                # (flug_x, flug_y) und verblasst dabei -
    flug_y: int = 0                # so parkt ein Fokus-Punkt in der Karte


@dataclass
class Szene:
    motiv: Path | None
    start: float          # globaler Start; das Ende ist der Start der naechsten
    zoom_rein: bool = True
    overlays: list[Overlay] = field(default_factory=list)
    motiv_animiert: bool = False   # motiv ist eine echte bewegte Kulisse
                                    # (GIF/WebM/MP4), kein Standbild
    motiv_poster: Path | None = None   # Standbild dazu - fuer den Crossfade
                                        # der Folgeszene und als Fallback,
                                        # falls der animierte Renderpfad
                                        # scheitert


@dataclass
class KartenStand:
    """Ein stehendes Overlay mit Zeitfenster: ein Stand der Themen-Karte
    (derselbe Kasten mit einem geparkten Stichpunkt mehr) oder der
    Themen-Titel oben, der ein ganzes Segment lang steht. Bewusst eine
    Dataclass und kein Tupel - beim Entpacken eines Tupels ist in dieser
    Funktion schon einmal ein Name kollidiert."""
    png: Path
    x: int
    y: int
    von: float
    bis: float
    einflug: str = ""
    blende: float = 0.3       # Aufblendzeit; 0.0 = harter Schnitt
    haelt: bool = False       # am Ende nicht ausblenden, weil eine
                              # Folgestufe desselben Kastens uebernimmt


@dataclass
class FokusKarte:
    """Der Stichpunkt, ueber den gerade gesprochen wird: gross in der freien
    Bildhaelfte, ab flug_ab auf dem Weg an seinen Platz in der Themen-Karte
    (ziel_x/ziel_y sind die Ecke des zugeschnittenen Overlays am Ziel)."""
    png: Path
    x: int
    y: int
    von: float
    bis: float
    flug_ab: float | None     # None: der Punkt parkt ohne Flug (harter Schnitt)
    ziel_x: int
    ziel_y: int


def _post_datum(datum: str) -> str:
    """2026-08-16 -> 08/16/26 (Datumsstil der 4chan-Post-Kopfzeile)."""
    j, m, t = datum.split("-")
    return f"{m}/{t}/{j[2:]}"


def szenen_bauen(bloecke: list[Block], block_worte: list[list[Wort]],
                 abschnitte: list[Abschnitt], zuordnung: dict[int, dict],
                 fdaten: dict, hook: str, datum: str, arbeit: Path,
                 ende: float, thumb: str = "",
                 sprech_ende: float = 0.0,
                 nur_video: bool = False) -> list[Szene]:
    """Drehbuch (folien.json v2) + Wort-Zeitstempel -> Szenenfolge.
    Jede Szene traegt ein vollflaechiges Motiv; Kapitel-Opener, der Themen-Titel oben, die persistente
    Karte mit den geparkten Stichpunkten darunter (beide stehen bis zum
    Themen- oder Zwischenthemen-Wechsel), der gerade besprochene Stichpunkt
    als Fokus-Karte in der freien Bildhaelfte, Zitat-Karten und Kennzahlen
    liegen als zeitlich verankerte Overlays darauf - keine Sprechsekunde
    ohne Text im Bild. Die Motiv-Auswahl folgt der v6-Logik: frisches
    eigenes Thread-Bild vor frischem Pool-Bild vor Wiederholung
    (siehe MotivWahl - shorts.py rechnet damit dieselbe Zuordnung)."""
    wahl = MotivWahl(datum)
    werte = wahl.werte
    typen = motiv_typen(datum)
    poster_pfade = motiv_poster_pfade(datum)
    tages_motiv = wahl.tages_motiv
    pool_bild = wahl.pool_bild
    eigenes_bild = wahl.eigenes_bild

    ov_nr = 0
    # [geplant, weggefallen] der Stichwort-Fragmente: seit die Lesezeit-Boeden
    # hoeher liegen (19.08.2026), muss im Log stehen, wie viele Fragmente die
    # Fenster-Pruefung von hinten wegkuerzt - frisst sie das Feature auf,
    # gehoeren die Boeden zurueckgenommen, nicht die Fragmente.
    frag_stat = [0, 0]

    def png(bild) -> tuple[Path, int, int]:
        nonlocal ov_nr
        lage = szenen.speichern(bild, arbeit / f"overlay_{ov_nr:03d}.png")
        ov_nr += 1
        return lage

    def ov(bild, start: float, bis: float, fade: float = 0.35,
           einflug: str = "") -> Overlay:
        pfad, x, y = png(bild)
        return Overlay(pfad, start, bis, fade, x, y, einflug)

    folge: list[Szene] = []

    def neu(motiv: Path | None, start: float) -> Szene:
        poster: Path | None
        if motiv is not None and motiv in klip_poster:
            # ein zugeteilter WebM/MP4-Clip (siehe _klip_zuordnung), kein
            # Bild-Motiv aus motive.json - eigener Poster-Weg statt typen/
            # poster_pfade, die nur die Bild-Kulisse kennen.
            animiert, poster = True, klip_poster[motiv]
        else:
            animiert = motiv is not None and typen.get(motiv.name) == "animiert"
            poster = poster_pfade.get(motiv.name) if motiv is not None else None
        s = Szene(motiv, start, zoom_rein=len(folge) % 2 == 0,
                  motiv_animiert=animiert, motiv_poster=poster)
        folge.append(s)
        return s

    def start_von(index: int) -> float:
        return block_worte[index][0].start if block_worte[index] else 0.0

    agenda_idx = [i for i, b in enumerate(bloecke) if b.rolle == "agenda"]
    zahl_idx = [i for i, b in enumerate(bloecke) if b.rolle == "zahl"]
    eintraege = [bloecke[i].text.rstrip(".") for i in agenda_idx]
    koepfe = [(i, b.abschnitt) for i, b in enumerate(bloecke)
              if b.art == "ueberschrift" and not b.rolle]

    # Kapitel-Motive vorab reservieren (die Agenda-Vorschau nutzt sie mit,
    # ohne selbst frische Bilder zu verbrauchen - wie in v6).
    kapitel_eigene, kapitel_motive = wahl.kapitel_reservieren(
        abschnitte, [nr for _, nr in koepfe])
    titel_map = thread_titel(datum)

    # Freigegebene WebM/MP4-Clips inhaltlich auf Abschnitte verteilen (siehe
    # _klip_zuordnung) - eine Ergaenzung zur Bild-Kulisse, kein Ersatz: die
    # meisten Abschnitte bleiben ohne Clip. Das Posterframe entsteht nur fuer
    # tatsaechlich zugeteilte Clips, nicht fuer den ganzen Katalog.
    klip_zuordnung = _klip_zuordnung(datum, abschnitte, titel_map, nur_video)
    klip_poster: dict[Path, Path] = {}
    for pfad in klip_zuordnung.values():
        try:
            klip_poster[pfad] = _klip_poster(pfad, arbeit)
        except Exception as e:
            print(f"WARNUNG: Clip-Poster fuer {pfad.name} fehlgeschlagen "
                 f"({e}) - Clip wird nicht verwendet")
    klip_zuordnung = {nr: p for nr, p in klip_zuordnung.items()
                      if p in klip_poster}
    if klip_zuordnung:
        print("Clip-Zuordnung: " + ", ".join(
            ("Intro" if nr == INTRO_KLIP_KEY else f"Kapitel {nr}")
            + f" -> {p.name}" for nr, p in klip_zuordnung.items()))

    # Intro. Kaltstart: in Sekunde 0 steht gross das Schlagwort des Tages im
    # Bild - dasselbe, das das Vorschaubild traegt. Damit loest das Video den
    # Klick auch im Bild ein und nicht nur im gesprochenen Hook; YouTube
    # bewertet die ersten 30 s als eigene Kennzahl. Bewusst ohne Aufblende
    # (fade=0): ein Cold Open, der einblendet, ist keiner.
    kopf_idx = next((i for i, b in enumerate(bloecke)
                     if b.rolle == "agenda_kopf"), None)
    zk_idx = next((i for i, b in enumerate(bloecke) if b.rolle == "zahl_kopf"),
                  None)
    outro_idx = next((i for i, b in enumerate(bloecke) if b.rolle == "outro"),
                     None)
    vorne = zahlen_vorne(bloecke)
    erster_kopf = start_von(koepfe[0][0]) if koepfe else ende
    # Nach dem Cold Open kommt seit 20.08.2026 der TL;DR-Zahlenblock; nur im
    # Agenda-Fallback (keine Zahlen im Drehbuch) steht dort die Agenda.
    intro_bis = (start_von(kopf_idx) if kopf_idx is not None
                 else start_von(zk_idx) if vorne and zk_idx is not None
                 else erster_kopf)
    s = neu(klip_zuordnung.get(INTRO_KLIP_KEY) or tages_motiv or pool_bild(),
           0.0)
    hook_ab = 0.4
    if thumb and intro_bis > KALTSTART_MIN + 1.0:
        # Das Schlagwort soll KALTSTART lange stehen (2.0s waren ein
        # Aufblitzen, Nutzer-Feedback 19.08.2026), aber nicht auf Kosten
        # der Hook-Karte: die braucht ihre Lesezeit vor intro_bis. Weil der
        # Hook woertlich mitgesprochen wird, gilt fuer ihn die
        # Untertitel-Norm (HOOK_CPS) statt des Nebenher-Lesetempos.
        hook_ab = min(KALTSTART,
                      max(KALTSTART_MIN,
                          intro_bis - (HOOK_VORLAUF + len(hook) / HOOK_CPS)))
        s.overlays.append(ov(szenen.zahl_tafel(thumb, "", ""), 0.0,
                             hook_ab, fade=0.0))
    s.overlays.append(ov(szenen.titel_karte(hook, label="TODAY'S TOP STORY"),
                         hook_ab, max(intro_bis, hook_ab + 0.6),
                         einflug="unten"))

    # Agenda als "Coming up"-Strecke: je Eintrag eine Mini-Szene mit dem
    # Motiv seines Kapitels als Vorschau.
    if kopf_idx is not None and agenda_idx:
        t0 = start_von(kopf_idx)
        s = neu(pool_bild(nur_frisch=True) or tages_motiv, t0)
        s.overlays.append(ov(szenen.titel_karte("Coming up today",
                                                label="AGENDA"),
                             t0 + 0.2, start_von(agenda_idx[0]),
                             einflug="unten"))
        for k, i in enumerate(agenda_idx):
            t = start_von(i)
            bis = start_von(agenda_idx[k + 1]) if k + 1 < len(agenda_idx) \
                else erster_kopf
            m = kapitel_motive[k] if k < len(kapitel_motive) else None
            s = neu(m or tages_motiv, t)
            s.overlays.append(ov(
                szenen.titel_karte(eintraege[k],
                                   label=f"COMING UP · {k + 1:02d}",
                                   gross=False),
                t + 0.15, bis, einflug="unten"))

    # Zahlen des Tages: je Kennzahl eine eigene Gross-Zahl-Szene mit
    # Count-up. Als TL;DR direkt nach dem Cold Open (vorne) oder - bei einer
    # Blockliste alter Ordnung - vor dem Outro; die Szenenliste muss
    # chronologisch bleiben (szenen_video haengt die Kanten an s.start auf),
    # deshalb entscheidet die Blockfolge, wo dieser Aufruf faellt.
    karten = [z for z in fdaten.get("zahlen") or []
              if isinstance(z, dict) and z.get("wert")][:4]

    def zahlen_szenen(zahl_schluss: float, kopf_titel: str,
                      kopf_label: str) -> None:
        if zk_idx is None or not karten:
            return
        t0 = start_von(zk_idx)
        z = neu(pool_bild(), t0)
        z.overlays.append(ov(szenen.titel_karte(kopf_titel, label=kopf_label),
                             t0 + 0.2,
                             start_von(zahl_idx[0]) if zahl_idx else t0 + 4.0,
                             einflug="unten"))
        genutzt = zahl_idx[:len(karten)]
        for j, i in enumerate(genutzt):
            t = start_von(i)
            bis = start_von(genutzt[j + 1]) if j + 1 < len(genutzt) \
                else zahl_schluss
            z = neu(pool_bild(), t)
            # Das letzte Sprechfenster teilt sich, sobald Karten uebrig sind,
            # die nicht mehr vorgelesen werden (ZAHLEN_GESPROCHEN < 4): erst
            # laeuft der Count-up der gesprochenen Zahl, danach steht die
            # stille Uebersicht mit allen vieren. So kostet keine der
            # ungesprochenen Zahlen Vorspannzeit und trotzdem hat der
            # Zuschauer sie alle gesehen.
            rest = len(karten) - len(genutzt)
            if j + 1 == len(genutzt) and rest > 0 \
                    and bis - t >= ZAHL_COUNTUP_MIN + ZAHL_UEBERSICHT_MIN:
                schnitt = bis - ZAHL_UEBERSICHT_MIN
                _countup_overlays(z, karten[j], t + 0.2, schnitt, ov)
                z.overlays.append(ov(szenen.zahlen_uebersicht(karten),
                                     schnitt, bis, einflug="unten"))
                print(f"TL;DR: {len(genutzt)} von {len(karten)} Zahlen "
                      f"gesprochen, alle vier im Bild "
                      f"({ZAHL_UEBERSICHT_MIN:.1f}s Uebersicht)")
            else:
                _countup_overlays(z, karten[j], t + 0.2, bis, ov)
                if j + 1 == len(genutzt) and rest > 0:
                    print(f"TL;DR: Fenster zu kurz ({bis - t:.1f}s) - "
                          f"{rest} Zahl(en) nur als Karte, keine Uebersicht")

    if vorne:
        # Karte und Ansage sagen dasselbe: der gesprochene Kopf ist
        # PRAES_ZAHLEN.
        zahlen_szenen(erster_kopf, ZAHLEN_LABEL, "TL;DR")

    # Kapitel. Das Ende des letzten Kapitels ist der erste Rahmen-Block NACH
    # den Kapiteln (Outro; bei alter Ordnung der Zahlen-Kopf) - der
    # Index-Filter schuetzt davor, den vorgezogenen TL;DR-Block zu treffen.
    letzter_kopf = koepfe[-1][0] if koepfe else -1
    schluss = next((start_von(i) for i, b in enumerate(bloecke)
                    if i > letzter_kopf
                    and b.rolle in SCHLUSS_ROLLEN and block_worte[i]),
                   ende)
    for k, (kopf, nr) in enumerate(koepfe):
        kopf_start = start_von(kopf)
        naechster = start_von(koepfe[k + 1][0]) if k + 1 < len(koepfe) \
            else schluss
        rumpf_idx = [i for i, b in enumerate(bloecke)
                     if b.abschnitt == nr and not b.rolle
                     and b.art != "ueberschrift"]
        rumpf_worte = [w for i in rumpf_idx for w in block_worte[i]]
        rumpf_start = rumpf_worte[0].start if rumpf_worte else kopf_start + 2.0

        eintrag = zuordnung.get(nr, {})
        titel = _folien_titel(zuordnung, bloecke, nr) or bloecke[kopf].text
        eigene = kapitel_eigene[k]
        quelle = (titel_map.get(abschnitte[nr].threads[0])
                  or f"thread {abschnitte[nr].threads[0]}") \
            if abschnitte[nr].threads else ""
        if len(quelle) > 60:
            quelle = quelle[:59].rstrip() + "…"

        eigen_i = 0

        def naechstes_motiv(aktuell: Path | None) -> Path | None:
            """Frisches eigenes Thread-Bild vor frischem Pool-Bild vor
            Rotation durch die eigenen (in ihr stecken auch die
            zurueckgestellten Textwaende)."""
            nonlocal eigen_i
            p = eigenes_bild(eigene) or pool_bild(nur_frisch=True)
            if p is not None:
                return p
            # Ein zugeteilter Videoclip (siehe _klip_zuordnung) darf hier nie
            # wiederholt werden: ohne diese Sperre lieferte der Fallback
            # unten bei knappem Kapitel-Pool denselben bewegten Clip fuer
            # jede weitere Story-Szene des Kapitels zurueck - anders als ein
            # zweimal gezeigtes Standbild faellt das sofort unangenehm auf
            # (Nutzer-Feedback 18.08.2026: Clip 10x am Berichtsende
            # wiederholt, "0 Relevanz und 0 Unterhaltungswert").
            if aktuell is not None and aktuell in klip_poster:
                return pool_bild() or tages_motiv
            # Ist der Tagespool durch, wird wiederholt - dann lieber ein
            # Motiv zweimal als eine Textwand einmal.
            wieder = [p for p in eigene
                      if not _ist_textwand(werte, p.name)] or eigene
            if len(wieder) >= 2:
                for _ in range(len(wieder)):
                    kandidat = wieder[eigen_i % len(wieder)]
                    eigen_i += 1
                    if kandidat != aktuell:
                        return kandidat
            return aktuell

        # Opener: Kapiteltitel als Lower Third, solange die Ueberschrift
        # gesprochen wird; die Szene laeuft danach als erste Story weiter.
        # Ein zugeteilter Clip (siehe _klip_zuordnung) ersetzt hier bewusst
        # nur das Opener-Motiv dieses einen Abschnitts, nicht dessen ganze
        # Bild-Kulisse - Clips sind eine Ergaenzung, kein Ersatz.
        akt = klip_zuordnung.get(nr, kapitel_motive[k])
        kapitel_szene = neu(akt, kopf_start)
        opener_bis = min(
            max(rumpf_start,
                kopf_start + (OPENER_QUELLE_MIN if quelle else OPENER_MIN)),
            naechster - 0.5)
        # Tempo-Badge am Kapitelzaehler: seit 21.08.2026 ersetzt er den
        # frueheren eigenen Abschnitt "FILLING FAST". Dass ein Thread
        # schnell fuellt, ist kein Thema, sondern eine Eigenschaft des
        # Themas - also gehoert es an dessen Kapitel, nicht in eine eigene
        # Strecke am Videoende.
        tempo = str(eintrag.get("tempo") or "").strip()
        label = f"CHAPTER {k + 1:02d} / {len(koepfe)}"
        kapitel_szene.overlays.append(ov(
            szenen.titel_karte(titel,
                               label=f"{label}  ·  {tempo}" if tempo else label,
                               quelle=f"Source: {quelle}" if quelle else ""),
            kopf_start + 0.2, opener_bis, einflug="unten"))

        # Sonderereignisse des Drehbuchs im Kapitelrumpf verorten
        # Der vierte Eintrag ist das natuerliche Ende: die Zeit, zu der der
        # zugehoerige gesprochene Inhalt vorbei ist. None = keins bekannt,
        # dann gilt allein die Hoechstdauer der Szenenart.
        ereignisse: list[tuple[float, str, dict, float | None]] = []
        for zt in eintrag.get("zwischenthemen") or []:
            if isinstance(zt, dict) and str(zt.get("titel") or "").strip():
                tz = _anker_zeit(str(zt.get("anker") or ""), rumpf_worte)
                if tz is not None and rumpf_start + 2.0 < tz < naechster - 3.0:
                    ereignisse.append((tz, "zwischen", zt, None))
        zit = eintrag.get("zitat")
        if isinstance(zit, dict) and str(zit.get("text") or "").strip():
            sp = _anker_spanne(str(zit.get("anker") or ""), rumpf_worte)
            if sp is None:  # das Zitat selbst steht oft woertlich im Bericht
                sp = _anker_spanne(str(zit["text"]), rumpf_worte)
            if sp is not None and sp[0] < naechster - 3.0:
                # Die Karte gehoert zu ihrem Satz und geht mit ihm. Ohne diese
                # Bindung stand sie starre ZITAT_MAX=12s im Bild, waehrend der
                # Ton laengst beim naechsten Thema war (Nutzer-Feedback
                # 19.08.2026: XOM-Zitat bei 10:31, gesprochen rund 4s).
                natur = (_satz_ende(rumpf_worte, sp[1]) or sp[1]) \
                    + ZITAT_NACHLAUF
                ereignisse.append((max(sp[0], rumpf_start + 1.0), "zitat",
                                   zit, max(natur, sp[0] + ZITAT_MIN)))
        kar = eintrag.get("karte")
        if isinstance(kar, dict) and str(kar.get("wert") or "").strip():
            tz = _anker_zeit(str(kar.get("anker") or ""), rumpf_worte)
            if tz is None:
                tz = rumpf_start + (naechster - rumpf_start) * 0.6
            if tz < naechster - 3.0:
                ereignisse.append((max(tz, rumpf_start + 1.0), "karte", kar,
                                   None))
        ereignisse.sort(key=lambda e: e[0])
        gewaehlt: list[tuple[float, float, str, dict]] = []
        frei = opener_bis  # keine Sonderszene, solange der Opener steht
        for ez, art, px, bis_natur in ereignisse:
            if ez < frei + 1.0:
                continue
            dauer = {"zwischen": ZWISCHEN_MAX, "zitat": ZITAT_MAX,
                     "karte": KARTE_MAX}[art]
            bis = min(ez + dauer, naechster - 0.5)
            if bis_natur is not None:
                bis = min(bis, bis_natur)
            if bis > ez + 2.0:
                gewaehlt.append((ez, bis, art, px))
                frei = bis + EREIGNIS_ABSTAND

        # Themen-Karte: Titel + auflaufende Stichpunkte (moeglichst je Satz
        # einer) stehen dauerhaft im Bild, bis das Thema oder Zwischenthema
        # wechselt; auf Zitat-, Kennzahl- und NEXT-UP-Szenen traegt deren
        # eigene Grafik den Text. Die Bildseite waehlt das Drehbuch.
        stich = [p for p in eintrag.get("stichworte") or []
                 if isinstance(p, dict) and str(p.get("text") or "").strip()]
        zeiten = _punkt_zeiten(stich, rumpf_worte, rumpf_start, naechster) \
            if stich else []
        stich, zeiten = _luecken_fuellen(stich, zeiten, gewaehlt, rumpf_worte,
                                          rumpf_start, naechster)
        tags = list(zip(zeiten, stich))
        lage = str(eintrag.get("lage") or ("left" if k % 2 == 0 else "right"))
        segmente: list[tuple[float, str, str]] = [(rumpf_start, titel, lage)]
        for tz, _, art, px in gewaehlt:
            if art == "zwischen":
                segmente.append((tz, str(px["titel"]),
                                 str(px.get("lage") or lage)))
        # Story-Strecken zwischen den Sonderszenen; lange Strecken werden am
        # naechsten Stichwort geteilt (= Motivwechsel gegen die Monotonie).
        # Steht vor der Kartenplanung, weil ein Flug keine Szenengrenze
        # ueberqueren darf - die Grenzen muessen also vorher bekannt sein.
        strecken: list[tuple[float, float, tuple[str, dict] | None]] = []
        cursor = rumpf_start
        for tz, bis, art, px in gewaehlt:
            if tz > cursor + 0.3:
                strecken.append((cursor, tz, None))
            strecken.append((tz, bis, (art, px)))
            cursor = bis
        if naechster > cursor + 0.3:
            strecken.append((cursor, naechster, None))

        def story_teile(von: float, bis: float) -> list[tuple[float, float]]:
            """Lange Story-Strecke am naechsten Stichwort teilen."""
            teile: list[tuple[float, float]] = []
            s0 = von
            while bis - s0 > STORY_MAX:
                kand = [t for t, _ in tags if s0 + 8.0 <= t <= s0 + STORY_MAX]
                c = kand[-1] if kand else s0 + STORY_MAX
                teile.append((s0, c))
                s0 = c
            teile.append((s0, bis))
            return teile

        naehte = sorted({naechster} | {
            grenze for von, bis, so in strecken
            for paar in (story_teile(von, bis) if so is None else [(von, bis)])
            for grenze in paar})

        def naht_nach(t: float) -> float:
            """Erste Szenengrenze nach t, sonst das Kapitelende."""
            return next((n for n in naehte if n > t + 0.05), naechster)

        def sicht_bis(a: float, b: float) -> float:
            """Ende des zusammenhaengenden SICHTBAREN Fensters ab a.

            Fokus-Punkt, Detail-Kasten und Themen-Karte liegen nur auf
            Story-Strecken (karte_auflegen); Sonderszenen - NEXT UP, Zitat,
            Kennzahl - tragen ihre eigene Grafik und verdecken sie. Das
            geplante Fenster zeit[n] -> land[n] ist deshalb nicht das
            gerenderte: fiel ein Anker kurz vor eine Sonderszene, blieb vom
            Fenster ein Sekundenbruchteil und die Mindestdauer-Pruefung sah
            das nicht (Pacing-Messung 19.08.2026: $29B HYNIX BUYBACK stand
            0.15s, "MIGHT CALL IN SICK" 0.68s - frame-verifiziert)."""
            t = a
            for von, bis, so in strecken:
                if bis <= t + 0.01:
                    continue
                if so is not None or von > t + 0.05:
                    break       # Sonderszene oder Luecke: hier ist Schluss
                t = min(bis, b)
                if t >= b - 0.01:
                    break
            return t

        karten_plan: list[KartenStand] = []
        titel_plan: list[KartenStand] = []
        detail_plan: list[KartenStand] = []
        fokus_plan: list[FokusKarte] = []
        for gi, (g0, gtitel, glage) in enumerate(segmente):
            g1 = segmente[gi + 1][0] if gi + 1 < len(segmente) else naechster
            texte = [str(p["text"]) for t, p in tags if g0 <= t < g1]
            # Die Stichwort-Fragmente zum Punkt; die Lueckenfueller aus
            # _luecken_fuellen haben keine, dann bleibt die Liste leer.
            details = [_detail_liste(p) for t, p in tags if g0 <= t < g1]
            zeit = [t for t, p in tags if g0 <= t < g1]
            # Der Themen-Titel ist der Kopf der Randspalte. Er steht allein,
            # bis der erste Kartenstand die Voll-Spalte (Titel + Trennlinie
            # + Punkte) bringt - die loest ihn hart ab, denn die Titelpixel
            # sind identisch und zwei Overlays uebereinander wuerden das
            # Kasten-Alpha verdoppeln. Sein Zeitfenster wird deshalb erst
            # nach der Kartenstand-Rechnung eingetragen.
            tpfad, tx0, ty0 = png(szenen.themen_titel(gtitel, glage))
            # Landezeit je Punkt: er steht als Fokus-Karte in der freien
            # Bildhaelfte, bis der naechste ihn abloest, und fliegt dann in
            # die Themen-Karte. Der letzte Punkt parkt LETZT_HALT vor dem
            # Segmentende, damit die vollstaendige Liste am Themenende steht.
            # Zu kurze Fenster bekommen gar keine Fokus-Karte; ihr Punkt
            # erscheint sofort in der Liste, wie vor der Bewegung.
            land: list[float] = []
            fliegt: list[bool] = []
            zeigt: list[bool] = []
            for n in range(len(zeit)):
                if n + 1 < len(zeit):
                    # Der Flug setzt vor dem Wechsel ein, damit der abgeloeste
                    # Punkt die Mitte verlassen hat, wenn der neue dort
                    # ankommt; ohne Flug bleibt er bis zum Wechsel stehen.
                    ab, halt = zeit[n + 1] - FLUG_VORLAUF, zeit[n + 1]
                else:
                    ab, halt = g1 - LETZT_HALT - FLUG_DAUER, g1 - LETZT_HALT
                if ab > zeit[n] + FOKUS_MAX:
                    # Obergrenze gegen den Stillstand: nach FOKUS_MAX parkt
                    # der Punkt auch ohne Nachfolger in der Karte, statt dass
                    # die Bildmitte einfriert (Pacing-Messung 19.08.2026:
                    # PETROBRAS-Punkt stand 20.6s unveraendert).
                    ab, halt = zeit[n] + FOKUS_MAX, zeit[n] + FOKUS_MAX \
                        + FLUG_DAUER
                # Der Punkt steht bis dahin - auch ueber Szenengrenzen
                # hinweg, dort laeuft er ohne Blende weiter wie die
                # Themen-Karte. Nur der Flug selbst darf keine Grenze
                # ueberqueren, weil fade= das Alpha nicht bei halber
                # Deckkraft fortsetzen kann; faellt eine Grenze in die
                # Flugzeit, parkt der Punkt beim Wechsel mit hartem Schnitt.
                # Lesezeit-Boden nach Textlaenge statt Konstante: 1.1s
                # reichten fuer 29 Zeichen nicht (bis 30 cps gemessen,
                # 19.08.2026), waehrend parallel ein anderer Satz laeuft.
                boden = fokus_boden(texte[n])
                f = (sicht_bis(zeit[n], ab) - zeit[n] >= boden
                     and naht_nach(ab) >= ab + FLUG_DAUER)
                z = ab + FLUG_DAUER if f else halt
                steht = sicht_bis(zeit[n], z) - zeit[n] >= boden
                if not steht:
                    # Zu kurz fuer eine Fokus-Karte: der Punkt erscheint
                    # sofort in der Liste, wie vor der Bewegung.
                    f, z = False, zeit[n]
                # Nur gegen Rueckwaertsspringen sichern, ohne Mindestabstand:
                # ein Kartenstand mit Dauer 0 wird unten uebersprungen und der
                # naechste zeigt seinen Punkt mit. Ein Abstand wuerde sich bei
                # mehreren kurzen Punkten hintereinander aufsummieren und die
                # Liste gegen die Anker verschieben.
                gerade = min(max(z, land[-1]) if land else z, g1)
                fliegt.append(f and abs(gerade - z) < 0.01)
                zeigt.append(steht
                             and sicht_bis(zeit[n], gerade) - zeit[n] >= boden)
                land.append(gerade)
            marken = [g0] + land
            beginn = g0
            # Jeder Kartenstand ist dieselbe Randspalte mit einem Stichpunkt
            # mehr; er loest den vorigen (bzw. den Titel-Teil) hart an Ort
            # und Stelle ab - einen Einflug hat nur der Titel-Teil beim
            # Segmentbeginn. Nicht an stand == 0 haengen, denn ein zu kurzes
            # erstes Fenster wird uebersprungen.
            karten_start: float | None = None
            for stand in range(len(marken)):
                bis_f = marken[stand + 1] if stand + 1 < len(marken) else g1
                if stand == 0:
                    # Noch kein Punkt geparkt: die Spalte zeigt nur ihren
                    # Kopf. Solange steht der Titel-Teil allein.
                    beginn = bis_f
                    continue
                if bis_f - beginn <= 0.05 and stand + 1 < len(marken):
                    continue  # zu kurzes Fenster: der naechste Stand deckt es
                pfad, kx, ky = png(
                    szenen.themen_karte(gtitel, texte, stand, glage))
                if karten_start is None:
                    karten_start = beginn
                karten_plan.append(KartenStand(pfad, kx, ky, beginn, bis_f))
                beginn = bis_f
            # Der Titel-Teil steht vom Segmentbeginn bis zur ersten
            # Voll-Spalte (oder das ganze Segment, wenn nie ein Punkt parkt)
            # und faehrt von seiner Bildkante herein.
            titel_plan.append(KartenStand(
                tpfad, tx0, ty0, g0,
                karten_start if karten_start is not None else g1,
                "rechts" if glage == "right" else "links"))
            for n, t_n in enumerate(zeit):
                if not zeigt[n]:
                    continue
                # Flugziel ist die Textecke im Kartenstand nach der Landung.
                ziel = szenen.karte_punkt_ziel(gtitel, texte, n + 1, glage)
                if ziel is None:
                    continue
                # Derselbe Textinhalt wie in der Karte, sonst verliert der
                # Punkt beim Parken Text (die Fokus-Karte ist breiter).
                punkt_text = szenen.karte_text(texte[n])
                # Die Fragmente stehen nur, solange der Satz laeuft: sie
                # erscheinen einzeln an der Stelle, an der ihr Inhalt
                # gesprochen wird, gehen weg, bevor der Punkt in die Karte
                # fliegt, und parken nie mit - dort bleibt der Bulletpoint
                # allein. Zu kurze Fenster bekommen keine, zwei bis drei
                # Zeilen Kleintext wollen gelesen werden.
                #
                # Solange der Kapitel-Opener steht, bleibt der Detail-Kasten
                # weg: er reicht bis etwa y=465 und stiesse an dessen Bande
                # (ab y=426). Er setzt aber nur SPAETER ein, statt ganz zu
                # entfallen - der erste Stichpunkt eines Kapitels beginnt bei
                # OPENER_MIN=4.0 fast immer noch unter dem Opener, und ihm die
                # Fragmente zu streichen haette jedes Kapitel um seinen oft
                # substanzreichsten Punkt gebracht. Die Fokus-Karte selbst
                # steht dabei von Anfang an auf ihrer Stapel-Position; sie
                # endet oberhalb von 400 und kollidiert nie.
                det_bis = land[n] - (FLUG_DAUER if fliegt[n] else 0.0)
                det_von = max(t_n, opener_bis)
                # Wie beim Punkt: gemessen wird das sichtbare Fenster gegen
                # einen Boden nach Zeichenzahl. Drei Fragmente à 25 Zeichen
                # sind in DETAIL_MIN=2.6s nicht lesbar (38 cps gemessen).
                # Seit der Staffelung ist die Summe der Zeichen genau das
                # richtige Mass: die Fragmente werden nacheinander gelesen,
                # ihre Lesezeiten addieren sich also wirklich.
                # Passt nicht die ganze Liste ins Fenster, fallen
                # Fragmente von hinten weg, statt dass alle gleichzeitig
                # aufspringen - die Staffelung ist sonst genau dort dahin,
                # wo es am engsten ist.
                frag = list(details[n])
                fenster_frei = sicht_bis(det_von, det_bis) - det_von
                while frag and detail_boden(frag) > fenster_frei:
                    frag = frag[:-1]
                frag_stat[0] += len(details[n])
                frag_stat[1] += len(details[n]) - len(frag)
                zeigt_detail = bool(frag)
                # Der Fokus-Stapel steht in der Bildhaelfte GEGENUEBER der
                # Randspalte - vertikal kollidiert er mit deren Titel nicht
                # mehr, oben_min bleibt also die Bug-Unterkante (Default).
                bild, tx, ty = szenen.fokus_punkt(
                    punkt_text, glage, frag if zeigt_detail else None)
                pfad, fx, fy = png(bild)
                if zeigt_detail:
                    teile = szenen.detail_teile(punkt_text, frag, glage)
                    if teile is not None:
                        kaesten, zeilen_bilder = teile
                        # Jedes Fragment kommt, wenn sein Inhalt gesprochen
                        # wird - nicht alle mit dem Bulletpoint zusammen. Der
                        # Kasten selbst erscheint mit dem ersten Fragment,
                        # sonst stuende erst eine leere Flaeche da; seine
                        # Hoehe ist von Anfang an die endgueltige, damit der
                        # Stapel unter dem fliegenden Fokus-Punkt nicht
                        # wandert.
                        fenster = [w for w in rumpf_worte
                                   if det_von - 0.4 <= w.start <= det_bis]
                        dz = _detail_zeiten(frag[:len(zeilen_bilder)],
                                            fenster, det_von,
                                            det_von + fenster_frei)
                        # Erst alle Kastenstufen, dann die Zeilen: die
                        # Overlays werden in Listenreihenfolge aufgelegt,
                        # und eine spaetere (hoehere) Kastenstufe wuerde
                        # sonst die frueher eingetragenen Zeilen unter ihrem
                        # Grund begraben (Render-Probe 19.08.2026: Zeile 1
                        # und 2 standen nur noch schemenhaft im Bild).
                        for k, (kbild, zvon) in enumerate(zip(kaesten, dz)):
                            # Die Kastenstufe steht, bis die naechste sie
                            # abloest - hart und ohne Blende, sonst laegen
                            # zwei Kaesten uebereinander und der Grund
                            # verdoppelte kurz seine Deckkraft.
                            letzte = k + 1 >= len(dz)
                            kpfad, kx, ky = png(kbild)
                            detail_plan.append(KartenStand(
                                kpfad, kx, ky, zvon,
                                det_bis if letzte else dz[k + 1],
                                blende=0.3 if k == 0 else 0.0,
                                haelt=not letzte))
                        for zbild, zvon in zip(zeilen_bilder, dz):
                            zpfad, zx, zy = png(zbild)
                            detail_plan.append(KartenStand(
                                zpfad, zx, zy, zvon, det_bis))
                # Bewegt wird das zugeschnittene Overlay: sein Ziel ist die
                # Kartenposition minus dem Textversatz innerhalb des Bildes.
                fokus_plan.append(FokusKarte(
                    pfad, fx, fy, t_n, land[n],
                    land[n] - FLUG_DAUER if fliegt[n] else None,
                    ziel[0] - (tx - fx), ziel[1] - (ty - fy)))

        def karte_auflegen(sz: Szene, a: float, b: float) -> None:
            for st in titel_plan + karten_plan:
                a0, b0 = max(a, st.von), min(b, st.bis)
                if b0 - a0 > 0.02:
                    # Hereinfahren darf nur der Abschnitt, der den echten
                    # Kartenbeginn enthaelt: laeuft dieselbe Karte in der
                    # naechsten Szene weiter (Motivwechsel mitten im Thema),
                    # muss sie dort stehen. max() gibt st.von bitgleich
                    # zurueck, der Vergleich braucht also keine Toleranz.
                    sz.overlays.append(
                        Overlay(st.png, a0, b0, 0.0, st.x, st.y,
                                st.einflug if a0 == st.von else ""))
            for st in detail_plan:
                a0, b0 = max(a, st.von), min(b, st.bis)
                if b0 - a0 > 0.02:
                    # Wie die Karte darueber: aufblenden nur im Stueck mit
                    # dem echten Beginn, und nur das Stueck mit dem echten
                    # Ende darf ausblenden - sonst blendet dieselbe Zeile an
                    # jeder Szenennaht neu auf bzw. verblasst mitten im Satz.
                    sz.overlays.append(Overlay(
                        st.png, a0, b0, st.blende if a0 == st.von else 0.0,
                        st.x, st.y,
                        weiter=st.haelt or b0 < st.bis - 0.02))
            for fk in fokus_plan:
                a0, b0 = max(a, fk.von), min(b, fk.bis)
                if b0 - a0 <= 0.02:
                    continue
                # Aufblenden und Einflug nur im Stueck mit dem echten Beginn,
                # fliegen nur im Stueck, das die ganze Flugzeit enthaelt.
                # Abgeschnittene Stuecke blenden an der Naht nicht aus
                # (weiter=True) - sonst verblasst die Karte dort und steht in
                # der naechsten Szene wieder voll da, ein Flackern. Ohne
                # weiter=True stand fruehere Fassungen deshalb entweder als
                # Geisterschrift hinter dem naechsten Punkt oder verliessen
                # die Bildmitte, bevor ihr Satz gesprochen war.
                sz.overlays.append(Overlay(
                    fk.png, a0, b0, 0.35, fk.x, fk.y,
                    "unten" if a0 == fk.von else "",
                    flug_ab=(fk.flug_ab if fk.flug_ab is not None
                             and a0 <= fk.flug_ab + 0.001
                             and b0 >= fk.bis - 0.001 else None),
                    flug_x=fk.ziel_x, flug_y=fk.ziel_y,
                    weiter=b0 < fk.bis - 0.02))

        erste_story = True
        sz: Szene | None = None
        for von, bis, sonder in strecken:
            if sonder is None:
                for a, b in story_teile(von, bis):
                    if erste_story:
                        sz, erste_story = kapitel_szene, False
                    elif sz is not None and b - a < STORY_REST_MIN:
                        # Reststueck vor einer Sonderszene: zu kurz fuer ein
                        # eigenes Motiv - es blitzte sonst auf und waere
                        # wieder weg, bevor das Auge es erfasst hat
                        # (Pacing-Messung 19.08.2026: Szene 37 stand 0.875s).
                        # Das Vormotiv laeuft einfach weiter, was zugleich
                        # ein Pool-Bild spart.
                        pass
                    else:
                        akt = naechstes_motiv(akt)
                        sz = neu(akt, a)
                    karte_auflegen(sz, a, b)
            else:
                art, px = sonder
                erste_story = False
                akt = naechstes_motiv(akt)
                sz = neu(akt, von)
                if art == "zwischen":
                    sz.overlays.append(ov(
                        szenen.titel_karte(str(px["titel"]), label="NEXT UP",
                                           gross=False),
                        von + 0.1, bis, einflug="unten"))
                elif art == "zitat":
                    sz.overlays.append(ov(
                        szenen.zitat_post(str(px["text"]), _post_datum(datum)),
                        von + 0.1, bis, einflug="unten"))
                else:
                    _countup_overlays(sz, px, von + 0.2, bis, ov)

    if not vorne:
        # Blockliste alter Ordnung: Zahlen wie frueher vor dem Outro.
        zahlen_szenen(start_von(outro_idx) if outro_idx is not None else ende,
                      "Numbers of the day", "THE NUMBERS")

    # Schluss-Beat: das staerkste Board-Zitat des Tages als eigene Szene,
    # unmittelbar vor dem Abbinder. Es bekommt ein frisches Motiv und die
    # gewohnte Post-Karte - dasselbe Bildvokabular wie die Kapitel-Zitate,
    # damit der Schluss nicht wie ein Fremdkoerper wirkt.
    zit_idx = next((i for i, b in enumerate(bloecke)
                    if b.rolle == "schluss_zitat"), None)
    frage_idx = next((i for i, b in enumerate(bloecke)
                      if b.rolle == "schluss_frage"), None)
    if zit_idx is not None and block_worte[zit_idx]:
        t = start_von(zit_idx)
        bis = next((start_von(i) for i in (frage_idx, outro_idx)
                    if i is not None and block_worte[i]), ende)
        s = neu(pool_bild() or tages_motiv, t)
        s.overlays.append(ov(
            szenen.zitat_post(bloecke[zit_idx].text.split(": ", 1)[-1]
                              .strip('"'), _post_datum(datum)),
            t + 0.2, bis, einflug="unten"))
        print(f"Schluss-Zitat: {bis - t:.1f}s")

    if outro_idx is not None:
        # Die Cliffhanger-Frage wird schon vor dem Abbinder gesprochen, steht
        # im Bild aber bis zum letzten Frame (siehe outro_tafel) - so ist sie
        # das Letzte, was der Zuschauer sieht, ohne den Abbinder zu
        # verdraengen.
        frage = (bloecke[frage_idx].text if frage_idx is not None else "")
        t = start_von(frage_idx if frage_idx is not None
                      and block_worte[frage_idx] else outro_idx)
        s = neu(tages_motiv or pool_bild(), t)
        outro_start = t + 0.3
        # Board-Aktivitaets-Chart (aktivitaet.py, 18.08.2026): eigener Beat
        # vor der Abschluss-Tafel im selben Outro-Fenster, nur wenn genug
        # Zeit fuer beide bleibt - die Tafel behaelt dabei immer ihr
        # OUTRO_TAFEL_MIN_SEC, die Grafik bekommt nur den Rest. matplotlib
        # ist damit eine optionale, nicht harte Abhaengigkeit: schlaegt der
        # Import oder das Rendern fehl (z.B. auf einem venv ohne
        # matplotlib), faellt nur dieser eine Beat weg, nicht das ganze
        # Szenen-Layout - deshalb der eigene try/except statt eines
        # Modul-weiten `import aktivitaet` oben in der Datei.
        #
        # Bemessungsgrundlage ist das Ende der Sprache, nicht das Ende des
        # Videos: der stumme Ausklang danach gehoert ganz der Abschluss-Tafel
        # (Nutzerwunsch 19.08.2026, "das Schlussbild muss laenger sichtbar
        # sein und ausfaden"). Ohne diese Trennung frisst der Chart den
        # Ausklang auf und die Tafel behaelt wieder nur ihr Minimum.
        gesprochen = sprech_ende or ende
        try:
            import aktivitaet
            reihe = aktivitaet.taegliche_extrakt_zahlen(EXTRAKTE)
            chart_dauer = (gesprochen - outro_start) - OUTRO_TAFEL_MIN_SEC
            if len(reihe) >= 2 and chart_dauer >= AKTIVITAET_MIN_SEC:
                s.overlays.append(ov(aktivitaet.aktivitaets_chart(reihe),
                                     outro_start, outro_start + chart_dauer,
                                     einflug="unten"))
                outro_start += chart_dauer
        except Exception as e:
            print(f"Aktivitaets-Chart uebersprungen ({e})")
        # Die Tafel steht bis zum letzten Frame und blendet dabei laenger aus
        # als jedes andere Overlay - das Bild dahinter geht ueber SCHLUSS_FADE
        # gleichzeitig nach Schwarz (siehe _szene_clip).
        s.overlays.append(ov(szenen.outro_tafel(frage), outro_start, ende,
                             fade=SCHLUSS_FADE, einflug="unten"))
        print(f"Schlussbild: {ende - outro_start:.1f}s "
              f"(davon {ende - gesprochen:.1f}s stummer Ausklang)"
              + (f", Cliffhanger {frage!r}" if frage else ""))

    # Je Fokus-Punkt ein eigenes PNG; ueber Naehte geteilte Stuecke teilen es,
    # deshalb ueber die Pfade zaehlen und nicht ueber die Overlays.
    fokus = len({o.png for s in folge for o in s.overlays if o.flug_x})
    fluege = sum(1 for s in folge for o in s.overlays if o.flug_ab is not None)
    print(f"Szenen: {len(folge)}, Overlays: {ov_nr}, "
          f"Fokus-Punkte: {fokus} ({fluege} fliegen in die Karte)")
    print(f"Stichwort-Fragmente: {frag_stat[0] - frag_stat[1]} gezeigt, "
          f"{frag_stat[1]} wegen zu enger Fenster weggefallen"
          if frag_stat[1] else
          f"Stichwort-Fragmente: {frag_stat[0]} gezeigt, keins weggefallen")
    # Die Zahl, die am 18.08.2026 gefehlt hat: das Video lief mit einem
    # einzigen Motiv durch alle 70 Szenen, und im Log stand nichts davon.
    kulisse = len({s.motiv for s in folge if s.motiv})
    print(f"Kulisse: {kulisse} verschiedene Motive auf {len(folge)} Szenen")
    if kulisse < 2:
        print("WARNUNG: das ganze Video laeuft mit einem einzigen Bild - "
              "Sichtpruefung des Tages und motiv_quelle() pruefen")
    # Gegenprobe am Ergebnis: ein Flug muss ganz in seine Szene fallen, sonst
    # schneidet der Renderer ihn ab (fade= kann Alpha nicht bei halber
    # Deckkraft fortsetzen). Dafuer sorgt die Naht-Liste in der Planung - wenn
    # eine kuenftige Aenderung sie umgeht, faellt es hier auf.
    kanten = [s.start for s in folge[1:]] + [ende]
    zerschnitten = sum(1 for s, bis in zip(folge, kanten) for o in s.overlays
                       if o.flug_ab is not None
                       and (o.start < s.start - 0.01 or o.ende > bis + 0.01))
    if zerschnitten:
        print(f"WARNUNG: {zerschnitten} Fluege ragen aus ihrer Szene")
    return folge


def _countup_overlays(sz: Szene, karte: dict, ab: float, bis: float,
                      ov) -> None:
    """Kennzahl als Gross-Zahl mit hart geschnittenen Count-up-Stufen."""
    wert = str(karte["wert"])
    titel = str(karte.get("titel") or "")
    sub = str(karte.get("sub") or "")
    stufen = szenen.countup_werte(wert)
    for si, w in enumerate(stufen):
        sz.overlays.append(ov(szenen.zahl_tafel(w, titel, sub),
                              ab + si * COUNTUP_TAKT,
                              ab + (si + 1) * COUNTUP_TAKT, 0.0))
    sz.overlays.append(ov(szenen.zahl_tafel(wert, titel, sub),
                          ab + len(stufen) * COUNTUP_TAKT, bis, 0.0))


UEBERGANG = 0.48         # Kreuzblende auf das Motiv der naechsten Szene
EINFLUG_DAUER = 0.40     # so lange rueckt eine Karte in ihre Endlage
EINFLUG_WEG = 72         # aus so vielen Pixeln Versatz kommt sie
FLUG_DAUER = 0.35        # so lange fliegt ein Fokus-Punkt in die Themen-Karte
FLUG_VORLAUF = 0.25      # so viel vor dem Wechsel setzt er sich in Bewegung:
                         # der abgeloeste Punkt ist damit rund 0.1 s nach dem
                         # Wechsel gelandet, waehrend der neue noch einfliegt
                         # (EINFLUG_DAUER). Vorher starteten beide gleichzeitig
                         # und begegneten sich 0.55 s lang in der Bildmitte.
KALTSTART = 3.5          # Wunschdauer des Schlagworts des Tages allein im
                         # Bild, bevor die Hook-Karte uebernimmt. 2.0s waren
                         # ein Aufblitzen (Nutzer-Feedback 19.08.2026); der
                         # tatsaechliche Wechsel weicht zurueck bis
                         # KALTSTART_MIN, wenn die Hook-Karte sonst ihre
                         # Lesezeit vor intro_bis nicht bekaeme.
KALTSTART_MIN = 2.0      # harter Boden des Schlagworts
HOOK_VORLAUF = 0.5       # Blickwechsel zur Hook-Karte
HOOK_CPS = 17.0          # Lesetempo der Hook-Karte: sie wird woertlich
                         # mitgesprochen, deshalb Untertitel-Norm statt des
                         # konservativen Nebenher-Tempos (FOKUS_CPS)
AKTIVITAET_MIN_SEC = 3.5  # kuerzer lohnt sich die Balkengrafik im Outro nicht
ZAHL_COUNTUP_MIN = 1.8   # so lange muss der Count-up der letzten gesprochenen
                         # Zahl mindestens stehen bleiben, bevor die stille
                         # Uebersicht sein Fenster uebernehmen darf
ZAHL_UEBERSICHT_MIN = 2.2  # Lesezeit der Uebersichtstafel mit allen vier
                           # Zahlen; passt das Fenster nicht, entfaellt sie
                           # ersatzlos statt aufzublitzen
                         # (Balken + Titel brauchen einen Moment zum Lesen)
AUSKLANG = 5.0        # stummer Nachlauf hinter dem letzten gesprochenen Wort:
                      # so lange steht das Schlussbild noch, ohne dass Text
                      # dazukommt. Vorher standen hier 3.0s, die -shortest
                      # restlos wegschnitt, weil die Tonspur am letzten Wort
                      # endete - das Video war am letzten Wort schlagartig aus.
SCHLUSS_FADE = 1.5    # Ausblende des Schlussbilds (Tafel-Alpha und Bild nach
                      # Schwarz); muss kleiner als AUSKLANG bleiben.
OUTRO_TAFEL_MIN_SEC = 4.0  # die Abschluss-Tafel behaelt davon immer so viel,
                           # die Aktivitaets-Grafik bekommt nur den Rest
FOKUS_MIN = 1.1          # absoluter Boden; die Lesezeit rechnet fokus_boden()
DETAIL_MIN = 2.6         # kuerzer bekommt ein Punkt keine Stichwort-Fragmente:
                         # zwei bis drei Zeilen Kleintext wollen gelesen
                         # werden, und ein Aufblitzen kostet mehr Ruhe als es
                         # Substanz bringt
FOKUS_MAX = 12.0         # so lange steht ein Fokus-Punkt hoechstens in der
                         # Mitte; danach parkt er auch ohne Nachfolger in der
                         # Karte - die Karte lebt, statt dass die Mitte
                         # einfriert (gemessen 19.08.2026: 15.4-20.6s)
# Lesezeit-Boeden als Funktion der Textlaenge. Untertitel-Norm ist 15-17
# Zeichen pro Sekunde bei voller Aufmerksamkeit; hier liest der Zuschauer
# NEBEN dem laufenden gesprochenen Text, deshalb konservativer. Die
# Konstanten oben bleiben der absolute Boden fuer sehr kurze Texte.
FOKUS_VORLAUF = 0.9      # Zeit bis zum ersten Zeichen (Blick wandert hin)
FOKUS_CPS = 15.0         # Lesetempo Fokus-Punkt (Grossbuchstaben, gross)
DETAIL_CPS = 10.0        # Lesetempo Kleintext-Fragmente (12.0 lieferte
                         # Fragmente, die zu kurz standen, um lesbar zu
                         # sein - Nutzer-Feedback 19.08.2026)
DETAIL_FRAG_MIN = 2.0    # Boden je einzelnem Fragment (der Kasten als
                         # Ganzes hat mit DETAIL_MIN seinen eigenen);
                         # 1.4 war ein Aufblitzen, siehe DETAIL_CPS


def fokus_boden(text: str) -> float:
    """Mindest-Standzeit eines Fokus-Punkts nach seiner Zeichenzahl."""
    return max(FOKUS_MIN, FOKUS_VORLAUF + len(text) / FOKUS_CPS)


def detail_frag_boden(fragment: str) -> float:
    """Mindest-Standzeit EINES Fragments nach seiner Zeichenzahl.

    Eigener, niedrigerer Boden als DETAIL_MIN: der galt dem ganzen Kasten
    mit zwei bis drei Zeilen. Seit die Fragmente einzeln erscheinen, ist
    die Frage pro Fragment eine andere - ein Blick auf eine Zeile."""
    return max(DETAIL_FRAG_MIN, len(fragment) / DETAIL_CPS)


def detail_boden(fragmente: list[str]) -> float:
    """Mindest-Standzeit des Detail-Kastens: die Lesezeiten seiner Fragmente
    addieren sich, weil sie nacheinander erscheinen und gelesen werden."""
    return max(DETAIL_MIN, sum(detail_frag_boden(f) for f in fragmente))
LETZT_HALT = 2.5         # so lange steht die vollstaendige Liste am Themenende;
                         # gedeckt durch GOOGLE_KAPITEL_PAUSE, sonst muesste
                         # der letzte Punkt im laufenden Satz wegfliegen


def _lage(o: Overlay) -> tuple[str, str]:
    """x- und y-Angabe fuer overlay=, bei Bedarf als Bewegungs-Ausdruck.

    Zwei Bewegungen sind moeglich, beide als Versatz zur Ruhelage aus dem
    Zuschnitt. Sie liegen an entgegengesetzten Enden der Standzeit und
    duerfen deshalb einfach summiert werden.

    Einflug: die Karte startet um EINFLUG_WEG Pixel versetzt und rueckt mit
    cubic ease-out an ihren Platz - schnell los, sanft ankommen. Bewusst nur
    ein kurzer Versatz und nicht ein Anfahren von der Bildkante, sonst waere
    die Karte in den ersten Zehnteln teilweise ausserhalb des Bildes und die
    Regel "keine Sprechsekunde ohne Text" nur noch auf dem Papier erfuellt.
    Nach Ablauf der Einflugzeit haelt der if-Zweig die Karte bitgenau auf
    ihrem Platz, damit der Anschluss an den naechsten Kartenstand (harter
    Schnitt) nicht zittert.

    Flug: der Fokus-Punkt wandert in FLUG_DAUER an seinen Platz in der
    Themen-Karte, mit smoothstep - anfahren und abbremsen, damit das Auge
    mitkommt. clip() haelt den Weg vor dem Start und nach der Ankunft fest;
    ein negatives flug_ab (Flug begann in der Vorszene) rechnet dadurch
    korrekt weiter.

    Standzeiten unter der doppelten Einflugdauer bleiben statisch: was kaum
    steht, soll nicht auch noch fahren. Bei Enge weicht der Einflug, nicht
    der Flug - das Parken ist die eigentliche Aussage."""
    dx: list[str] = []
    dy: list[str] = []
    steht = o.ende - o.start - (FLUG_DAUER if o.flug_ab is not None else 0.0)
    if o.einflug and steht >= 2 * EINFLUG_DAUER:
        weg = (f"if(gt(t,{o.start + EINFLUG_DAUER:.3f}),0,{EINFLUG_WEG}"
               f"*pow(1-(t-{o.start:.3f})/{EINFLUG_DAUER},3))")
        if o.einflug == "links":
            dx.append(f"-({weg})")
        elif o.einflug == "rechts":
            dx.append(f"+({weg})")
        elif o.einflug == "oben":
            dy.append(f"-({weg})")
        else:
            dy.append(f"+({weg})")
    if o.flug_ab is not None:
        p = f"clip((t-{o.flug_ab:.3f})/{FLUG_DAUER},0,1)"
        s = f"(({p})*({p})*(3-2*({p})))"
        dx.append(f"+({o.flug_x - o.x})*{s}")
        dy.append(f"+({o.flug_y - o.y})*{s}")
    xa = f"'{o.x}{''.join(dx)}'" if dx else str(o.x)
    ya = f"'{o.y}{''.join(dy)}'" if dy else str(o.y)
    return xa, ya


def _motiv_normalisiert(motiv: Path, arbeit: Path) -> Path:
    """Normalisierte Arbeitskopie eines animierten Motivs (GIF/WebM/MP4):
    feste Framerate, gedeckelte Aufloesung, yuv420p, ohne Ton. Das gibt GIF
    und Video-Clips in _szene_clip() denselben Renderpfad (kein GIF-
    Demuxer-Sonderfall) und wird pro Motiv gecacht, weil derselbe Motiv-Pfad
    innerhalb eines Laufs mehrfach gerendert werden kann (das einlaufende
    Motiv der naechsten Szene im Crossfade nutzt zwar den Poster, nicht
    diese Kopie - aber ein Rueckgriff auf denselben Tag kann dieselbe Datei
    mehrfach als Szenen-Kulisse ziehen)."""
    ziel = arbeit / "normalisiert" / f"{motiv.stem}.mp4"
    if ziel.exists() and ziel.stat().st_size > 0:
        return ziel
    ziel.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(motiv),
         # trunc(.../2)*2 statt nur min(1920,iw): manche /biz/-Clips haben
         # eine ungerade Breite (z.B. 341x540) - yuv420p verlangt gerade
         # Breite UND Hoehe, -2 rundet nur die berechnete Seite, nicht die
         # feste (Fuchs-Clip 18.08.2026: ffmpeg-Exit 187, "width not
         # divisible by 2").
         "-vf", f"scale='trunc(min(1920,iw)/2)*2':-2,fps={FPS}",
         "-pix_fmt", "yuv420p", "-an", str(ziel)],
        check=True, timeout=120, capture_output=True)
    return ziel


def _klip_poster(pfad: Path, arbeit: Path) -> Path:
    """Standbild eines WebM/MP4-Clips (Katalog-Clips haben - anders als
    animierte GIFs - kein vorab erzeugtes Posterframe, weil ihre
    Sichtpruefung nur Extraktframes braucht, keinen dauerhaften Poster).
    Wird nur fuer tatsaechlich einer Szene zugeteilte Clips erzeugt, nicht
    fuer den ganzen Katalog."""
    ziel = arbeit / "normalisiert" / f"{pfad.stem}__poster.png"
    if ziel.exists():
        return ziel
    ziel.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(pfad),
         "-frames:v", "1", "-q:v", "2", str(ziel)],
        check=True, timeout=30, capture_output=True)
    return ziel


INTRO_KLIP_KEY = -1  # Sentinel in _klip_zuordnung()s Rueckgabe: kollidiert
# nie mit einem echten Abschnitts-Index (immer >= 0), markiert den fuer das
# Intro nominierten Clip in derselben dict wie die Kapitel-Zuteilung.

KLIP_PROMPT_ZUORDNUNG = """\
Du ordnest kurze, TONLOSE Videoclips (WebM/MP4-Ausschnitte vom Board /biz/)
den Abschnitten eines Nachrichtenvideos zu, damit sie dort als kurze bewegte
Kulisse statt eines Standbilds laufen. Bewegtbild ist deutlich unterhaltsamer
als ein Standbild - nutze JEDEN Clip, der zu einem Abschnitt vernuenftig
passt (Stimmung/Thema/Motiv, nicht nur Stichwortgleichheit). Im Zweifel
lieber zuteilen als weglassen; nur wenn ein Clip zu KEINEM Abschnitt passt,
bleibt er ungenutzt.

Unten stehen die Abschnitte (Nummer und Titel) sowie die freigegebenen
Clips mit ihrer Beschreibung. Waehle fuer jeden Abschnitt HOECHSTENS EINEN
Clip. Ein Clip darf hoechstens einem Abschnitt zugeteilt werden.

Zusaetzlich: nominiere unter "intro" den einen Clip (falls vorhanden), der
sich am besten als Aufmerksamkeits-Fang fuer die allerersten Sekunden des
Videos eignet (auffaellig, keine Vorkenntnis des Themas noetig). Dieser Clip
darf KEINEM Abschnitt zugeteilt sein - waehle ihn aus den uebrigen Clips.
Bleibt keiner uebrig, gib "intro": null zurueck (oder nimm einen Clip aus
der Zuordnung heraus, wenn er als Aufhaenger klar am besten passt).

Gib NUR ein JSON-Objekt aus, ohne Vor- oder Nachbemerkungen und ohne
Code-Zaun:
{"zuordnung": {"<abschnitt-nummer>": "<clip-md5>", ...},
 "intro": "<clip-md5-oder-null>"}
"""


def _klip_zuordnung(datum: str, abschnitte: list[Abschnitt],
                    titel_map: dict[str, str],
                    nur_video: bool = False) -> dict[int, Path]:
    """Ordnet freigegebene Katalog-Clips (arbeit/clips/katalog.json)
    inhaltlich Abschnitten zu - ein claude_ruf()-Aufruf, analog den
    Sichtpruefungen, statt einer Rang-Sortierung wie bei der Bildkulisse
    (siehe _bild_rang): Clips sind selten genug, dass sich eine inhaltliche
    Einzelzuordnung lohnt (Recherche 18.08.2026, Abschnitt "Zuordnung im
    Drehbuch"). Leer, wenn keine Clips frei sind oder der Aufruf scheitert -
    dann laeuft die Kulisse wie bisher nur mit Bildern, nie ein Fehler.

    Der Katalog ist kumulativ (siehe klip_katalog.py) - ohne eine
    Wiederverwendungssperre koennte derselbe freigegebene Clip taeglich neu
    gewaehlt werden, unbegrenzt. Analog der MD5-Sperrliste der
    Bilder (run_report.VERWENDET_TAGE) bleibt ein kuerzlich gezeigter Clip
    hier aussen vor, und jede tatsaechliche Wahl schreibt "zuletzt_verwendet"
    sofort in den Katalog zurueck - ausser mit nur_video (Testpfad): dann
    bleibt der Stempel im Speicher und der Katalog auf der Platte unberuehrt,
    ein Testlauf darf dem naechsten produktiven Lauf keine Clips wegsperren
    (Delta-Rueckrollung vom 19.08.2026). Ausnahme: "zuletzt_verwendet" ==
    datum zaehlt weiterhin als frei - sonst sperrt sich ein erneuter Testlauf
    desselben Tages (z.B. nach einem Bugfix-Rebuild) selbst alle Clips."""
    katalog = klip_katalog.katalog_laden()
    grenze = (date.fromisoformat(datum)
             - timedelta(days=rr.VERWENDET_TAGE)).isoformat()

    def frisch_genug(e: dict) -> bool:
        letzte = e.get("zuletzt_verwendet")
        return not letzte or letzte == datum or letzte < grenze

    frei = {md5: e for md5, e in katalog["clips"].items()
           if e.get("status") == "frei" and e.get("beschreibung")
           and frisch_genug(e)}
    if not frei or not abschnitte:
        return {}
    zeilen = [f"{i}: {titel_map.get(a.threads[0], a.threads[0])}"
             if a.threads else f"{i}: Abschnitt {i}"
             for i, a in enumerate(abschnitte)]
    eingabe = ("Abschnitte:\n" + "\n".join(zeilen) + "\n\nClips:\n"
              + "\n".join(f"- {md5}: {e['beschreibung']}"
                          for md5, e in frei.items()))
    daten: dict = {}
    for versuch in (1, 2):
        try:
            out = rr.claude_ruf(KLIP_PROMPT_ZUORDNUNG, eingabe, "sonnet",
                                180, effort="low").strip()
            daten = json.loads(rr._json_schneiden(out))
        except Exception as e:
            print(f"WARNUNG: Clip-Zuordnung fehlgeschlagen ({e}) - Kulisse "
                 f"laeuft ohne Clips")
            return {}
        roh = daten.get("zuordnung")
        # Leere Zuordnung trotz freier, beschriebener Clips ist plausibel
        # (kein Clip passt), aber bei effort="low" auch schon mal ein
        # inkonsistenter Ausreisser - ein zweiter Versuch ist billiger als
        # ein Video ganz ohne Clips (Nutzer-Feedback 18.08.2026).
        if (isinstance(roh, dict) and roh) or isinstance(daten.get("intro"),
                                                          str):
            break
        print(f"Clip-Zuordnung: Versuch {versuch} ordnete nichts zu "
             f"({len(frei)} Clips verfuegbar)"
             + (" - zweiter Versuch" if versuch == 1 else ""))
    roh = daten.get("zuordnung")
    if not isinstance(roh, dict):
        roh = {}
    ziel_dir = klip_katalog.KLIP_DIR / datum
    aus: dict[int, Path] = {}
    vergeben: set[str] = set()
    for k, md5 in roh.items():
        try:
            idx = int(k)
        except (TypeError, ValueError):
            continue
        if not (0 <= idx < len(abschnitte)) or not isinstance(md5, str) \
                or md5 in vergeben or md5 not in frei:
            continue
        pfad = klip_katalog.klip_datei(md5, katalog, ziel_dir)
        if pfad is None:
            continue
        aus[idx] = pfad
        vergeben.add(md5)
        katalog["clips"][md5]["zuletzt_verwendet"] = datum
    intro_md5 = daten.get("intro")
    # Backstop zum Prompt: nominiert das Modell trotz der Vorgabe einen
    # bereits einem Kapitel zugeteilten Clip, laeuft er sonst zweimal im
    # selben Video - einmal im Intro, einmal im Kapitel-Opener. Genau die
    # Doppelung, die der Nutzer am 19.08.2026 gemeldet hat. Lieber ein
    # Intro ohne Clip (faellt auf tages_motiv zurueck) als ein Wiedersehen
    # nach wenigen Minuten.
    if isinstance(intro_md5, str) and intro_md5 in vergeben:
        print(f"Clip-Zuordnung: Intro-Clip {intro_md5[:8]} ist bereits einem "
             f"Kapitel zugeteilt - Intro laeuft ohne Clip")
        intro_md5 = None
    if isinstance(intro_md5, str) and intro_md5 in frei:
        pfad = klip_katalog.klip_datei(intro_md5, katalog, ziel_dir)
        if pfad is not None:
            aus[INTRO_KLIP_KEY] = pfad
            vergeben.add(intro_md5)
            katalog["clips"][intro_md5]["zuletzt_verwendet"] = datum
    if vergeben:
        if nur_video:
            print("Testlauf (--nur-video) - Clip-Katalog nicht gestempelt "
                  "(zuletzt_verwendet in arbeit/clips/katalog.json bleibt "
                  "unberuehrt)")
        else:
            klip_katalog.katalog_speichern(katalog)
    return aus


def _szene_clip(s: Szene, f0: int, f1: int, idx: int, arbeit: Path,
                suffix: str, bug: Overlay, vig: Overlay,
                naechstes: Path | None, naechster_zoom_rein: bool,
                schluss: bool = False) -> Path:
    """Eine Szene als eigenen kurzen Clip rendern: Motiv mit langsamem
    zoompan-Drift, darueber Vignette, die zeitgesteuerten Text-Overlays und
    zuoberst der Ecken-Bug. Bewusst je Szene ein kleiner, immer gleich
    aufgebauter ffmpeg-Lauf statt einer grossen fragilen Filterkette.

    Wechselt das Motiv zur naechsten Szene, blendet deren Bild in den letzten
    Frames dieses Clips auf. Der Uebergang steckt damit im Clip selbst und der
    Zusammenschnitt bleibt ein Streamcopy - kein Re-Encode der Nahtstellen."""
    n = max(f1 - f0, 1)
    dauer = n / FPS
    t0 = f0 / FPS
    ovs: list[Overlay] = [Overlay(vig.png, 0.0, dauer, 0.0, vig.x, vig.y)]
    for o in s.overlays:
        a = max(0.0, o.start - t0)
        b = min(dauer, o.ende - t0)
        if b - a > 0.05:
            # Einflug nur, wenn der Overlay in dieser Szene wirklich beginnt
            ein = o.einflug if o.start >= t0 else ""
            # Was hier endet, blendet weich weg - auch wenn das Ende genau auf
            # die Szenengrenze faellt, denn dort blendet der Hintergrund
            # ebenfalls. Nur was in der naechsten Szene weiterlaeuft, muss bis
            # zum letzten Frame stehen bleiben, sonst blitzt es an der Naht.
            # Ein Frame Toleranz, weil die Szenengrenzen auf das Frame-Raster
            # gerundet werden und ein Kartenende sonst um Millisekunden
            # "hinausragt" und faelschlich als Fortsetzung gilt.
            ovs.append(Overlay(
                o.png, a, b, o.fade, o.x, o.y, ein,
                ausblenden=(o.ende - t0 <= dauer + 1.0 / FPS
                            and not o.weiter),
                einblenden=o.start >= t0,
                flug_ab=None if o.flug_ab is None else o.flug_ab - t0,
                flug_x=o.flug_x, flug_y=o.flug_y))
    ovs.append(Overlay(bug.png, 0.0, dauer, 0.0, bug.x, bug.y))

    animiert = bool(s.motiv is not None and s.motiv_animiert)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if s.motiv is not None and animiert:
        try:
            quelle = _motiv_normalisiert(s.motiv, arbeit)
        except Exception as e:
            if s.motiv_poster is None:
                raise
            print(f"WARNUNG: animiertes Motiv {s.motiv.name} nicht "
                  f"normalisiert ({e}) - Standbild-Fallback")
            ersatz = replace(s, motiv=s.motiv_poster, motiv_animiert=False)
            return _szene_clip(ersatz, f0, f1, idx, arbeit, suffix, bug, vig,
                               naechstes, naechster_zoom_rein, schluss)
        # -stream_loop -1 laesst das Motiv seine eigene, meist kuerzere
        # Laufzeit fuellend wiederholen; -t deckelt sie auf die von der TTS
        # vorgegebene Szenendauer (Analogie zu den geloopten Overlay-PNGs
        # unten). d=1 haelt zoompan pro Ausgabeframe bei genau einem
        # Eingabeframe statt ein Standbild d-mal zu vervielfachen - die
        # Zoomformel zaehlt ueber `on` ohnehin Ausgabeframes, der Ken-Burns-
        # Effekt bleibt also unveraendert, nur die Animation bleibt erhalten.
        cmd += ["-stream_loop", "-1", "-t", f"{dauer + 0.3:.3f}",
               "-i", str(quelle)]
        d = "1"
    elif s.motiv is not None:
        cmd += ["-i", str(s.motiv)]
        d = str(n)
    if s.motiv is not None:
        z = f"1+{ZOOM_HUB}*on/{n}" if s.zoom_rein \
            else f"1+{ZOOM_HUB}*({n}-on)/{n}"
        # 2x-Supersampling vor zoompan gegen das bekannte Zittern des Filters
        teile = [f"[0:v]scale={2 * CANVAS_W}:{2 * CANVAS_H}"
                 f":force_original_aspect_ratio=increase,"
                 f"crop={2 * CANVAS_W}:{2 * CANVAS_H},"
                 f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                 f":d={d}:s={CANVAS_W}x{CANVAS_H}:fps={FPS}[bg]"]
    else:
        cmd += ["-f", "lavfi", "-i",
                f"color=c={HINTERGRUND}:s={CANVAS_W}x{CANVAS_H}:r={FPS}"
                f":d={dauer + 0.3:.3f}"]
        teile = ["[0:v]null[bg]"]
    for o in ovs:
        cmd += ["-loop", "1", "-framerate", str(FPS),
                "-t", f"{dauer + 0.3:.3f}", "-i", str(o.png)]
    kette = "[bg]"
    uebergang = (s.motiv is not None and naechstes is not None
                 and naechstes != s.motiv and dauer > 2 * UEBERGANG)
    if uebergang:
        cmd += ["-loop", "1", "-framerate", str(FPS),
                "-t", f"{dauer + 0.3:.3f}", "-i", str(naechstes)]
        # Das kommende Motiv wird in dem Zoomstand eingeblendet, mit dem die
        # naechste Szene startet (die Zoomrichtung wechselt je Szene, deshalb
        # ist der Anschluss stetig) - sonst springt es an der Naht.
        z0 = 1.0 if naechster_zoom_rein else 1 + ZOOM_HUB
        teile.append(
            f"[{len(ovs) + 1}:v]scale={2 * CANVAS_W}:{2 * CANVAS_H}"
            f":force_original_aspect_ratio=increase,"
            f"crop={2 * CANVAS_W}:{2 * CANVAS_H},"
            f"crop=iw/{z0:.3f}:ih/{z0:.3f},scale={CANVAS_W}:{CANVAS_H},"
            f"format=rgba,fade=t=in:st={dauer - UEBERGANG:.3f}"
            f":d={UEBERGANG}:alpha=1[nx]")
        teile.append(f"{kette}[nx]overlay=0:0[bgx]")
        kette = "[bgx]"
    for j, o in enumerate(ovs):
        filt = f"[{j + 1}:v]format=rgba"
        # Aufblenden nur, wo das Overlay wirklich beginnt: ein aus der
        # Vorszene weiterlaufendes Overlay wuerde sonst an jeder Naht neu
        # einblenden (o.start ist hier die auf die Szene gekuerzte Zeit).
        if o.fade > 0 and o.einblenden:
            filt += f",fade=t=in:st={o.start:.3f}:d={o.fade:.2f}:alpha=1"
        if o.flug_ab is not None:
            # Waehrend des Flugs verblasst die Karte und der Karteneintrag
            # erscheint an ihrer Landestelle. Die Grossschrift der Fokus-Karte
            # und der kleine Eintrag sind nicht deckungsgleich; der
            # Alpha-Uebergang deckt den Groessenwechsel ab.
            fa = max(0.0, o.flug_ab + 0.45 * FLUG_DAUER)
            filt += (f",fade=t=out:st={fa:.3f}"
                     f":d={max(0.08, o.flug_ab + FLUG_DAUER - fa):.2f}:alpha=1")
        elif o.fade > 0 and o.ausblenden:
            filt += (f",fade=t=out:st={max(o.start, o.ende - o.fade):.3f}"
                     f":d={o.fade:.2f}:alpha=1")
        filt += f"[o{j}]"
        teile.append(filt)
        xa, ya = _lage(o)
        teile.append(f"{kette}[o{j}]overlay=x={xa}:y={ya}"
                     f":enable='between(t,{o.start:.3f},{o.ende:.3f})'[v{j}]")
        kette = f"[v{j}]"
    # Letzte Szene: das ganze Bild geht nach Schwarz, waehrend die
    # Abschluss-Tafel darueber ausblendet. Ein Bericht, der am letzten Wort
    # hart abreisst, wirkt wie ein Verbindungsabbruch (Nutzerwunsch
    # 19.08.2026). Die Blende liegt im Clip selbst, der Zusammenschnitt
    # bleibt damit ein Streamcopy.
    if schluss and dauer > SCHLUSS_FADE + 0.2:
        teile.append(f"{kette}fade=t=out:st={dauer - SCHLUSS_FADE:.3f}"
                     f":d={SCHLUSS_FADE}[fin]")
        kette = "[fin]"
    ziel = arbeit / f"szene{suffix}_{idx:03d}.mp4"
    cmd += ["-filter_complex", ";".join(teile), "-map", kette,
            "-frames:v", str(n), "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", str(ziel)]
    try:
        subprocess.run(cmd, check=True, timeout=600, capture_output=True)
    except subprocess.CalledProcessError as e:
        if not animiert or s.motiv_poster is None:
            raise
        print(f"WARNUNG: Render mit animiertem Motiv "
              f"{s.motiv.name if s.motiv else '?'} fehlgeschlagen ({e}) - "
              f"Retry mit Standbild")
        ersatz = replace(s, motiv=s.motiv_poster, motiv_animiert=False)
        return _szene_clip(ersatz, f0, f1, idx, arbeit, suffix, bug, vig,
                           naechstes, naechster_zoom_rein, schluss)
    return ziel


BETT = Path.home() / ".config" / "boardstats" / "bett.opus"
BETT_QUELLE = Path.home() / ".config" / "boardstats" / "bett_quelle.mp3"
BETT_LOOP_UEBERGANG = 4.0  # Sekunden Crossfade an der Loop-Naht eines echten Tracks
BETT_DB = -20.0          # so viel leiser als die Sprache laeuft das Bett
BETT_AUSBLENDE = 4.0     # Sekunden Ausblende am Videoende
BETT_SEKUNDEN = 720      # Bettlaenge; alle Perioden gehen glatt darin auf
ZIEL_LUFS = -14.0        # YouTubes Normalisierungsziel
# Ducking (Befund 18.08.2026): eine Bandenergie-Messung mit der echten
# Stimme zeigte, dass eine feste -20dB-Konstante das Arpeggio im
# 150-700Hz-Sprachband nicht ausreichend absenkt. Das Bett laeuft daher
# durchgehend als Hintergrundmusik ueber das ganze Video, sidechaincompress
# drueckt es weg, sobald Sprache aktiv ist, statt es dauerhaft auf -20dB zu
# belassen.
DUCK_SCHWELLE = 0.02     # sidechaincompress-Schwelle (linear), weit unter Sprachpegel
DUCK_RATIO = 20          # nahe Limiting: fast jede Ueberschreitung wird geduckt
DUCK_ATTACK = 50         # ms
DUCK_RELEASE = 350       # ms
# Intro-Anhebung: Bis zur ersten Kapitelmarke laeuft das Bett lauter. Der
# Vorspann ist die einzige Strecke, die praktisch jeder Zuschauer hoert
# (gemessen 19.08.2026: nach 17 s sind schon 24 % weg), und dort traegt die
# Musik den Schwung, waehrend spaeter der Inhalt traegt. Gemessene Intro-
# Laenge: rund 30 s bis Kapitel 1. Der Wert ist eine Starthypothese - ob 7 dB
# richtig sind, entscheidet das Ohr am fertigen Video.
BETT_INTRO_ANHEBUNG = 7.0   # dB zusaetzlich bis zur ersten Kapitelmarke
BETT_INTRO_RAMPE = 2.5      # Sekunden, in denen sich die Anhebung abbaut
# Toene des Betts: Puls (A1), Bass (A2) und ein Arpeggio A-C-E-A, dazu ein
# hoher Ton als Farbe. Bewusst im Mittenbereich und nicht nur als
# Tieffrequenz-Flaeche: eine Flaeche unter 150 Hz ist messbar vorhanden, aber
# selbst auf Studiokopfhoerern nicht als Musik zu erkennen (Befund
# 17.08.2026). Alle Perioden teilen BETT_SEKUNDEN, damit die Loop-Naht
# phasenrichtig sitzt - erreicht wird sie bei rund 10 min Video ohnehin nie.
BETT_STIMMEN = [
    # (Frequenz, Amplitude, Periode, Versatz, Abfall); Abfall None = Flaeche
    (55.0, 0.70, 0.75, 0.0, 8.0),        # Puls im 80er-Takt
    (110.0, 0.22, 12.0, 0.0, None),      # Bass als Flaeche
    (220.0, 0.50, 3.0, 0.0, 3.2),        # Arpeggio
    (261.63, 0.42, 3.0, 0.75, 3.2),
    (329.63, 0.42, 3.0, 1.5, 3.2),
    (440.0, 0.30, 3.0, 2.25, 3.2),
    (659.26, 0.16, 12.0, 6.0, 2.6),      # Farbe, nur jede vierte Runde
]


def bett_bauen(ziel: Path = BETT, quelle: Path = BETT_QUELLE) -> Path:
    """Das Musikbett bauen und normalisiert ablegen.

    Liegt eine Quelldatei vor (echter, Content-ID-freier Track, manuell auf
    dem Render-Rechner platziert - siehe [[video-bett-echter-track]]), wird
    daraus ein loopfaehiges Bett geschnitten (`_bett_aus_track`). Sonst wie
    bisher synthetisch aus BETT_STIMMEN (`_bett_synthetisch`) - Synthese hat
    keinen Rechteinhaber, keinen Fingerprint und keinen Content-ID-Eintrag,
    was fuer den taeglich unbeaufsichtigten Upload sicherer ist. Beide Wege
    normalisieren vorab auf einen festen Wert, damit BETT_DB im Lauf eine
    Konstante ist und jeder Tag gleich klingt. Die Datei(en) liegen ausserhalb
    des Repos - das Repo ist oeffentlich, und Audio gehoert dort so wenig hin
    wie Board-Bilder."""
    if quelle.exists():
        return _bett_aus_track(quelle, ziel)
    return _bett_synthetisch(ziel)


def _bett_aus_track(quelle: Path, ziel: Path) -> Path:
    """Loopfaehiges Bett aus einem echten Track schneiden.

    Ein realer Track loopt nicht von selbst - beim Zusammenstoss von Ende
    und Anfang wuerde `-stream_loop -1` einen hoerbaren Bruch erzeugen. Statt
    den ganzen Track zu wiederholen, wird daher eine Loop-Naht gebaut: die
    ersten und letzten BETT_LOOP_UEBERGANG Sekunden werden abgetrennt, gegeneinander
    ueberblendet (Tail faded raus, Head faded rein, gemischt) und ans Ende
    der uebrig bleibenden Mitte gehaengt. Die Schleife endet damit exakt an
    der Stelle, an der der Track (ohne die abgeschnittenen Raender) ohnehin
    weiterginge - dieselbe Crossfade-Idee wie an den Segmentgrenzen in
    `_ton_kette()`, nur als Loop-Naht statt als Ein-/Ausblende."""
    dauer = _mp3_dauer(quelle)
    fade = min(BETT_LOOP_UEBERGANG, dauer / 4)
    mitte_ende = dauer - fade
    kette = (
        f"[0:a]atrim=start={fade:.3f}:end={mitte_ende:.3f},"
        f"asetpts=PTS-STARTPTS[body];"
        f"[0:a]atrim=start={mitte_ende:.3f}:end={dauer:.3f},"
        f"asetpts=PTS-STARTPTS,afade=t=out:st=0:d={fade:.3f}[tail];"
        f"[0:a]atrim=start=0:end={fade:.3f},"
        f"asetpts=PTS-STARTPTS,afade=t=in:st=0:d={fade:.3f}[head];"
        f"[tail][head]amix=inputs=2:duration=first:normalize=0[naht];"
        f"[body][naht]concat=n=2:v=0:a=1,"
        f"loudnorm=I=-20:TP=-2:LRA=6[out]")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-i", str(quelle),
         "-filter_complex", kette, "-map", "[out]",
         "-ac", "2", "-c:a", "libopus", "-b:a", "96k", str(ziel)],
        check=True, timeout=900, capture_output=True)
    print(f"Bett aus Track gebaut: {ziel} ({ziel.stat().st_size // 1024} KiB, "
          f"{dauer - fade:.0f} s Loop, Quelle {quelle.name})")
    return ziel


def _bett_synthetisch(ziel: Path) -> Path:
    """Das Musikbett synthetisieren und normalisiert ablegen."""
    ein: list[str] = []
    teile: list[str] = []
    for i, (f, a, p, v, abfall) in enumerate(BETT_STIMMEN):
        ein += ["-f", "lavfi", "-i",
                f"sine=f={f}:d={BETT_SEKUNDEN}:r=48000"]
        if abfall is None:
            # Flaeche mit langsamer Schwebung, damit sie nicht steht
            kurve = f"{a}*(0.85+0.15*sin(2*PI*t/{p}))"
        else:
            # Anschlag mit exponentiellem Abfall, ab dem Versatz in der Periode
            m = f"mod(t,{p})"
            kurve = f"{a}*gte({m},{v})*exp(-{abfall}*({m}-{v}))"
            if v + p / 4 < p:      # nur das eigene Viertel der Periode
                kurve = f"{kurve}*lt({m},{v + p / 4 + 0.75})"
        teile.append(f"[{i}:a]volume='{kurve}':eval=frame[s{i}]")
    misch = "".join(f"[s{i}]" for i in range(len(BETT_STIMMEN)))
    teile.append(f"{misch}amix=inputs={len(BETT_STIMMEN)}:normalize=0,"
                 f"aecho=0.8:0.7:420|900:0.28|0.16,alimiter=limit=0.9,"
                 f"loudnorm=I=-20:TP=-2:LRA=6[out]")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", *ein,
         "-filter_complex", ";".join(teile), "-map", "[out]",
         "-ac", "2", "-c:a", "libopus", "-b:a", "96k", str(ziel)],
        check=True, timeout=900, capture_output=True)
    print(f"Bett gebaut: {ziel} ({ziel.stat().st_size // 1024} KiB, "
          f"{BETT_SEKUNDEN} s)")
    return ziel


def _intro_anhebung(kapitel1: float) -> str:
    """volume-Ausdruck, der das Bett bis kapitel1 anhebt und dann zurueckfaehrt.

    Der Ausdruck rechnet in linearer Verstaerkung, weil der volume-Filter das
    so erwartet; ueber die kurze Rampe ist der Unterschied zu einer Rampe in
    dB nicht hoerbar. Die Anhebung sitzt hinter sidechaincompress, nicht
    davor: das Ducking soll weiter formen, nur auf hoeherem Grundpegel.
    Leerstring, wenn keine Kapitelmarke bekannt ist - dann bleibt alles wie
    bisher, statt auf einen geratenen Zeitpunkt zu setzen."""
    if kapitel1 <= BETT_INTRO_RAMPE:
        return ""
    k = 10 ** (BETT_INTRO_ANHEBUNG / 20)
    ab = kapitel1 - BETT_INTRO_RAMPE
    return (f"volume=volume='if(lt(t,{ab:.2f}),{k:.4f},"
            f"if(lt(t,{kapitel1:.2f}),"
            f"{k:.4f}+(1-{k:.4f})*(t-{ab:.2f})/{BETT_INTRO_RAMPE},1))'"
            f":eval=frame")


def _ton_kette(start: int, ende: float,
               kapitel1: float = 0.0) -> tuple[list[str], list[str], str]:
    """Eingaben, Filterteile und Ausgangs-Label der Tonspur (ohne Loudness).

    start ist der ffmpeg-Input-Index der Sprachdatei; der Messlauf zaehlt ab
    0, der Mux ab 1, weil dort das Video Input 0 ist. Ohne Bettdatei bleibt
    es bei der Sprache - fehlt sie, laeuft der Cron-Tag ohne Musik weiter.

    Das Bett laeuft durchgehend als Hintergrundmusik ueber die gesamte
    Videolaenge; sidechaincompress duckt es, sobald Sprache aktiv ist
    (Befund 18.08.2026, Bandenergie-Messung mit der echten Stimme zeigte,
    dass eine feste -20dB-Konstante das Arpeggio im 150-700Hz-Sprachband
    nicht ausreichend absenkt - siehe
    research/messung-maskierung-arpeggio-vs-rauschen-2026-08-18.md und
    arbeit/messung_ducking.py)."""
    # Die Tonspur muss bis `ende` reichen, nicht nur bis zum letzten Wort:
    # -shortest kappt das Video an der kuerzesten Spur, und der stumme
    # Ausklang mit dem Schlussbild faellt sonst restlos weg (gemessen
    # 19.08.2026: Video 718.4s, letzter Cue 718.5s - der Puffer kam nie an).
    if not BETT.exists():
        return [], [f"[{start}:a]apad=whole_dur={ende:.3f}[mix]"], "[mix]"
    ab = max(ende - BETT_AUSBLENDE, 0.1)
    anhebung = _intro_anhebung(kapitel1)
    return (["-stream_loop", "-1", "-i", str(BETT)],
            # Die gepolsterte Sprache wird zweimal gebraucht - als Trigger des
            # Duckings und als Mischanteil - deshalb asplit. Gepolstert wird
            # vor dem Split, weil sidechaincompress keine framesync-Optionen
            # kennt: endet der Trigger, endet auch sein Ausgang, und die
            # Mischung waere trotz laufendem Bett wieder nur so lang wie die
            # Sprache (gemessen: 5s Sprache, ende=12s -> 5s Mischung).
            [f"[{start}:a]apad=whole_dur={ende:.3f},asplit=2[sp][sck]",
             f"[{start + 1}:a]volume={BETT_DB}dB,"
             f"afade=t=in:st=0:d=2,afade=t=out:st={ab:.2f}:d={BETT_AUSBLENDE}"
             f"[bettg]",
             # sidechaincompress: erstes Label wird komprimiert, zweites ist
             # der Trigger. threshold liegt weit unter dem Sprachpegel und
             # ratio nahe am Limiting, damit praktisch jede aktive Silbe das
             # Bett wegdrueckt; in Sprechpausen federt es ueber `release`
             # zurueck (bei den kurzen, median 0.6s langen Pausen federt es
             # in der Praxis nicht vollstaendig zurueck - siehe
             # arbeit/messung_ducking.py - das ist gewollt: lieber durchgehend
             # unauffaellig als zwischen Silben hoerbar pumpend).
             f"[bettg][sck]sidechaincompress=threshold={DUCK_SCHWELLE}:"
             f"ratio={DUCK_RATIO}:attack={DUCK_ATTACK}:release={DUCK_RELEASE}"
             f"[bettd]",
             f"[bettd]{anhebung}[bett]" if anhebung else "[bettd]anull[bett]",
             # normalize=0 ist Pflicht: mit dem Standard teilt amix durch die
             # Zahl der Eingaenge und die Sprache verliert 6 dB.
             # duration=first haelt die Laenge weiter an der Sprache, damit
             # ein zu kurzes Bett nicht ueber -shortest das Video kappt - die
             # Sprache reicht durch apad jetzt selbst bis `ende`.
             "[sp][bett]amix=inputs=2:duration=first:normalize=0[mix]"],
            "[mix]")


def _loudnorm_gemessen(audio_mp3: Path, ende: float,
                       kapitel1: float = 0.0) -> str:
    """loudnorm-Filter mit den Messwerten eines Analysedurchlaufs.

    Zweipass, weil einpassiges loudnorm vorwaertsblickend regelt und hoerbar
    pumpt; mit measured_* ist es eine reine Verstaerkung. Gemessen wird die
    fertige Mischung, nicht die Sprache allein. Wir liegen ohne diesen
    Schritt bei rund -19.5 LUFS, YouTubes Ziel ist -14 und die Plattform
    hebt nur ab, nie an - der Bericht klingt im Feed also duenner als das
    Nachbarvideo. Scheitert die Messung, bleibt es bei einpassig: lieber
    ungenau normalisiert als kein Video."""
    ziel = f"loudnorm=I={ZIEL_LUFS}:TP=-1.5:LRA=11"
    bett_ein, teile, quelle = _ton_kette(0, ende, kapitel1)
    kette = ";".join([*teile, f"{quelle}{ziel}:print_format=json[m]"])
    try:
        aus = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(audio_mp3),
             *bett_ein, "-filter_complex", kette, "-map", "[m]",
             "-f", "null", "-"],
            capture_output=True, text=True, check=True, timeout=900)
        werte = json.loads(aus.stderr[aus.stderr.rindex("{"):
                                      aus.stderr.rindex("}") + 1])
        return (f"{ziel}:measured_I={werte['input_i']}"
                f":measured_TP={werte['input_tp']}"
                f":measured_LRA={werte['input_lra']}"
                f":measured_thresh={werte['input_thresh']}"
                f":offset={werte['target_offset']}:linear=true")
    except (subprocess.SubprocessError, ValueError, KeyError) as e:
        print(f"Loudness-Messung gescheitert ({e}) - einpassig normalisieren")
        return ziel


def ton_argumente(audio_mp3: Path, ende: float,
                  kapitel1: float = 0.0) -> tuple[list[str], list[str]]:
    """ffmpeg-Argumente fuer die Tonspur: Bett dazu, Endmix auf ZIEL_LUFS.

    Zurueck kommen die Eingabe-Argumente (hinter dem Video-Input) und die
    Ausgabe-Argumente. Beide Renderpfade nutzen dieselbe Funktion, damit ein
    Fallback-Tag nicht anders klingt als die uebrigen. An der Sprachdatei
    selbst wird nichts geaendert: an ihren Wort-Zeitstempeln haengen
    Overlays, Kapitelmarken und Untertitel."""
    bett_ein, teile, quelle = _ton_kette(1, ende, kapitel1)
    # level=false am Limiter ist wichtig: mit dem Standard normalisiert er den
    # Ausgang auf seinen limit-Wert und verschiebt damit die Lautheit, die
    # loudnorm gerade gesetzt hat. So greift er nur noch als Notbremse.
    norm = _loudnorm_gemessen(audio_mp3, ende, kapitel1)
    teile.append(f"{quelle}{norm},alimiter=limit=0.95:level=false[ton]")
    # Stereo und 48 kHz fest: die Sprachdatei ist Mono mit 24 kHz und wuerde
    # das Ausgabeformat sonst vorgeben (gemessen: Mono bei 96 kHz). Das Bett
    # traegt eine leichte Breite aus seinen versetzten Echos - in Mono
    # summiert die weg, und die Stimme bleibt ohnehin in der Mitte.
    return (["-i", str(audio_mp3), *bett_ein],
            ["-filter_complex", ";".join(teile), "-map", "0:v", "-map", "[ton]",
             "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000"])


def szenen_video(folge: list[Szene], audio_mp3: Path, ziel_mp4: Path,
                 arbeit: Path, suffix: str, datum: str, ende: float,
                 kapitel1: float = 0.0) -> None:
    """Alle Szenen rendern, auf dem 25-fps-Frame-Raster nahtlos aneinander
    schneiden (kein Drift zur Tonspur) und mit dem Audio muxen."""
    if not folge:
        raise RuntimeError("keine Szenen")
    bug_pfad, bx, by = szenen.speichern(
        szenen.bug(datum), arbeit / f"overlay{suffix}_bug.png")
    bug = Overlay(bug_pfad, 0.0, 0.0, 0.0, bx, by)
    vig_pfad, vx, vy = szenen.speichern(
        szenen.vignette(), arbeit / f"overlay{suffix}_vignette.png")
    vig = Overlay(vig_pfad, 0.0, 0.0, 0.0, vx, vy)
    grenzen = [round(s.start * FPS) for s in folge]
    grenzen.append(max(int(ende * FPS + 0.5), grenzen[-1] + SZENE_MIN_FRAMES))
    for i in range(1, len(grenzen)):
        grenzen[i] = max(grenzen[i], grenzen[i - 1] + SZENE_MIN_FRAMES)
    def crossfade_motiv(aktuell: Szene, naechste: Szene) -> Path | None:
        # Der Crossfade blendet nur 0.3s lang ein - dafuer reicht immer ein
        # Standbild, auch wenn die Folgeszene animiert ist. Erspart eine
        # zweite -stream_loop-Eingabe fuer eine kaum wahrnehmbare Naht. Der
        # Gleichheits-Check MUSS auf dem rohen Motiv liegen, nicht auf dem
        # Poster: zwei Szenen mit demselben animierten Motiv (Pool-
        # Wiederholung an bildarmen Tagen) sollen wie bisher gar keinen
        # Crossfade zeigen, nicht faelschlich auf das eigene Standbild
        # ueberblenden.
        if naechste.motiv is None or naechste.motiv == aktuell.motiv:
            return None
        return naechste.motiv_poster if naechste.motiv_animiert else naechste.motiv

    clips = [_szene_clip(s, grenzen[i], grenzen[i + 1], i, arbeit, suffix,
                         bug, vig,
                         crossfade_motiv(s, folge[i + 1]) if i + 1 < len(folge) else None,
                         folge[i + 1].zoom_rein if i + 1 < len(folge) else True,
                         schluss=i + 1 == len(folge))
             for i, s in enumerate(folge)]
    liste = arbeit / f"szenen{suffix}.txt"
    liste.write_text(
        "\n".join("file '" + str(c).replace("\\", "/") + "'" for c in clips)
        + "\n", encoding="utf-8")
    ton_ein, ton_aus = ton_argumente(audio_mp3, ende, kapitel1)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", str(liste),
         *ton_ein, "-vf", f"scale={YOUTUBE_W}:{YOUTUBE_H}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", *ton_aus, "-shortest", str(ziel_mp4)],
        check=True, timeout=900, capture_output=True)
    print(f"Szenen-Video: {len(clips)} Szenen, {grenzen[-1] / FPS:.0f} s")


# ----------------------------------------------------------- Video-Zusammenbau

def video_erzeugen(audio_mp3: Path, ass_datei: Path | None, ziel_mp4: Path,
                   konkat: Path | None = None, ende: float = 0.0,
                   kapitel1: float = 0.0) -> None:
    """ass_datei=None ist der Praesentationsmodus: der Text steckt schon in
    den Standbildern der ffconcat-Liste, eingebrannt wird nichts mehr."""
    filter_teile: list[str] = []
    if konkat is not None:
        eingabe = ["-f", "concat", "-safe", "0", "-i", str(konkat)]
        filter_teile.append(f"fps={FPS}")  # Standbilder auf feste Framerate
    else:
        eingabe = ["-f", "lavfi", "-i",
                   f"color=c={HINTERGRUND}:s={CANVAS_W}x{CANVAS_H}"]
    if ass_datei is not None:
        filter_teile.append(
            "ass=" + str(ass_datei).replace("\\", "/").replace(":", r"\:"))
    # Skalierung zuletzt: ASS-Koordinaten und die Standbilder liegen im
    # 1280x720-Raster, erst danach wird fuers YouTube-1080p-Ziel vergroessert.
    filter_teile.append(f"scale={YOUTUBE_W}:{YOUTUBE_H}")
    vf = ",".join(filter_teile)
    # Dieselbe Tonbehandlung wie im Szenen-Pfad: sonst klingt genau der Tag
    # anders, an dem der Fallback greift. -vf trifft den Videostream,
    # -filter_complex nur die Tonspur - sie liegen nicht uebereinander.
    ton_ein, ton_aus = ton_argumente(audio_mp3, ende or _mp3_dauer(audio_mp3),
                                     kapitel1)
    subprocess.run(
        ["ffmpeg", "-y", *eingabe, *ton_ein,
         "-vf", vf,
         "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
         *ton_aus, "-shortest", str(ziel_mp4)],
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
    return entschaerft(titel[:100].rstrip())


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
        return entschaerft(wert.strip())[:THUMB_MAX_ZEICHEN].strip().upper()
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


# Schlagzeilenwoerter, die im Titel gross stehen, aber als Suchbegriff nichts
# taugen. Ohne diese Liste landeten Tags wie "crashes" oder "impossible" beim
# Upload (gemessen 20.08.2026 an den Uploads vom 16.-20.08.).
STOPP_TAGS = frozenset({
    "crashes", "crash", "pumps", "pump", "dumps", "dump", "impossible",
    "vanish", "vanishes", "hits", "cuts", "sets", "same", "day", "days",
    "watch", "only", "about", "their", "own", "the", "and", "for", "with",
    "from", "into", "over", "under", "now", "new", "big", "all", "how",
    "why", "you", "your", "its", "but", "not", "out", "off", "who", "was",
    # Fachkuerzel und Ticker, die als Wort zu mehrdeutig sind, um zu treffen
    "cusip", "app", "link", "ceo", "cfo", "etf", "faq", "usd", "eur", "chf",
    # Rubrikenkoepfe, die als Suchbegriff nichts eingrenzen
    "macro", "glossary", "board life",
})


def _titel_schlagworte(titel: str) -> list[str]:
    """Die Eigennamen des Titels als Tag-Kandidaten: die grossgeschriebenen
    Woerter vor dem Serien-Suffix, einzeln.

    Frueher lieferte hier _thumb_aus_titel() die Vorlage - das ist aber der
    Text fuers Vorschaubild und damit eine gekappte Phrase ("klarna crashes
    $120k"), die als Suchbegriff niemand eingibt. Einzelne Namen wie "klarna"
    oder "moderna" treffen dagegen echte Suchen."""
    ohne_suffix = titel.split(" | ")[0]
    aus: list[str] = []
    for wort in ohne_suffix.split():
        rein = re.sub(r"[^0-9A-Za-zÄÖÜäöü&.-]+", "", wort)
        if len(rein) <= 2 or not rein.isupper() or not rein[0].isalpha():
            continue
        if not rein.isalpha() or rein.lower() in STOPP_TAGS:
            continue  # "120K", "250B" sind Schlagzeilen-Zahlen, keine Suchbegriffe
        aus.append(rein)
    return aus


TAG_MAX_LAENGE = 44  # laengster Kapiteltitel aus folien.json


def _tag_saeubern(roh: str) -> str:
    """Ein Tag-Kandidat in Upload-Form: klein, ohne Satzzeichen-Rauschen.
    Apostrophe fallen ersatzlos weg ("day's" -> "days"), sonst wuerde die
    Zeichenklasse daraus das Fragment "day s" machen."""
    t = roh.replace("'", "").replace("’", "")
    t = re.sub(r"[^0-9A-Za-zÄÖÜäöü$&. -]+", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def _phrase_kuerzen(roh: str) -> str:
    """Eine Themen-Phrase auf ihren suchbaren Kern bringen: der Teil vor dem
    ersten Komma (dahinter beginnt ein zweiter Gedanke), ohne fuehrenden
    Artikel."""
    p = roh.split(",")[0].strip()
    for artikel in ("the ", "a ", "an "):
        if p.lower().startswith(artikel):
            p = p[len(artikel):]
            break
    return p


def tags_bauen(sprache: str, titel: str, bloecke: list[Block],
               markdown: str = "", fdaten: dict | None = None) -> list[str]:
    """Tag-Liste fuer den Upload: die Tagesthemen als vollstaendige
    Suchphrasen, danach die festen Serien-Tags. Quellen, spezifisch vor
    generisch: die Eigennamen des Titels, Firmennamen samt Ticker aus dem
    Bericht, der ##-Ueberschriften-Teil NACH dem Doppelpunkt als Phrase,
    die Kapiteltitel aus folien.json und zuletzt die Themenkoepfe.
    Vorher (gemessen 20.08.2026) blieben nur 108 von 450 Zeichen genutzt,
    darunter Rauschen wie "moderna pumps" (gekapptes Titelfragment).
    Konservativ unter dem 500-Zeichen-Limit gekappt, das YouTube auf die
    Gesamtliste rechnet; die Serien-Tags haben ihr Budget immer sicher."""
    kandidaten = _titel_schlagworte(titel)
    # Ticker stehen im Bericht in Klammern hinter dem Firmennamen
    # ("Klarna (KLAR)") - Name und Ticker sind die praezisesten
    # Suchbegriffe des Tages.
    for name, ticker in re.findall(r"([A-Z][A-Za-z&.-]{2,29})\s+\(([A-Z]{2,5})\)",
                                   markdown):
        kandidaten += [name, ticker]
    kandidaten += re.findall(r"\(([A-Z]{2,5})\)", markdown)
    # Nur Ueberschriften mit Doppelpunkt tragen ein echtes Thema
    # ("MONERO: ..."); die ohne sind generische Serienrubriken
    # ("UNVERAENDERT SEIT GESTERN") und als Suchbegriff wertlos. Der Teil
    # NACH dem Doppelpunkt ist die Suchphrase, der Kopf davor nur Beiwerk.
    koepfe: list[str] = []
    for b in bloecke:
        if b.art == "ueberschrift" and ":" in b.text:
            kopf, thema = b.text.split(":", 1)
            phrase = _phrase_kuerzen(thema)
            if " " in phrase:
                # Ein einzelnes Restwort ("HOUSING: FROZEN, ..." -> "FROZEN")
                # ist keine Suchphrase mehr, nur ein Adjektiv.
                kandidaten.append(phrase)
            koepfe.append(kopf)
    # Die Kapiteltitel aus folien.json (<= 44 Zeichen) sind bereits sauber
    # formulierte Tagesthemen; uebernommen nur fuer Abschnitte, deren
    # ##-Ueberschrift per Doppelpunkt ein echtes Thema traegt.
    for a in (fdaten or {}).get("abschnitte") or []:
        if isinstance(a, dict) and ":" in str(a.get("ueberschrift") or ""):
            kandidaten.append(_phrase_kuerzen(str(a.get("titel") or "")))
    kandidaten += koepfe
    fest = list(FESTE_TAGS[sprache])
    budget = TAGS_MAX_ZEICHEN - sum(len(t) + 2 for t in fest)
    aus: list[str] = []
    laenge = 0
    for roh in kandidaten:
        t = _tag_saeubern(roh)
        if not t or t in STOPP_TAGS or t in aus or t in fest:
            continue  # STOPP_TAGS gilt fuer jede Quelle, auch Ticker "(CUSIP)"
        if not 2 <= len(t) <= TAG_MAX_LAENGE:
            continue
        if laenge + len(t) + 2 > budget:
            continue  # Mehrwort-Tags zaehlen bei YouTube mit Quotes
        laenge += len(t) + 2
        aus.append(t)
    return aus + fest


def kapitel_eins_start(bloecke: list[Block],
                       block_worte: list[list[Wort]]) -> float:
    """Startzeit des ersten gesprochenen Worts der ersten ##-Ueberschrift -
    also das Ende des Vorspanns. 0.0, wenn es keine Ueberschrift gibt; die
    Tonmischung faehrt dann ohne Intro-Anhebung, statt auf einem geratenen
    Zeitpunkt zu arbeiten."""
    for block, worte in zip(bloecke, block_worte):
        if block.art == "ueberschrift" and worte:
            return worte[0].start
    return 0.0


def kapitel_bauen(bloecke: list[Block], block_worte: list[list[Wort]],
                  intro: str) -> str:
    """Kapitelmarken fuer die Beschreibung: je ##-Ueberschrift ein Kapitel ab
    dem Start ihres ersten gesprochenen Worts. YouTube zeigt sie als Kapitel
    und in der Suche als Schluesselmomente, verlangt aber eine erste Marke
    bei 00:00, mindestens drei Marken und 10 s Mindestabstand - sonst lieber
    gar keine Liste als eine halb wirksame.

    intro ist der Titel der 00:00-Marke: "TL;DR", wenn der Zahlenblock
    vorne gesprochen wird (er deckt dann Cold Open + Zahlen ab; eine eigene
    Marke bekommt der Zahlenblock nicht, sie laege <10 s nach 00:00), sonst
    das kapitel_intro der Sprache ("Intro")."""
    zeilen = [f"00:00 {intro}"]
    letzte = 0
    for block, worte in zip(bloecke, block_worte):
        if block.art != "ueberschrift" or not worte:
            continue
        s = int(worte[0].start)
        if s < letzte + 10:
            # Nur das erste Kapitel kann knapp an der Intro-Marke liegen (der
            # Vorspann ist kurz und der Hook schwankt in der Laenge). Es dann
            # fallen zu lassen, waere der lautlose Fehler; die Marke ein paar
            # Sekunden nach hinten zu schieben kostet nichts, weil YouTube nur
            # den Abstand prueft und der Zuschauer die Sekunde nicht merkt.
            if letzte:
                continue
            print(f"Kapitel 1 liegt bei {s}s - Marke auf 10s geschoben, "
                  f"sonst faellt sie unter die 10-Sekunden-Regel")
            s = 10
        letzte = s
        zeit = (f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"
                if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}")
        titel = block.text.replace("<", "").replace(">", "").replace("—", "-")
        # Der Reliability-Tag der Ueberschrift ("[one loud ID]", seit
        # 21.08.2026 Prompt-Regel 4a) gehoert in den Bericht, nicht in den
        # Kapitelnamen: dort waere er nur Rauschen im Player und frisst von
        # der knappen Zeilenbreite. Im gesprochenen Text steht er ohnehin -
        # gestrippt wird nur diese eine Darstellung.
        titel = re.sub(r"\s*\[[^\]]*\]\s*$", "", titel).strip()
        # Harte Laengengrenze, an der Wortgrenze: der Prompt fordert 40
        # Zeichen, aber Prompt-Prosa ist keine Zusicherung - laengere
        # Kapitelnamen schneidet der YouTube-Player selbst ab, und zwar
        # mitten im Wort. Gekappt wird NUR diese Darstellung, nie die
        # Ueberschrift im Bericht: an der haengen die Verbatim-Anker des
        # Drehbuchs.
        if len(titel) > KAPITELNAME_MAX:
            titel = rr._wortgrenze(titel, KAPITELNAME_MAX)
        zeilen.append(f"{zeit} {titel}")
    return "\n".join(zeilen) if len(zeilen) >= 3 else ""


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
    return entschaerft(re.sub(r"[ \t]+", " ", zeile).rstrip())


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
                       datum: str, kapitel: str = "") -> str:
    """Kopfzeile + Hashtags + Kapitelmarken + Berichtstext im Rohtext + Liste
    der Quell-Threads. YouTube laesst nur 5000 Zeichen zu, der Bericht ist gut
    doppelt so lang - deshalb wird an einer Abschnittsgrenze gekappt. Die
    Thread-Links bekommen ihr Budget vorab, sie duerfen der Kappung nie zum
    Opfer fallen - Hashtags und Kapitel ebenso, sie stehen vor dem Text."""
    kopf = cfg["beschreibung"].format(datum=datum) + "\n" + HASHTAG_ZEILE
    if kapitel:
        kopf += "\n\n" + kapitel
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


@dataclass
class Drehbuch:
    """Gemeinsame Sicht von Hauptvideo und Shorts auf den Tag: die Block-
    Struktur des Berichts, die vertonte Blockfolge samt Rahmen-Saetzen und
    die Drehbuch-Daten aus folien.json. In einer Funktion gebuendelt, damit
    shorts.py exakt DENSELBEN Codepfad laeuft wie main() - eine nachgebaute
    Kopie wuerde bei der naechsten Aenderung stumm von der Tonspur abweichen
    und die Schnittgrenzen der Shorts verschieben."""
    bloecke: list[Block]
    abschnitte: list[Abschnitt]
    bloecke_ton: list[Block]
    fdaten: dict | None
    zuordnung: dict[int, dict]
    titel: str
    hook: str
    hook_ton: str


def drehbuch_bauen(tag_dir: Path, markdown: str, sprache: str,
                   datum: str) -> Drehbuch:
    """Baut aus Bericht, titel.json und folien.json die vertonte Blockfolge -
    identisch zu dem, was main() vor der Vertonung tut."""
    cfg = SPRACHEN[sprache]
    bloecke, abschnitte = abschnitte_erzeugen(markdown)
    serien_titel = cfg["titel"].format(datum=datum)
    titel = titel_laden(tag_dir, sprache, serien_titel)
    hook = titel.split(" | ")[0].strip()
    # Gesprochen wird der Aufhaenger nur, wenn er nachweislich einer ist: das
    # Serien-Suffix " | /biz/ <datum>" muss dahinter stehen. Fehlt es, ist der
    # Titel entweder der statische Serientitel (kein Aufhaenger) oder er wurde
    # bei 100 Zeichen gekappt - dann waere der "Hook" ein abgeschnittener Rest.
    hook_ton = hook if " | " in titel and titel != serien_titel else ""
    # Praesentationsmodus (v6/v7): nur englisch und nur mit folien.json; sonst
    # bleibt alles beim v5-Text-Layout. Die Rahmen-Saetze kommen mit in die
    # Vertonung, damit ihre Zeitfenster die Folienwechsel steuern.
    fdaten = folien_laden(tag_dir) if sprache == "en" else None
    zuordnung: dict[int, dict] = {}
    if fdaten:
        zuordnung = folien_zuordnen(fdaten, bloecke)
        bloecke_ton = praesentations_bloecke(bloecke, zuordnung, fdaten, datum,
                                             hook_ton)
    else:
        bloecke_ton = bloecke
    return Drehbuch(bloecke, abschnitte, bloecke_ton, fdaten, zuordnung,
                    titel, hook, hook_ton)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sprache", choices=sorted(SPRACHEN), default="en")
    ap.add_argument("--nur-video", action="store_true",
                    help="Video nur bauen, ohne Upload und ohne Marker (Test); "
                         "laesst den Delta-Zustand unberuehrt: kein "
                         "zuletzt_verwendet-Stempel in arbeit/clips/"
                         "katalog.json")
    ap.add_argument("--trockenlauf", action="store_true",
                    help="einheitliches Dry-Run-Flag der Pipeline; hier "
                         "gleichbedeutend mit --nur-video (kein Upload, kein "
                         "Marker, Delta-Zustand bleibt unberuehrt)")
    ap.add_argument("--trotz-altdaten", action="store_true",
                    help=f"auch hochladen, wenn der Datenstand des Berichts "
                         f"aelter als {DATENSTAND_MAX_H:.0f} h ist")
    ap.add_argument("--bett-bauen", action="store_true",
                    help=f"Musikbett neu synthetisieren ({BETT}) und beenden")
    ap.add_argument("--vorschau", type=float, metavar="SEKUNDEN",
                    default=None,
                    help="nur die ersten N Sekunden des Szenen-Layouts "
                         "bauen (impliziert --nur-video, Test); nutzt "
                         "weiter volle Aufloesung, nur weniger Szenen")
    args = ap.parse_args()
    if args.vorschau is not None or args.trockenlauf:
        args.nur_video = True
    if args.bett_bauen:
        # Bewusst ein eigener Aufruf und nicht "baue es, wenn die Datei
        # fehlt": ein Cron-Lauf soll keine Tonspur erzeugen, die niemand
        # gehoert hat. Fehlt die Datei, laeuft der Tag ohne Musik.
        bett_bauen()
        return
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

    # Frische des Datenstands, bevor irgendetwas Geld oder Rechenzeit kostet.
    # Der Testpfad (--nur-video) prueft nicht: er laedt ohnehin nichts hoch
    # und muss auch an alten Berichten arbeiten koennen.
    alter = datenstand_alter_h(markdown)
    if alter is None:
        print("WARNUNG: keine lesbare Datenstand-Zeile im Bericht - "
              "Frischepruefung uebersprungen")
    else:
        print(f"Datenstand des Berichts: {alter:.1f} h alt")
        if alter > DATENSTAND_MAX_H and not (args.nur_video or args.trotz_altdaten):
            print(f"Datenstand aelter als {DATENSTAND_MAX_H:.0f} h - kein "
                  f"Upload. Das Board liefert offenbar keine neuen Posts "
                  f"(4chan nicht erreichbar oder Crawl ausgefallen); der "
                  f"Bericht waere ein Aufguss mit frischem Titel. Mit "
                  f"--trotz-altdaten trotzdem hochladen.")
            return

    d = drehbuch_bauen(tag_dir, markdown, args.sprache, datum)
    abschnitte = d.abschnitte
    titel, hook, bloecke_ton = d.titel, d.hook, d.bloecke_ton
    fdaten, zuordnung = d.fdaten, d.zuordnung
    print(f"Titel: {titel}")

    arbeit = VIDEO_DIR / datum
    arbeit.mkdir(parents=True, exist_ok=True)
    audio_mp3 = arbeit / f"audio{cfg['suffix']}.mp3"
    ass_datei = arbeit / f"untertitel{cfg['suffix']}.ass"
    video_mp4 = arbeit / f"video{cfg['suffix']}.mp4"

    bild = vorschaubild(arbeit, tag_dir, cfg, args.sprache, datum, titel)
    text = ton_text(bloecke_ton)

    print("erzeuge Vertonung mit Wort-Zeitstempeln ...")
    worte = ton_holen(text, audio_mp3, cfg, args.nur_video)
    print(f"{len(worte)} Woerter erkannt")
    block_worte = worte_zu_bloecken(worte, bloecke_ton)
    sprech_ende = worte[-1].end if worte else 0.0
    ende = sprech_ende + AUSKLANG  # stummer Ausklang, siehe _ton_kette
    kapitel1 = kapitel_eins_start(bloecke_ton, block_worte)
    if kapitel1:
        print(f"Vorspann bis {kapitel1:.1f}s - Bett dort "
              f"{BETT_INTRO_ANHEBUNG:.0f} dB lauter")

    srt_pfad = arbeit / f"untertitel{cfg['suffix']}.srt"
    srt_datei: Path | None = srt_pfad
    try:
        print(f"Untertitel: {srt_erzeugen(worte, srt_pfad)} Cues "
              f"({srt_pfad.name})")
    except OSError as e:
        # Untertitel sind Beigabe - ohne sie greift die YouTube-Automatik.
        print(f"Untertitel nicht erzeugt: {e}")
        srt_datei = None

    if args.vorschau is not None and not (
            fdaten and int(fdaten.get("version") or 1) >= 2):
        print("Vorschau nur im Szenen-Layout (v7) unterstuetzt - "
              "kein folien.json v2 vorhanden, baue komplett")

    fertig = False
    if fdaten and int(fdaten.get("version") or 1) >= 2:
        # Szenen-Layout (v7): Drehbuch-folien.json mit Stichworten,
        # Zwischenthemen, Zitaten und Kennzahlen.
        try:
            folge = szenen_bauen(bloecke_ton, block_worte, abschnitte,
                                 zuordnung, fdaten, hook, datum, arbeit, ende,
                                 thumb_text_laden(tag_dir, args.sprache,
                                                  titel),
                                 sprech_ende=sprech_ende,
                                 nur_video=args.nur_video)
            ende_bauen = ende
            if args.vorschau is not None:
                voll = len(folge)
                ende_bauen = min(ende, args.vorschau)
                folge = [s for s in folge if s.start < ende_bauen] or folge[:1]
                print(f"Vorschau: nur die ersten {ende_bauen:.0f} s "
                      f"({len(folge)} von {voll} Szenen)")
            print("baue Szenen-Video ...")
            szenen_video(folge, audio_mp3, video_mp4, arbeit, cfg["suffix"],
                         datum, ende_bauen, kapitel1)
            fertig = True
        except Exception as e:
            # Kein Layout-Problem darf den Upload verhindern.
            print(f"Szenen-Aufbau fehlgeschlagen ({e}) - Ersatz-Layout")
    konkat: Path | None = None
    ass_arg: Path | None = None
    if not fertig and fdaten and int(fdaten.get("version") or 1) < 2:
        # Alte folien.json ohne Version: v6-Folien-Praesentation.
        try:
            konkat = folien_konkat(bloecke_ton, block_worte, abschnitte,
                                   zuordnung, fdaten, hook, datum, arbeit,
                                   cfg["suffix"], ende)
        except Exception as e:
            # Die Praesentation darf den Upload nie verhindern: dieselbe
            # Vertonung laeuft dann im v5-Text-Layout weiter (die
            # Rahmen-Saetze erscheinen dort als gewoehnliche Absaetze).
            print(f"Folien-Aufbau fehlgeschlagen ({e}) - Text-Layout als Ersatz")
            konkat = None
    if not fertig and konkat is None:
        anzeigen = anzeigen_bauen(bloecke_ton, block_worte, fonts_laden())
        print(f"{len(anzeigen)} Anzeigen in {len(bloecke_ton)} Bloecken, "
              f"{len(abschnitte)} Abschnitte")
        ass_erzeugen(anzeigen, ass_datei)
        ass_arg = ass_datei
        try:
            plan = hintergrund_plan(bloecke_ton, block_worte, abschnitte,
                                    datum, ende)
            konkat = hintergrund_liste(plan, arbeit, cfg["suffix"])
            print(f"Hintergrund: {len(plan)} Standbilder")
        except Exception as e:
            # Ohne Hintergrund entsteht das Video wie bisher auf der Grundflaeche.
            print(f"Hintergrund nicht aufgebaut ({e}) - nehme die Grundflaeche")

    if not fertig:
        print("baue Video ...")
        video_erzeugen(audio_mp3, ass_arg, video_mp4, konkat, ende)

    if args.nur_video:
        print(f"nur Video gebaut, kein Upload: {video_mp4}")
        return

    kurz = cfg["beschreibung"].format(datum=datum)
    try:
        # Mit dem TL;DR-Zahlenblock vorne heisst die 00:00-Marke "TL;DR"
        # (sie deckt Cold Open + Zahlen ab), sonst wie bisher "Intro".
        kapitel = kapitel_bauen(bloecke_ton, block_worte,
                                "TL;DR" if zahlen_vorne(bloecke_ton)
                                else cfg["kapitel_intro"])
        beschreibung = beschreibung_bauen(tag_dir, markdown, cfg, datum, kapitel)
    except Exception as e:
        # Ein Fehler beim Zusammenbau darf den Upload nie verhindern.
        print(f"Beschreibung nicht aufgebaut ({e}) - nehme nur die Kopfzeile")
        beschreibung = kurz
    print("lade auf YouTube hoch ...")
    tags = tags_bauen(args.sprache, titel, bloecke_ton, markdown, fdaten)
    try:
        video_id, url = youtube_auth.hochladen(video_mp4, titel, beschreibung,
                                               privacy_status="private",
                                               tags=tags, sprache=args.sprache)
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
                                               privacy_status="private",
                                               tags=tags, sprache=args.sprache)
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

    # Eigene Untertitel-Spur: praezisere Zeiten und saubere Satz-Cues statt
    # der YouTube-Automatik. captions.insert braucht den force-ssl-Scope -
    # traegt der Token nur youtube.upload, kommt 403 und es bleibt bei den
    # Auto-Untertiteln; der gelungene Upload ist davon unberuehrt.
    if srt_datei is not None and srt_datei.exists():
        try:
            youtube_auth.untertitel_setzen(video_id, srt_datei, args.sprache)
            print(f"Untertitel hochgeladen ({srt_datei.name})")
        except (RuntimeError, OSError) as e:
            print(f"Untertitel nicht hochgeladen: {e}")

    # Serien-Playlist: haelt die Tagesberichte als Reihe zusammen, statt sie
    # nur einzeln im Kanal liegen zu lassen. Der neueste Bericht steht vorn
    # (position 0), das ist bei einer Tagesreihe die nuetzliche Reihenfolge.
    # Scheitert der Eintrag, bleibt der Upload gueltig - nachtragen laesst
    # sich das jederzeit.
    playlist_id = cfg.get("playlist")
    if playlist_id:
        try:
            youtube_auth.playlist_eintragen(video_id, playlist_id)
            print(f"in Playlist eingehaengt ({playlist_id})")
        except RuntimeError as e:
            print(f"Playlist-Eintrag nicht gesetzt: {e}")

    # Kanal-Trailer: das Video, das die Kanalseite Besuchern ohne Abo oben
    # zeigt. Bei einer Tagesreihe soll dort der neueste Bericht stehen, nicht
    # der vom Tag der Einrichtung. Auch das darf den Upload nicht entwerten.
    try:
        if youtube_auth.kanal_trailer_setzen(video_id):
            print("als Kanal-Trailer gesetzt")
    except RuntimeError as e:
        print(f"Kanal-Trailer nicht gesetzt: {e}")

    # Erst jetzt oeffentlich schalten: bis hierher lief das Video unter
    # "privat", damit niemand es ohne Vorschaubild, Untertitel oder
    # Playlist-Eintrag zu sehen bekommt. Schlaegt das fehl, bleibt das Video
    # bewusst privat statt halbfertig oeffentlich zu stehen - der Fehler
    # muss auffallen, statt stillschweigend uebergangen zu werden.
    youtube_auth.status_setzen(video_id, "public")
    print("auf oeffentlich geschaltet")


if __name__ == "__main__":
    main()
