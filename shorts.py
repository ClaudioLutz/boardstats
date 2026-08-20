#!/usr/bin/env python3
"""Schneidet aus dem fertigen Tagesvideo-Material ein YouTube-Short pro
##-Story des Berichts (9:16, maximal ~3 Minuten) und laedt sie einzeln hoch.

Hintergrund (Brainstorm 20.08.2026, Prio 2): 43 von 54 Views kommen ueber
die YouTube-Suche, aber Suchanfragen zu einzelnen Storys/Tickern treffen
auf ein 10-Minuten-Tagesvideo statt auf das passende Segment. Ein Short je
Story mit story-spezifischem Titel und Tags gibt jeder Story einen eigenen
Suchtreffer; das Tagesvideo bleibt unveraendert das Hauptprodukt.

Eigenstaendiger Pipeline-Schritt (eigene Failure-Domain), aufgerufen in
video.sh NACH dem Hauptvideo - ein Fehler hier darf weder die uebrigen
Shorts noch den Cron-Lauf kippen (try/except je Story, Exit-Code 0, solange
das Skript selbst lief).

Es wird NICHT neu vertont: die Tonspur ist ein Ausschnitt aus
video/<datum>/audio_en.mp3, geschnitten an den Wort-Zeitstempeln der
Kapitelgrenzen (audio_en.worte.json; Ersatzweise aus untertitel_en.srt
rekonstruiert). Die Blockfolge kommt ueber video_report.drehbuch_bauen() -
exakt derselbe Codepfad wie beim Hauptvideo, damit die Schnittgrenzen zur
Tonspur passen. Ein Aehnlichkeits-Guard (Wortstrom gegen Blocktexte)
verhindert Schnitte auf einer Tonspur, die nicht zum aktuellen Bericht
gehoert (z. B. Bericht abends regeneriert, Audio vom Morgenlauf).

Bild: eigenes, schlichtes 1080x1920-Layout (Titel oben, Stichworte gross
und progressiv ueber die Anker-Zeitstempel aus folien.json eingeblendet,
Kennzahl-Karte falls vorhanden). Dahinter liegt ueber die ganze Laufzeit
das Kapitel-Motiv des Hauptvideos (arbeit/motive/, Zuordnung ueber
vr.MotivWahl - Story i traegt dasselbe Motiv wie Kapitel i), formatfuellend
zugeschnitten und per Scrim abgedunkelt; ohne freigegebene Bilder rendert
das Short wie bisher auf dem Farbtheme. Farb- und Schrift-Vokabular kommt
aus design_tokens.py und thumbnail.py, die Shorts-UI-Zonen (untere ~420 px,
rechte ~190 px) bleiben frei.

Marker extrakte/<datum>/shorts_en.json haelt die hochgeladenen Storys fest
(inkrementell nach jedem Upload geschrieben); ein Wiederanlauf ueberspringt
sie. Wie video_en.json wird der Marker nicht von hier aus committet - der
naechste Report-Lauf nimmt ihn mit.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import design_tokens
import thumbnail
import video_report as vr
import youtube_auth

# ----------------------------------------------------------- Auswahl/Kappung

MAX_DAUER = 175.0   # laengere Storys ueberspringen (Shorts-Limit 3 min)
MIN_DAUER = 20.0    # kuerzere ebenso (kein Substanz-Short)
VORLAUF = 0.20      # Sekunden Ton vor dem ersten Wort der Ueberschrift
NACHLAUF = 0.50     # Sekunden Ton nach dem letzten Wort der Story
FADE = 0.15         # Sekunden Ein-/Ausblende an den Schnittkanten
BETT_DB = -22.0     # Musikbett so viel leiser als die Sprache (falls vorhanden)
AEHNLICHKEIT_MIN = 0.90  # Wortstrom muss so gut zum Bericht passen

# ----------------------------------------------------------- Layout 1080x1920

B, H = 1080, 1920
RAND = 72                 # linker/rechter Grundrand
# Shorts-UI-Schutzzonen: unten legt YouTube Titel/Kanal/Beschreibung ueber
# das Bild, rechts die Like/Kommentar-Spalte - dort steht kein eigener Text.
SAFE_UNTEN = 420
SAFE_RECHTS = 190
INHALT_B = B - RAND - SAFE_RECHTS   # nutzbare Textbreite

GRUND = design_tokens.NEUTRAL[9]
AKZENT = design_tokens.AKZENT[6]
HELL = design_tokens.WEISS
GRAU = design_tokens.NEUTRAL[3]
ALT = design_tokens.NEUTRAL[2]
KARTE_BG = design_tokens.NEUTRAL[8]

KOPF_Y = 96
KOPF_TEXT = "4CHAN /biz/  ·  BOARD REPORT"
TITEL_Y = 250
TITEL_FONT = 84
TITEL_ZEILE = 98
KICKER_FONT = 34
PUNKT_FONT = 46
PUNKT_ZEILE = 58
PUNKT_LUECKE = 30
PUNKT_QUADRAT = 14
PUNKT_EINZUG = 34
KARTE_HOEHE = 250
KARTE_UNTEN = H - SAFE_UNTEN - 40   # Unterkante der Kennzahl-Karte
MIN_STAND = 0.35    # Sekunden; naeher liegende Einblendungen werden geschoben

FFMPEG = "ffmpeg"


# ----------------------------------------------------------- Wortstrom laden

_SRT_ZEIT = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")


def _s(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def srt_worte(pfad: Path) -> list[vr.Wort]:
    """Wort-Zeitstempel naeherungsweise aus der SRT-Untertiteldatei: die
    Cue-Grenzen sind exakt (sie stammen aus denselben Wortzeiten), innerhalb
    eines Cues werden die Wortzeiten nach Zeichenlaenge verteilt. Reicht fuer
    Kapitelgrenzen, weil jede ##-Ueberschrift nach der langen Kapitelpause
    ihren eigenen Cue beginnt."""
    worte: list[vr.Wort] = []
    for block in pfad.read_text(encoding="utf-8").split("\n\n"):
        zeilen = [z for z in block.splitlines() if z.strip()]
        if len(zeilen) < 2:
            continue
        m = _SRT_ZEIT.search(zeilen[1] if zeilen[0].isdigit() else zeilen[0])
        if not m:
            continue
        start, ende = _s(*m.groups()[:4]), _s(*m.groups()[4:])
        text_zeilen = zeilen[2:] if zeilen[0].isdigit() else zeilen[1:]
        toks = " ".join(text_zeilen).split()
        if not toks:
            continue
        gesamt = sum(len(t) + 1 for t in toks)
        lauf = start
        for t in toks:
            anteil = (len(t) + 1) / gesamt * (ende - start)
            worte.append(vr.Wort(t, lauf, min(ende, lauf + anteil)))
            lauf += anteil
    return worte


def worte_laden(arbeit: Path, suffix: str) -> tuple[list[vr.Wort], str]:
    """Wortstrom der Tages-Tonspur: bevorzugt der exakte Ton-Cache
    (audio_en.worte.json), sonst die SRT-Naeherung. Der Cache-Schluessel wird
    bewusst ignoriert (er haengt an der Stimmkonfiguration); ob der Strom zum
    Bericht passt, entscheidet text_aehnlichkeit()."""
    cache = arbeit / f"audio{suffix}.worte.json"
    if cache.exists():
        try:
            d = json.loads(cache.read_text(encoding="utf-8"))
            worte = [vr.Wort(str(w[0]), float(w[1]), float(w[2]))
                     for w in d["worte"]]
            if worte:
                return worte, cache.name
        except (OSError, ValueError, TypeError, KeyError, IndexError) as e:
            print(f"Ton-Cache unbrauchbar ({e}) - versuche SRT")
    srt = arbeit / f"untertitel{suffix}.srt"
    if srt.exists():
        worte = srt_worte(srt)
        if worte:
            return worte, srt.name
    return [], ""


def text_aehnlichkeit(worte: list[vr.Wort], bloecke: list[vr.Block]) -> float:
    """Wie gut der Wortstrom der Tonspur zum aktuellen Bericht passt (0..1).
    Faellt der Wert, gehoert die Tonspur zu einem anderen Berichtsstand
    (z. B. abends regenerierter Bericht bei Tonspur vom Morgenlauf) - dann
    waeren alle Schnittgrenzen stumm falsch."""
    a = vr._norm_text(" ".join(w.text for w in worte))
    b = vr._norm_text(" ".join(bl.text for bl in bloecke))
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


# ----------------------------------------------------------- Story-Segmente

@dataclass
class Story:
    nr: int                    # Abschnittsindex (je ##-Ueberschrift einer)
    bloecke: list[vr.Block]    # Ueberschrift + zugehoerige Berichtsbloecke
    worte: list[vr.Wort]       # deren Wort-Zeitfenster, flach

    @property
    def start(self) -> float:
        return self.worte[0].start

    @property
    def ende(self) -> float:
        return self.worte[-1].end


def story_grenzen(bloecke: list[vr.Block]) -> list[tuple[int, int, int]]:
    """Blockbereiche der Storys: je ##-Ueberschrift (von, bis_exklusiv,
    abschnitt). Eine Story endet an der naechsten Ueberschrift oder am ersten
    Rahmen-Block (rolle != "", z. B. outro)."""
    aus: list[tuple[int, int, int]] = []
    von: int | None = None
    for i, b in enumerate(bloecke):
        grenze = b.art == "ueberschrift" or b.rolle != ""
        if von is not None and grenze:
            aus.append((von, i, bloecke[von].abschnitt))
            von = None
        if b.art == "ueberschrift" and b.rolle == "":
            von = i
    if von is not None:
        aus.append((von, len(bloecke), bloecke[von].abschnitt))
    return aus


def _phrase_suchen(phrase: str, toks: list[str],
                   ab: int = 0) -> tuple[int, int] | None:
    """Erste Fundstelle der Phrase im normalisierten Tokenstrom ab Index ab:
    (von, bis_exklusiv) oder None."""
    ziel = [t for t in (vr._norm_text(w) for w in phrase.split()) if t]
    if not ziel:
        return None
    for i in range(max(0, ab), len(toks) - len(ziel) + 1):
        if toks[i:i + len(ziel)] == ziel:
            return i, i + len(ziel)
    return None


# Rahmen-Saetze, an denen die letzte Story endet: der Outro-Satz und der
# Zahlenblock-Kopf (aktuelle wie fruehere Formulierung - die Tonspur des
# Tages kann von einem aelteren Codestand stammen als der Bericht).
ENDE_PHRASEN = [vr.PRAES_OUTRO, vr.PRAES_ZAHLEN, "Before we wrap up"]


def stories_finden(bloecke: list[vr.Block],
                   worte: list[vr.Wort]) -> list[Story]:
    """Die Storys direkt im Wortstrom der Tonspur lokalisieren: jede
    ##-Ueberschrift wird als Phrase gesucht (sequenziell, in Berichts-
    Reihenfolge), die Story laeuft bis zur naechsten Ueberschrift bzw. bis
    zum ersten Rahmen-Satz danach (Outro/Zahlenblock).

    Bewusst NICHT ueber worte_zu_bloecken: dessen Token-Zeiger reisst ab,
    wenn die Tonspur mit einer anderen Rahmen-Reihenfolge gebaut wurde als
    der aktuelle Codestand sie rekonstruiert (so geschehen 20.08.2026:
    Morgen-Audio mit Agenda vorne, Abend-Code mit TL;DR vorne) - die
    Ueberschrift-Phrasen selbst stehen dagegen in jeder Fassung woertlich im
    Strom."""
    toks = [vr._norm_text(w.text) for w in worte]
    grenzen = story_grenzen(bloecke)
    funde: list[tuple[int, int, int, int]] = []   # (von,bis,nr,block_von)
    ab = 0
    for block_von, _, nr in grenzen:
        fund = _phrase_suchen(bloecke[block_von].text, toks, ab)
        if fund is None:
            print(f"Ueberschrift von Abschnitt {nr} nicht in der Tonspur "
                  f"gefunden - Story uebersprungen")
            continue
        funde.append((fund[0], fund[1], nr, block_von))
        ab = fund[1]
    aus: list[Story] = []
    for i, (von, bis, nr, block_von) in enumerate(funde):
        if i + 1 < len(funde):
            ende_idx = funde[i + 1][0]
        else:
            ende_idx = len(worte)
            for phrase in ENDE_PHRASEN:
                fund = _phrase_suchen(phrase, toks, bis)
                if fund is not None:
                    ende_idx = min(ende_idx, fund[0])
        block_bis = next(b for v, b, n in grenzen if v == block_von)
        if ende_idx > von:
            aus.append(Story(nr, bloecke[block_von:block_bis],
                             worte[von:ende_idx]))
    return aus


# ----------------------------------------------------------- Metadaten

_TICKER = re.compile(r"\(([A-Z]{2,5})\)")


def ticker_finden(text: str) -> str | None:
    """Erster Boersen-Ticker der Story ("Klarna (KLAR)"); Klammer-Kuerzel,
    die keine Ticker sind, filtert die STOPP_TAGS-Liste."""
    for t in _TICKER.findall(text):
        if t.lower() not in vr.STOPP_TAGS:
            return t
    return None


def short_titel(kap_titel: str, ticker: str | None, datum: str) -> str:
    """Story-Titel + Ticker + Serien-Suffix, hoechstens 100 Zeichen. Kein
    "#Shorts" noetig - die Erkennung laeuft ueber Format und Laenge."""
    suffix = f" | /biz/ {datum}"
    kern = vr.entschaerft(kap_titel.strip())
    if ticker and f"({ticker})" not in kern and ticker not in kern.split():
        mit = f"{kern} ({ticker})"
        if len(mit) + len(suffix) <= 100:
            kern = mit
    if len(kern) + len(suffix) > 100:
        kern = kern[:100 - len(suffix) - 1].rstrip() + "…"
    return kern + suffix


def story_hashtag(kap_titel: str, ticker: str | None) -> str:
    roh = ticker or (kap_titel.split() or ["biz"])[0]
    tag = re.sub(r"[^0-9A-Za-z]+", "", roh).lower()
    return tag or "biz"


SHORT_SERIEN_TAGS = ["4chan", "biz", "finance"]


def short_tags(kap_titel: str, ueberschrift: str, story_text: str) -> list[str]:
    """Story-spezifische Tags (Ticker, Firmenname, Themenphrase) vor wenigen
    Serien-Tags - gleiche Saeuberung und Budget-Logik wie tags_bauen()."""
    kandidaten: list[str] = []
    for name, tick in re.findall(
            r"([A-Z][A-Za-z&.-]{2,29})\s+\(([A-Z]{2,5})\)", story_text):
        kandidaten += [name, tick]
    t = ticker_finden(story_text)
    if t:
        kandidaten.append(t)
    if ":" in ueberschrift:
        kopf, thema = ueberschrift.split(":", 1)
        phrase = vr._phrase_kuerzen(thema)
        if " " in phrase:
            kandidaten.append(phrase)
        kandidaten.append(kopf)
    kandidaten.append(vr._phrase_kuerzen(kap_titel))
    fest = list(SHORT_SERIEN_TAGS)
    budget = vr.TAGS_MAX_ZEICHEN - sum(len(x) + 2 for x in fest)
    aus: list[str] = []
    laenge = 0
    for roh in kandidaten:
        tag = vr._tag_saeubern(roh)
        if not tag or tag in vr.STOPP_TAGS or tag in aus or tag in fest:
            continue
        if not 2 <= len(tag) <= vr.TAG_MAX_LAENGE:
            continue
        if laenge + len(tag) + 2 > budget:
            continue
        laenge += len(tag) + 2
        aus.append(tag)
    return aus + fest


def tagesvideo_url(tag_dir: Path, marker_name: str) -> str:
    try:
        d = json.loads((tag_dir / marker_name).read_text(encoding="utf-8"))
        return str(d.get("url") or "")
    except (OSError, ValueError):
        return ""


def short_beschreibung(story: Story, kap_titel: str, ticker: str | None,
                       datum: str, tag_dir: Path, marker_name: str,
                       abschnitte: list[vr.Abschnitt]) -> str:
    """1-2 Saetze zur Story, Hashtags, Link aufs Tagesvideo und die
    Quell-Threads des Kapitels."""
    kopf = story.bloecke[0].text.rstrip(".") if story.bloecke else kap_titel
    zeilen = [vr.entschaerft(
        f"{kopf}. One story from the daily 4chan /biz/ situation report, "
        f"{datum}. Discourse documentation, not financial advice."),
        f"#biz #4chan #{story_hashtag(kap_titel, ticker)}"]
    url = tagesvideo_url(tag_dir, marker_name)
    if url:
        zeilen.append(f"\nFull report of the day: {url}")
    threads = (abschnitte[story.nr].threads
               if 0 <= story.nr < len(abschnitte) else [])
    if threads:
        zeilen.append("\nSource threads (4chan deletes them after a few days):")
        zeilen += [f"https://boards.4chan.org/biz/thread/{t}" for t in threads]
    text = "\n".join(zeilen)
    return text.replace("<", "").replace(">", "")


# ----------------------------------------------------------- Motiv-Hintergrund

SCRIM = 0.60        # Anteil GRUND-Farbe ueber dem ganzen Motiv
SCRIM_OBEN = 0.40   # zusaetzliche Abdunkelung am oberen Rand (Titel/Stichworte)
SCRIM_BODEN = 1250  # bis hier klingt der Zusatz-Scrim linear auf 0 ab


def story_motive(datum: str, bloecke: list[vr.Block],
                 abschnitte: list[vr.Abschnitt]) -> dict[int, Path]:
    """Kapitel-Motiv je Abschnittsindex - exakt die Zuordnung, mit der das
    Hauptvideo seine Kapitel belegt (vr.MotivWahl: die Kapitel-Reservierung
    ist dort der erste Pool-Zugriff auf frischem Zustand, eine frische
    MotivWahl liefert also identische Motive). Animierte Motive (GIF/WebM/
    MP4) werden durch ihr Posterframe ersetzt - die Shorts sind eine reine
    Standbild-Pipeline; die Clip-Zuteilung des Hauptvideos (Kapitel mit
    WebM-Clip als Opener) bleibt bewusst aussen vor.

    Leer, wenn der Tag keine freigegebenen Hintergrundbilder hat - dann
    rendern die Shorts wie bisher auf dem Farbtheme (der tages_motiv-
    Rueckfall des Hauptvideos gilt hier absichtlich nicht: das Vorschaubild
    passt inhaltlich auf keine einzelne Story)."""
    wahl = vr.MotivWahl(datum)
    if not wahl.pool:
        print("keine freigegebenen Hintergrundbilder - Shorts auf Farbtheme")
        return {}
    nrs = [nr for _, _, nr in story_grenzen(bloecke)]
    _, motive = wahl.kapitel_reservieren(abschnitte, nrs)
    typen = vr.motiv_typen(datum)
    poster = vr.motiv_poster_pfade(datum)
    aus: dict[int, Path] = {}
    for nr, m in zip(nrs, motive):
        if m is None:
            continue
        if typen.get(m.name) == "animiert":
            p = poster.get(m.name)
            if p is None:
                print(f"animiertes Motiv {m.name} ohne Posterframe - "
                      f"Story {nr} auf Farbtheme")
                continue
            m = p
        aus[nr] = m
    return aus


def hintergrund_bauen(motiv: Path) -> Image.Image | None:
    """Formatfuellender 1080x1920-Hintergrund aus dem Kapitel-Motiv:
    leicht skalierter Center-Crop plus Scrim (GRUND-Abdunkelung), damit
    Titel, Stichworte und Kennzahl-Karte lesbar bleiben. None, wenn das
    Motiv nicht lesbar ist (dann Farbtheme wie bisher)."""
    try:
        with Image.open(motiv) as roh:
            bild = roh.convert("RGB")
    except (OSError, ValueError) as e:
        print(f"Motiv {motiv.name} nicht lesbar ({e}) - Farbtheme")
        return None
    faktor = max(B / bild.width, H / bild.height)
    bild = bild.resize((max(B, round(bild.width * faktor)),
                        max(H, round(bild.height * faktor))),
                       Image.Resampling.LANCZOS)
    x = (bild.width - B) // 2
    y = (bild.height - H) // 2
    bild = bild.crop((x, y, x + B, y + H))
    grund = Image.new("RGB", (B, H), GRUND)
    bild = Image.blend(bild, grund, SCRIM)
    # Die Titel-/Stichwort-Zone oben braucht mehr Deckung als der Rest:
    # helle Motivpartien (weisse Meme-Flaechen) fressen sonst die gedimmten
    # grauen Stichworte. Linear abklingender Zusatz-Scrim statt mehr
    # Uniform-Scrim, damit das Motiv in der unteren Haelfte sichtbar bleibt.
    verlauf = Image.new("L", (1, H))
    verlauf.putdata([
        round(255 * SCRIM_OBEN * max(0.0, 1.0 - zeile / SCRIM_BODEN))
        for zeile in range(H)])
    bild.paste(grund, (0, 0), verlauf.resize((B, H)))
    return bild


# ----------------------------------------------------------- Bildaufbau

def _wrap(d: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
          max_b: int) -> list[str]:
    zeilen: list[str] = []
    akt = ""
    for wort in text.split():
        probe = f"{akt} {wort}".strip()
        if akt and d.textlength(probe, font=font) > max_b:
            zeilen.append(akt)
            akt = wort
        else:
            akt = probe
    if akt:
        zeilen.append(akt)
    return zeilen


@dataclass
class Einblendung:
    zeit: float          # Sekunden relativ zum Short-Anfang
    stichworte: int      # so viele Stichworte sind sichtbar
    karte: bool          # Kennzahl-Karte sichtbar


def einblendungen(stich_zeiten: list[float | None],
                  karte_zeit: float | None, dauer: float) -> list[Einblendung]:
    """Zustandsfolge des Standbilds: Start nur mit Titel (Frame 1 ist das
    Shorts-Vorschaubild), dann je Anker-Zeit ein Stichwort mehr, die Karte ab
    ihrer Anker-Zeit. Stichworte ohne gefundenen Anker erscheinen mit ihrem
    Vorgaenger; zu dichte Wechsel werden auf MIN_STAND auseinandergeschoben."""
    folge = [Einblendung(0.0, 0, karte_zeit is not None and karte_zeit <= 0)]
    roh: list[tuple[float, str]] = []
    letzte = 0.0
    for z in stich_zeiten:
        if z is not None and z > letzte:
            letzte = z
        roh.append((letzte, "stich"))
    if karte_zeit is not None and karte_zeit > 0:
        roh.append((karte_zeit, "karte"))
    roh.sort(key=lambda e: e[0])
    n, karte = 0, folge[0].karte
    for zeit, art in roh:
        if art == "stich":
            n += 1
        else:
            karte = True
        zeit = max(zeit, folge[-1].zeit + MIN_STAND)
        if zeit >= dauer - 0.3:
            zeit = max(folge[-1].zeit + MIN_STAND, dauer - 0.3)
        if abs(zeit - folge[-1].zeit) < 1e-6 or (
                folge[-1].zeit >= zeit and len(folge) > 1):
            folge[-1] = Einblendung(folge[-1].zeit, n, karte)
        else:
            folge.append(Einblendung(zeit, n, karte))
    return folge


def _karte_zeichnen(d: ImageDraw.ImageDraw, karte: dict) -> None:
    x0, y1 = RAND, KARTE_UNTEN
    x1, y0 = B - SAFE_RECHTS, KARTE_UNTEN - KARTE_HOEHE
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=KARTE_BG,
                        outline=AKZENT, width=3)
    wert = str(karte.get("wert") or "")
    titel = str(karte.get("titel") or "")
    sub = str(karte.get("sub") or "")
    f_wert = thumbnail.schrift_mono(88)
    while wert and d.textlength(wert, font=f_wert) > x1 - x0 - 72:
        f_wert = thumbnail.schrift_mono(int(f_wert.size) - 6)
    d.text((x0 + 36, y0 + 30), wert, font=f_wert, fill=AKZENT)
    d.text((x0 + 36, y0 + 148), titel, font=thumbnail.schrift(True, 34),
           fill=HELL)
    d.text((x0 + 36, y0 + 194), sub, font=thumbnail.schrift_medium(28),
           fill=GRAU)


def frame_bauen(kicker: str, titel: str, punkte: list[str], sichtbar: int,
                karte: dict | None, karte_an: bool, datum: str,
                hintergrund: Image.Image | None = None) -> Image.Image:
    """Ein Standbild-Zustand des Shorts (1080x1920). Mit hintergrund liegt
    das abgedunkelte Kapitel-Motiv unter dem Text (siehe hintergrund_bauen),
    sonst die Farbflaeche wie bisher."""
    bild = (hintergrund.copy() if hintergrund is not None
            else Image.new("RGB", (B, H), GRUND))
    d = ImageDraw.Draw(bild)

    # Kopfzeile: Serienmarke links, Datum rechts, Amber-Linie darunter.
    d.text((RAND, KOPF_Y), KOPF_TEXT, font=thumbnail.schrift(True, 34),
           fill=AKZENT)
    fb = thumbnail.schrift_medium(34)
    d.text((B - RAND - d.textlength(datum, font=fb), KOPF_Y), datum,
           font=fb, fill=GRAU)
    d.rectangle([RAND, KOPF_Y + 62, B - RAND, KOPF_Y + 66], fill=AKZENT)

    # Kicker (Rubrik) und Story-Titel.
    y = TITEL_Y
    if kicker:
        fk = thumbnail.schrift_medium(KICKER_FONT)
        text = kicker.upper()
        while text and d.textlength(text + "…", font=fk) > B - 2 * RAND:
            text = text[:-1].rstrip()
        if text != kicker.upper():
            text += "…"
        d.text((RAND, y - 56), text, font=fk, fill=GRAU)
    f_titel = thumbnail.schrift(True, TITEL_FONT)
    titel_zeilen = _wrap(d, titel, f_titel, B - 2 * RAND)
    if len(titel_zeilen) > 4:
        f_titel = thumbnail.schrift(True, 68)
        titel_zeilen = _wrap(d, titel, f_titel, B - 2 * RAND)
    zh = int(TITEL_ZEILE * f_titel.size / TITEL_FONT)
    for z in titel_zeilen:
        d.text((RAND, y), z, font=f_titel, fill=HELL)
        y += zh
    y += 54

    # Stichworte: die juengsten zuerst weiss, aeltere gedimmt; es bleiben nur
    # so viele stehen, wie zwischen Titel und Karte/Schutzzone Platz haben.
    boden = (KARTE_UNTEN - KARTE_HOEHE - 40) if (karte and karte_an) \
        else (H - SAFE_UNTEN - 20)
    f_punkt = thumbnail.schrift_medium(PUNKT_FONT)
    bloecke: list[list[str]] = [
        _wrap(d, p, f_punkt, INHALT_B - PUNKT_EINZUG)
        for p in punkte[:max(0, sichtbar)]]
    # von hinten (neueste) so viele nehmen, wie in die Hoehe passen
    hoehen = [len(z) * PUNKT_ZEILE + PUNKT_LUECKE for z in bloecke]
    genommen = 0
    frei = boden - y
    for h in reversed(hoehen):
        if frei - h < 0:
            break
        frei -= h
        genommen += 1
    for i, zeilen in enumerate(bloecke[len(bloecke) - genommen:]):
        neuester = i == genommen - 1
        farbe = HELL if neuester else ALT
        d.rectangle([RAND, y + 20, RAND + PUNKT_QUADRAT,
                     y + 20 + PUNKT_QUADRAT],
                    fill=AKZENT if neuester else design_tokens.NEUTRAL[4])
        for z in zeilen:
            d.text((RAND + PUNKT_EINZUG, y), z, font=f_punkt, fill=farbe)
            y += PUNKT_ZEILE
        y += PUNKT_LUECKE

    if karte and karte_an:
        _karte_zeichnen(d, karte)
    return bild


# ----------------------------------------------------------- ffmpeg

def _lauf(kmd: list[str]) -> None:
    p = subprocess.run(kmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode:
        raise RuntimeError(f"ffmpeg fehlgeschlagen ({p.returncode}): "
                           f"{(p.stderr or '').strip()[-800:]}")


def audio_schneiden(quelle: Path, start: float, dauer: float,
                    ziel: Path, bett: Path | None) -> None:
    """Story-Ausschnitt aus der Tages-Tonspur, mit sanften Fades an den
    Schnittkanten; das Musikbett des Hauptvideos laeuft leise darunter,
    falls vorhanden (Fehler dort -> Short ohne Bett)."""
    sprache = (f"afade=t=in:st=0:d={FADE},"
               f"afade=t=out:st={max(0.0, dauer - FADE):.3f}:d={FADE}")
    kmd = [FFMPEG, "-y", "-loglevel", "error",
           "-ss", f"{start:.3f}", "-t", f"{dauer:.3f}", "-i", str(quelle)]
    if bett is not None:
        kmd += ["-stream_loop", "-1", "-i", str(bett), "-filter_complex",
                f"[0:a]{sprache}[sp];"
                f"[1:a]volume={BETT_DB}dB,"
                f"afade=t=out:st={max(0.0, dauer - 2.0):.3f}:d=2.0[bt];"
                f"[sp][bt]amix=inputs=2:duration=first:normalize=0[mix]",
                "-map", "[mix]"]
    else:
        kmd += ["-af", sprache]
    kmd += ["-t", f"{dauer:.3f}", "-c:a", "aac", "-b:a", "160k", str(ziel)]
    _lauf(kmd)


def video_bauen(frames: list[tuple[Path, float]], audio: Path, dauer: float,
                ziel: Path, arbeit: Path) -> None:
    """Standbild-Folge + Tonspur zum fertigen 1080x1920-MP4."""
    liste = arbeit / f"{ziel.stem}.ffconcat"
    zeilen = ["ffconcat version 1.0"]
    for pfad, fd in frames:
        zeilen.append(f"file '{pfad.name}'")
        zeilen.append(f"duration {max(0.05, fd):.3f}")
    zeilen.append(f"file '{frames[-1][0].name}'")   # concat-Konvention
    liste.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    _lauf([FFMPEG, "-y", "-loglevel", "error",
           "-f", "concat", "-safe", "0", "-i", str(liste),
           "-i", str(audio),
           "-map", "0:v", "-map", "1:a",
           "-vf", "fps=30,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-c:a", "copy", "-movflags", "+faststart",
           "-t", f"{dauer:.3f}", str(ziel)])


# ----------------------------------------------------------- Marker

def marker_laden(pfad: Path) -> list[dict]:
    try:
        d = json.loads(pfad.read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def marker_schreiben(pfad: Path, eintraege: list[dict]) -> None:
    pfad.write_text(json.dumps(eintraege, indent=2, ensure_ascii=False),
                    encoding="utf-8")


# ----------------------------------------------------------- Hauptablauf

def short_rendern(story: Story, kap: dict, datum: str, arbeit: Path,
                  start_schnitt: float, dauer: float,
                  bett: Path | None, motiv: Path | None = None) -> Path:
    """Rendert ein Short (Audio-Ausschnitt + Standbild-Folge) und gibt den
    MP4-Pfad zurueck."""
    hintergrund = hintergrund_bauen(motiv) if motiv is not None else None
    if motiv is None:
        print("  kein Kapitel-Motiv - Farbtheme")
    elif hintergrund is not None:
        print(f"  Motiv: {motiv.name}")
    kicker = story.bloecke[0].text.split(":")[0] if story.bloecke else ""
    titel = str(kap.get("titel") or story.bloecke[0].text.capitalize())
    stichworte = [str(s.get("text") or "") for s in kap.get("stichworte") or []
                  if isinstance(s, dict) and s.get("text")]
    anker = [str(s.get("anker") or "") for s in kap.get("stichworte") or []
             if isinstance(s, dict) and s.get("text")]
    zeiten: list[float | None] = []
    fehlend = 0
    for a in anker:
        t = vr._anker_zeit(a, story.worte) if a else None
        if t is None:
            fehlend += 1
            zeiten.append(None)
        else:
            zeiten.append(t - start_schnitt)
    if fehlend:
        print(f"  {fehlend} von {len(anker)} Ankern nicht gefunden - "
              f"Stichworte erscheinen mit dem Vorgaenger")
    karte = kap.get("karte") if isinstance(kap.get("karte"), dict) else None
    karte_zeit: float | None = None
    if karte:
        t = vr._anker_zeit(str(karte.get("anker") or ""), story.worte)
        karte_zeit = (t - start_schnitt) if t is not None else dauer * 0.6

    folge = einblendungen(zeiten, karte_zeit, dauer)
    frames: list[tuple[Path, float]] = []
    for i, e in enumerate(folge):
        bild = frame_bauen(kicker, titel, stichworte, e.stichworte,
                           karte, e.karte, datum, hintergrund)
        pfad = arbeit / f"short_{story.nr:02d}_f{i:02d}.png"
        bild.save(pfad, "PNG")
        naechste = folge[i + 1].zeit if i + 1 < len(folge) else dauer
        frames.append((pfad, naechste - e.zeit))

    audio = arbeit / f"short_{story.nr:02d}.m4a"
    audio_schneiden(vr.VIDEO_DIR / datum / "audio_en.mp3", start_schnitt,
                    dauer, audio, bett)
    ziel = arbeit / f"short_{story.nr:02d}.mp4"
    video_bauen(frames, audio, dauer, ziel, arbeit)
    return ziel


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sprache", choices=sorted(vr.SPRACHEN), default="en")
    ap.add_argument("--trockenlauf", action="store_true",
                    help="rendern ohne Upload und ohne Marker")
    ap.add_argument("--nur", type=int, default=None, metavar="STORY_INDEX",
                    help="nur die Story mit diesem Abschnittsindex")
    ap.add_argument("--datum", default=None,
                    help="Berichtstag (default: heute)")
    ap.add_argument("--status", choices=["public", "unlisted"],
                    default="public",
                    help="Sichtbarkeit nach dem Upload (Test: unlisted)")
    args = ap.parse_args()
    cfg = vr.SPRACHEN[args.sprache]
    datum = args.datum or date.today().isoformat()
    tag_dir = vr.EXTRAKTE / datum
    arbeit = vr.VIDEO_DIR / datum
    bericht = tag_dir / cfg["bericht"]
    audio = arbeit / f"audio{cfg['suffix']}.mp3"

    if not bericht.exists() or not audio.exists():
        print(f"keine Tages-Assets fuer {datum} "
              f"(bericht: {bericht.exists()}, audio: {audio.exists()}) - "
              f"keine Shorts")
        return
    markdown = bericht.read_text(encoding="utf-8")
    d = vr.drehbuch_bauen(tag_dir, markdown, args.sprache, datum)
    if not d.fdaten:
        print("keine folien.json - keine Story-Titel, keine Shorts")
        return

    worte, quelle = worte_laden(arbeit, cfg["suffix"])
    if not worte:
        print("weder Ton-Cache noch SRT vorhanden - keine Shorts")
        return
    aehnlich = text_aehnlichkeit(worte, d.bloecke_ton)
    print(f"Wortstrom aus {quelle}: {len(worte)} Woerter, "
          f"Text-Aehnlichkeit {aehnlich:.3f}")
    if aehnlich < AEHNLICHKEIT_MIN:
        print(f"Tonspur passt nicht zum aktuellen Bericht "
              f"(<{AEHNLICHKEIT_MIN}) - keine Shorts, um nicht an falschen "
              f"Grenzen zu schneiden")
        return

    stories = stories_finden(d.bloecke_ton, worte)
    print(f"{len(stories)} Storys in der Tonspur lokalisiert")
    motive = story_motive(datum, d.bloecke_ton, d.abschnitte)

    marker_pfad = tag_dir / f"shorts{cfg['suffix']}.json"
    eintraege = marker_laden(marker_pfad)
    fertig = {e.get("story_index") for e in eintraege}
    bett = vr.BETT if vr.BETT.exists() else None
    if bett is None:
        print("kein Musikbett gefunden - Shorts ohne Bett")

    for story in stories:
        if args.nur is not None and story.nr != args.nur:
            continue
        if story.nr in fertig and not args.trockenlauf:
            print(f"Story {story.nr} schon hochgeladen - uebersprungen")
            continue
        try:
            start_schnitt = max(0.0, story.start - VORLAUF)
            dauer = story.ende + NACHLAUF - start_schnitt
            kap = d.zuordnung.get(story.nr) or {}
            kap_titel = str(kap.get("titel")
                            or story.bloecke[0].text.capitalize())
            if not MIN_DAUER <= dauer <= MAX_DAUER:
                print(f"Story {story.nr} ({kap_titel}): {dauer:.1f}s - "
                      f"ausserhalb {MIN_DAUER:.0f}-{MAX_DAUER:.0f}s, "
                      f"uebersprungen")
                continue
            print(f"Story {story.nr}: {kap_titel} "
                  f"({story.start:.1f}-{story.ende:.1f}s, {dauer:.1f}s)")
            mp4 = short_rendern(story, kap, datum, arbeit, start_schnitt,
                                dauer, bett, motive.get(story.nr))
            if args.trockenlauf:
                print(f"  gerendert (kein Upload): {mp4}")
                continue

            story_text = " ".join(b.text for b in story.bloecke)
            ticker = ticker_finden(story_text)
            titel = short_titel(kap_titel, ticker, datum)
            beschreibung = short_beschreibung(
                story, kap_titel, ticker, datum, tag_dir, cfg["marker"],
                d.abschnitte)
            tags = short_tags(kap_titel, story.bloecke[0].text, story_text)
            print(f"  lade hoch: {titel}")
            video_id, url = youtube_auth.hochladen(
                mp4, titel, beschreibung, privacy_status="private",
                tags=tags, sprache=args.sprache)
            # Marker sofort persistieren: ein Abbruch danach darf beim
            # Wiederanlauf kein Duplikat hochladen.
            eintraege.append({"story_index": story.nr, "titel": titel,
                              "video_id": video_id, "url": url})
            marker_schreiben(marker_pfad, eintraege)
            fertig.add(story.nr)
            youtube_auth.status_setzen(video_id, args.status)
            print(f"  hochgeladen ({args.status}): {url}")
        except Exception as e:  # noqa: BLE001 - eine Story darf die anderen nie kippen
            print(f"Story {story.nr} fehlgeschlagen: {e}")


if __name__ == "__main__":
    main()
