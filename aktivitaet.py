#!/usr/bin/env python3
"""Balkengrafik "Board-Aktivitaet" - die erste eigene Datengrafik der
Pipeline (18.08.2026), noch NICHT in video_report.py verdrahtet.

Bisher bestand die einzige "Datengrafik" aus reinem Zahlen-Text
(zahl_tafel/countup_werte) - die am 17.08. bemaengelte Luecke war eine
echte Balken-/Sparkline-Grafik. Kandidat dafuer sind nicht die
"Zahlen des Tages" (poster claims wie "+300%" oder "10x" - heterogene
Einheiten, ein Balkenvergleich zwischen ihnen waere unbelegte
Aequivalenz, keine Datenvisualisierung), sondern eine echte, im Code
selbst anfallende Zeitreihe: Anzahl extrahierter Threads pro Tag
(extrakte/<datum>/<thread_id>.md), gemessen ueber die letzten Tage.

Rendert mit matplotlib (dark_background), Agg-Backend, keine
Systemabhaengigkeit ueber das ohnehin vorhandene Pillow/Python hinaus -
lediglich ein neues venv-Paket (siehe video.sh-Kommentar). Farben und
Schriften kommen aus demselben Token-/Font-System wie der Rest der
Overlays (design_tokens.py, thumbnail.schrift*), damit die Grafik nicht
wie ein Fremdkoerper neben den Pillow-Karten wirkt.

Absichtlich nicht an video_report.py angeschlossen: wo im Storyboard
(Timing/Dauer) diese Karte erscheinen soll, ist eine Produktionsentscheidung,
keine Rendering-Frage - siehe Recherche-Notiz vom 18.08.2026."""
from __future__ import annotations

import io
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from PIL import Image, ImageDraw

import design_tokens
import thumbnail

B = thumbnail.BREITE
H = thumbnail.HOEHE

_DATUM_ORDNER = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_THREAD_DATEI = re.compile(r"^\d+\.md$")

_DISPLAY_TTF = str(thumbnail.FONT_DIR / "SpaceGrotesk-Bold.ttf")
_TEXT_TTF = str(thumbnail.FONT_DIR / "Inter-Regular.ttf")


def taegliche_extrakt_zahlen(extrakte_dir: Path, tage: int = 14
                             ) -> list[tuple[str, int]]:
    """Anzahl extrahierter Thread-Dateien je Tagesordner, die letzten
    `tage` (nach Datum sortierte) Ordner. Zaehlt nur `<thread_id>.md`
    (README.md/bericht*.md/*.json bleiben aussen vor)."""
    ordner = sorted(d for d in extrakte_dir.iterdir()
                    if d.is_dir() and _DATUM_ORDNER.match(d.name))
    aus = []
    for d in ordner[-tage:]:
        n = sum(1 for f in d.iterdir() if _THREAD_DATEI.match(f.name))
        aus.append((d.name, n))
    return aus


def aktivitaets_chart(reihe: list[tuple[str, int]],
                      titel: str = "Board activity, last 14 days") -> Image.Image:
    """Balkengrafik als 1280x720-RGBA-Kartenoverlay - dasselbe Kartenformat
    (KARTE_BG-Flaeche, Akzentbalken, Eckenradius) wie die uebrigen Pillow-
    Karten, damit sie sich nicht wie ein Fremdkoerper einreiht."""
    theme = design_tokens.KARTEN_THEME["dunkel"]
    bg = tuple(c / 255 for c in theme["bg"])
    akzent = tuple(c / 255 for c in theme["wert"])
    text = tuple(c / 255 for c in (255, 255, 255))
    sub = tuple(c / 255 for c in theme["sub"])

    tage = [t[5:] for t, _ in reihe]     # "MM-DD" statt volles Datum
    werte = [n for _, n in reihe]

    fig = plt.figure(figsize=(9.6, 3.4), dpi=100)
    fig.patch.set_alpha(0)
    ax = fig.add_axes((0.06, 0.16, 0.90, 0.68))
    ax.set_facecolor(bg)
    balken = ax.bar(tage, werte, color=akzent, width=0.62)
    ax.set_ylim(0, max(werte) * 1.25 if werte else 1)
    ax.set_title(titel, color=text, fontproperties=FontProperties(fname=_DISPLAY_TTF),
                 fontsize=18, loc="left", pad=14)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0,
                   labelcolor=[c for c in sub], labelsize=11)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FontProperties(fname=_TEXT_TTF))
    ax.yaxis.grid(True, color=sub, alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)
    for rect, wert in zip(balken, werte):
        ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + max(werte) * 0.03,
               str(wert), ha="center", va="bottom", color=text, fontsize=11,
               fontproperties=FontProperties(fname=_TEXT_TTF))

    puffer = io.BytesIO()
    fig.savefig(puffer, format="png", transparent=True)
    plt.close(fig)
    puffer.seek(0)
    chart = Image.open(puffer).convert("RGBA")

    # matplotlib faerbt nur die Achsenflaeche (ax.set_facecolor) ein, nicht
    # die Raender drumherum (Titel/Tick-Labels) - die figure selbst bleibt
    # bewusst transparent, sonst waere sie ein rechteckiger Fremdkoerper mit
    # eigener, nicht abgerundeter Kante. Denselben Kartenhintergrund noch
    # einmal in PIL als abgerundetes Rechteck HINTER den Chart zu legen
    # schliesst genau diese Luecke - ohne ihn stand der Chart komplett
    # freischwebend auf dem rohen Board-Bild (Nutzer-Feedback 18.08.2026:
    # Balken kaum lesbar vor Bildrauschen).
    karte = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    ziel_breite = 1100
    skala = ziel_breite / chart.width
    chart = chart.resize((ziel_breite, int(chart.height * skala)),
                         Image.Resampling.LANCZOS)
    x = (B - chart.width) // 2
    y = (H - chart.height) // 2
    polster = 28
    ImageDraw.Draw(karte).rounded_rectangle(
        [x - polster, y - polster, x + chart.width + polster,
         y + chart.height + polster],
        radius=18, fill=(*theme["bg"], 235), outline=theme["rand"], width=2)
    karte.alpha_composite(chart, (x, y))
    return karte


if __name__ == "__main__":   # Handprobe: aktivitaet.py [extrakte-verzeichnis]
    import sys
    basis = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "extrakte"
    reihe = taegliche_extrakt_zahlen(basis)
    print(reihe)
    bild = aktivitaets_chart(reihe)
    ziel = Path("aktivitaet_probe.png")
    hintergrund = Image.new("RGBA", (B, H), (26, 26, 46, 255))
    hintergrund.alpha_composite(bild)
    hintergrund.convert("RGB").save(ziel)
    print(ziel.resolve())
