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
"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import ImageFont

import youtube_auth

BASE = Path(__file__).parent
EXTRAKTE = BASE / "extrakte"
VIDEO_DIR = BASE / "video"
STIMME = "de-DE-KatjaNeural"
FONT_NORMAL_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
FONT_FETT_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

CANVAS_W = 1280
CANVAS_H = 720
FONTSIZE = 34
UEBERSCHRIFT_FONTSIZE = 44
ZEILENHOEHE = 44
ABSATZ_ABSTAND = 20        # zusaetzlicher Abstand vor einem neuen Absatz
UEBERSCHRIFT_ABSTAND = 36  # zusaetzlicher Abstand vor einer Ueberschrift
PUNKT_ABSTAND = 12         # zusaetzlicher Abstand vor einem Aufzaehlungspunkt
MARGIN_LINKS = 80          # fester linker Textrand (linksbuendig wie der Bericht)
PUNKT_EINZUG = 40          # haengender Einzug fuer Aufzaehlungstext hinter dem «•»
ZEILENBREITE_MAX = CANVAS_W - 2 * MARGIN_LINKS
LESEPOSITION_Y = int(CANVAS_H * 0.45)  # hier steht die gerade gesprochene Zeile
V_MAX = 60.0      # px/s, Tempo-Deckel gegen Spruenge bei sehr dichten Ankern
ANKER_SCHRITT = 8  # alle N Zeilen ein Scroll-Anker (Tempo-Anpassung ans Sprechen)
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
    fliesstext = ImageFont.truetype(font_pfad(FONT_NORMAL_KANDIDATEN), FONTSIZE)
    return {
        "absatz": fliesstext,
        "punkt": fliesstext,
        "ueberschrift": ImageFont.truetype(font_pfad(FONT_FETT_KANDIDATEN),
                                           UEBERSCHRIFT_FONTSIZE),
    }


# ----------------------------------------------------------- Text-Bereinigung

_URL_ZEILE = re.compile(r"^(?:https?://\S+(?:\s+und\s+)?)+$")
_QUELLEN_ZEILE = re.compile(r"^(Quelle|Quellen|Belege):", re.IGNORECASE)


@dataclass
class Block:
    art: str  # "absatz", "ueberschrift" oder "punkt" (Aufzaehlung)
    text: str


def bloecke_erzeugen(markdown: str) -> list[Block]:
    """Reduziert den veroeffentlichten bericht.md-Text auf das Vorlesbare.

    Markdown-Syntax (Titel, Archiv-Link, Trennlinie) kann man nicht hoeren;
    Quell-/Beleg-Zeilen und nackte Thread-URLs sind fuer einen Leser gedacht,
    der klicken kann, nicht fuer einen Zuhoerer. Das GLOSSAR ist zum
    Nachschlagen gedacht, nicht zum Anhoeren, und entfaellt komplett - es
    bleibt oeffentlich im bericht.md sichtbar. Die Blockstruktur (Absatz vs.
    ##-Ueberschrift) bleibt erhalten, damit das Video sie darstellen kann."""
    zeilen = markdown.splitlines()
    ergebnis: list[Block] = []
    for i, zeile in enumerate(zeilen):
        z = zeile.strip()
        if i == 0 and z.startswith("# "):
            continue
        if z.startswith("## GLOSSAR"):
            break
        if not z or z == "---":
            continue
        if z.startswith("[") and "](README.md)" in z:
            continue
        if z.startswith("*Datenstand:") and z.endswith("*"):
            continue
        if _URL_ZEILE.match(z):
            continue
        if _QUELLEN_ZEILE.match(z):
            continue
        if z.startswith("## "):
            ergebnis.append(Block("ueberschrift", z[3:]))
        elif z.startswith("- "):
            ergebnis.append(Block("punkt", z[2:]))
        else:
            ergebnis.append(Block("absatz", z))
    return ergebnis


def text_fuer_tts(markdown: str) -> str:
    return "\n\n".join(b.text for b in bloecke_erzeugen(markdown))


# ----------------------------------------------------------- TTS mit Wort-Zeitstempeln

@dataclass
class Wort:
    text: str
    start: float
    end: float


def tts_mit_worten(text: str, ziel_mp3: Path) -> list[Wort]:
    """Vertont text und liefert dabei pro gesprochenem Wort Start/Ende (Sekunden).

    Nutzt die edge-tts-Bibliothek direkt (nicht die CLI), weil nur der
    Python-API-Stream WordBoundary-Ereignisse mit Zeitstempeln liefert."""
    import edge_tts

    async def _lauf() -> list[Wort]:
        communicate = edge_tts.Communicate(text, STIMME, boundary="WordBoundary")
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
    y_master: float = 0.0

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


def _anker_berechnen(zeilen: list[Zeile]) -> list[tuple[float, float]]:
    """Stuetzpunkte (zeit, master_y) der globalen Scroll-Funktion P(t).

    Alle ANKER_SCHRITT Zeilen ein Anker an der Sprechzeit-Mitte der Zeile -
    dazwischen laeuft der gesamte Text mit konstanter Geschwindigkeit als
    starrer Block. Zeiten werden streng monoton gehalten und das Tempo pro
    Segment auf V_MAX gedeckelt."""
    anker: list[tuple[float, float]] = []
    indizes = list(range(0, len(zeilen), ANKER_SCHRITT))
    if indizes[-1] != len(zeilen) - 1:
        indizes.append(len(zeilen) - 1)
    for i in indizes:
        z = zeilen[i]
        t = (z.start + z.end) / 2
        if anker:
            dy = z.y_master - anker[-1][1]
            if dy <= 0:
                continue
            t = max(t, anker[-1][0] + dy / V_MAX)
        anker.append((t, z.y_master))
    return anker


def _p_wert(anker: list[tuple[float, float]], t: float) -> float:
    """P(t): Master-Y, das zur Zeit t an der Leseposition steht.

    Vor dem ersten bzw. nach dem letzten Anker wird die Steigung des
    Randsegments fortgesetzt."""
    if len(anker) == 1:
        return anker[0][1] + (t - anker[0][0]) * 20.0
    if t <= anker[0][0]:
        (t1, y1), (t2, y2) = anker[0], anker[1]
    elif t >= anker[-1][0]:
        (t1, y1), (t2, y2) = anker[-2], anker[-1]
    else:
        for k in range(len(anker) - 1):
            if anker[k][0] <= t <= anker[k + 1][0]:
                (t1, y1), (t2, y2) = anker[k], anker[k + 1]
                break
    return y1 + (y2 - y1) * (t - t1) / (t2 - t1)


def _p_invers(anker: list[tuple[float, float]], y: float) -> float:
    """Umkehrung von P: Zeit, zu der Master-Y y die Leseposition passiert."""
    if len(anker) == 1:
        return anker[0][0] + (y - anker[0][1]) / 20.0
    if y <= anker[0][1]:
        (t1, y1), (t2, y2) = anker[0], anker[1]
    elif y >= anker[-1][1]:
        (t1, y1), (t2, y2) = anker[-2], anker[-1]
    else:
        for k in range(len(anker) - 1):
            if anker[k][1] <= y <= anker[k + 1][1]:
                (t1, y1), (t2, y2) = anker[k], anker[k + 1]
                break
    return t1 + (t2 - t1) * (y - y1) / (y2 - y1)


def _segmente(anker: list[tuple[float, float]], von: float, bis: float) -> list[tuple[float, float]]:
    """Zerlegt [von, bis] an den Ankerzeiten - innerhalb jedes Teilstuecks
    ist P(t) linear und laesst sich exakt als ein \\move ausdruecken."""
    punkte = [von] + [t for t, _ in anker if von < t < bis] + [bis]
    return [(punkte[k], punkte[k + 1]) for k in range(len(punkte) - 1)
            if punkte[k + 1] - punkte[k] > 1e-4]


def ass_erzeugen(zeilen: list[Zeile], ziel_ass: Path) -> None:
    """Baut das Untertitel-Skript: dichtes Fliesstext-Layout, das nach oben scrollt.

    Der gesamte Text scrollt als starrer Block entlang der globalen
    Scroll-Funktion P(t) - die Abstaende auf dem Bildschirm entsprechen
    dadurch immer exakt dem Master-Layout (keine Kollisionen, keine
    schwankenden Zeilenabstaende), waehrend das Tempo sich an den Ankern
    dem Sprechtempo anpasst. Jede Zeile wird als EIN zusammenhaengender
    String gerendert (libass setzt die Wortabstaende selbst, natuerlicher
    Textsatz); die Wort-Hervorhebung ist derselbe Zeilenstring noch einmal,
    bei dem alle Woerter ausser dem gerade gesprochenen per \\alpha
    unsichtbar sind - identischer Glyphenlauf, also pixelgenau
    deckungsgleich. Woerter einzeln per PIL-Metriken zu positionieren
    funktioniert dagegen nicht zuverlaessig: PIL und libass/HarfBuzz messen
    pro Wort um +-2 Prozent unterschiedlich (Kerning/Shaping/Fontskalierung),
    was je nach Wort klebende oder klaffende Luecken erzeugt."""
    # Master-Layout: feste vertikale Position jeder Zeile im Gesamttext
    y = 0.0
    for i, zeile in enumerate(zeilen):
        if i > 0 and zeile.blockanfang:
            y += {"ueberschrift": UEBERSCHRIFT_ABSTAND,
                  "punkt": PUNKT_ABSTAND}.get(zeile.art, ABSATZ_ABSTAND)
        zeile.y_master = y
        y += ZEILENHOEHE

    anker = _anker_berechnen(zeilen)
    y_enter = CANVAS_H + ZEILENHOEHE
    y_exit = -(ZEILENHOEHE + UEBERSCHRIFT_FONTSIZE)
    events: list[str] = []

    for zeile in zeilen:
        # Bildschirm-Y der Zeile: versatz - P(t)
        versatz = LESEPOSITION_Y + zeile.y_master
        fenster_start = max(0.0, _p_invers(anker, versatz - y_enter))
        fenster_end = _p_invers(anker, versatz - y_exit)
        if fenster_end <= fenster_start:
            continue

        if zeile.art == "ueberschrift":
            # fett + groesser, wie eine ##-Ueberschrift im Markdown-Bericht
            stil = f"\\fs{UEBERSCHRIFT_FONTSIZE}\\b1"
        else:
            stil = ""

        links_x = MARGIN_LINKS + (PUNKT_EINZUG if zeile.art == "punkt" else 0)
        zeilen_segmente = _segmente(anker, fenster_start, fenster_end)

        if zeile.art == "punkt" and zeile.blockanfang:
            # haengendes Aufzaehlungszeichen am linken Rand, Text eingezogen
            punkt_x = MARGIN_LINKS
            for t_a, t_b in zeilen_segmente:
                y1 = versatz - _p_wert(anker, t_a)
                y2 = versatz - _p_wert(anker, t_b)
                events.append(
                    f"Dialogue: 0,{_ass_zeit(t_a)},{_ass_zeit(t_b)},Report,,0,0,0,,"
                    f"{{\\move({punkt_x:.0f},{y1:.0f},{punkt_x:.0f},{y2:.0f})}}•"
                )

        texte = [_ass_escape(w.text) for w in zeile.worte]
        for t_a, t_b in zeilen_segmente:
            y1 = versatz - _p_wert(anker, t_a)
            y2 = versatz - _p_wert(anker, t_b)
            events.append(
                f"Dialogue: 0,{_ass_zeit(t_a)},{_ass_zeit(t_b)},Report,,0,0,0,,"
                f"{{\\move({links_x},{y1:.0f},{links_x},{y2:.0f}){stil}}}"
                + " ".join(texte)
            )

        for i, wort in enumerate(zeile.worte):
            # ganze Zeile noch einmal, nur das aktive Wort sichtbar (Akzent)
            teile = []
            if i > 0:
                teile.append("{\\alpha&HFF&}" + " ".join(texte[:i]) + " ")
            teile.append(f"{{\\alpha&H00&\\c{FARBE_AKZENT}}}{texte[i]}")
            if i < len(texte) - 1:
                teile.append("{\\alpha&HFF&} " + " ".join(texte[i + 1:]))
            hervorhebung = "".join(teile)

            w_start = max(fenster_start, wort.start)
            w_end = max(w_start + 0.01, min(fenster_end, wort.end))
            for t_a, t_b in _segmente(anker, w_start, w_end):
                y1 = versatz - _p_wert(anker, t_a)
                y2 = versatz - _p_wert(anker, t_b)
                events.append(
                    f"Dialogue: 1,{_ass_zeit(t_a)},{_ass_zeit(t_b)},Report,,0,0,0,,"
                    f"{{\\move({links_x},{y1:.0f},{links_x},{y2:.0f}){stil}}}"
                    f"{hervorhebung}"
                )

    ziel_ass.write_text(ASS_HEADER + "\n".join(events) + "\n", encoding="utf-8")


# ----------------------------------------------------------- Video-Zusammenbau

def video_erzeugen(audio_mp3: Path, ass_datei: Path, ziel_mp4: Path) -> None:
    ass_arg = str(ass_datei).replace("\\", "/").replace(":", r"\:")
    subprocess.run(
        ["ffmpeg", "-y",
         "-f", "lavfi", "-i", f"color=c={HINTERGRUND}:s={CANVAS_W}x{CANVAS_H}",
         "-i", str(audio_mp3),
         "-vf", f"ass={ass_arg}",
         "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
         "-shortest", str(ziel_mp4)],
        check=True, timeout=1200)


# ----------------------------------------------------------- Orchestrierung

def main() -> None:
    datum = date.today().isoformat()
    tag_dir = EXTRAKTE / datum
    bericht_pfad = tag_dir / "bericht.md"
    marker_pfad = tag_dir / "video.json"

    if not bericht_pfad.exists():
        print(f"kein Bericht fuer {datum} unter {bericht_pfad} - nichts zu tun")
        return
    if marker_pfad.exists():
        print(f"Video fuer {datum} schon hochgeladen: {marker_pfad}")
        return

    markdown = bericht_pfad.read_text(encoding="utf-8")
    bloecke = bloecke_erzeugen(markdown)
    text = "\n\n".join(b.text for b in bloecke)

    arbeit = VIDEO_DIR / datum
    arbeit.mkdir(parents=True, exist_ok=True)
    audio_mp3 = arbeit / "audio.mp3"
    ass_datei = arbeit / "untertitel.ass"
    video_mp4 = arbeit / "video.mp4"

    titel = f"/biz/-Lagebericht {datum}"
    print("erzeuge Vertonung mit Wort-Zeitstempeln ...")
    worte = tts_mit_worten(text, audio_mp3)
    print(f"{len(worte)} Woerter erkannt")

    fonts = fonts_laden()
    zeilen: list[Zeile] = []
    for block, block_worte in zip(bloecke, worte_zu_bloecken(worte, bloecke)):
        if block_worte:
            zeilen.extend(in_zeilen_umbrechen(block_worte, fonts[block.art], block.art))
    print(f"{len(zeilen)} Zeilen in {len(bloecke)} Bloecken")
    ass_erzeugen(zeilen, ass_datei)

    print("baue Video ...")
    video_erzeugen(audio_mp3, ass_datei, video_mp4)

    beschreibung = (
        f"Automatisierter Lagebericht aus dem 4chan-Board /biz/ (Business & "
        f"Finance) vom {datum}. Diskurs-Dokumentation, keine Anlageberatung.\n\n"
        f"Vollstaendiger Text mit Quellen: "
        f"https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/{datum}/bericht.md"
    )
    print("lade auf YouTube hoch ...")
    video_id, url = youtube_auth.hochladen(video_mp4, titel, beschreibung)
    marker_pfad.write_text(json.dumps({"video_id": video_id, "url": url}, indent=2), encoding="utf-8")
    print(f"hochgeladen: {url}")


if __name__ == "__main__":
    main()
