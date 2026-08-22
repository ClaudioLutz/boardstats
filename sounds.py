#!/usr/bin/env python3
"""Sound-Design fuer das Szenen-Video (Intent B5, 22.08.2026).

Vier Geraeusche, synthetisch und deterministisch erzeugt (kein Sample-Pack,
kein Rechteinhaber, kein Content-ID-Risiko - dieselbe Begruendung wie beim
synthetischen Musikbett in video_report.bett_bauen):

- **whoosh**  fuer die Bewegung (Fokus-Punkt fliegt in die Randspalte)
- **klick**   fuers Parken (der Punkt rastet in der Liste ein)
- **impact**  fuer die Zahl (der Count-up erreicht seinen Endwert)
- **kapitel** fuer den Kapitelwechsel (der Knall auf der Schwarzblende -
  ohne ihn liest sich das kurze Schwarzbild als Fehler, nicht als Absicht;
  siehe Intent A#80/69: die beiden werden zusammen gebaut oder gar nicht)

Voraussetzung laut Intent ist, dass die Geraeusche EXAKT auf der Bewegung
liegen - deshalb entstehen die Zeitpunkte in video_report.szenen_bauen aus
denselben Planwerten wie die Bewegungen selbst (flug_ab, Count-up-Ende,
kopf_start) und werden hier nur noch abgemischt.

Die Effektspur wird als eigene WAV gebaut (48 kHz mono, wie die Sprache)
und in video_report._ton_kette als dritter Eingang gemischt - bewusst NICHT
durch das Sidechain-Ducking: die Effekte sollen auf der Sprache liegen
duerfen, sie dauern nur Zehntel. Zurueckhaltung ist das Qualitaetsmerkmal
(Leitplanke 5): die Pegel unten sind leise gewaehlt, der Endmix laeuft
ohnehin durch die zweipassige loudnorm.
"""
from __future__ import annotations

import math
import random
import wave
from collections.abc import Callable
from pathlib import Path

SR = 48000

# Mischpegel je Geraeusch (linear, auf int16-Vollausschlag bezogen).
# Leise als Starthypothese - ob sie tragen, entscheidet das Ohr am
# fertigen Video, wie bei BETT_INTRO_ANHEBUNG.
PEGEL = {
    "whoosh": 0.16,
    "klick": 0.20,
    "zahl": 0.34,
    "kapitel": 0.42,
}


def _envelope(n: int, attack: float, release: float) -> list[float]:
    """Huellkurve: linearer Attack, exponentieller Release."""
    a = max(1, int(attack * SR))
    aus = []
    for i in range(n):
        e = min(1.0, i / a)
        e *= math.exp(-release * max(0, i - a) / SR)
        aus.append(e)
    return aus


def whoosh(dauer: float = 0.32) -> list[float]:
    """Gefiltertes Rauschen mit ansteigender Helligkeit: ein Ein-Pol-
    Tiefpass, dessen Koeffizient ueber die Dauer oeffnet - das klassische
    Anfahr-Geraeusch, ohne DSP-Bibliothek."""
    rnd = random.Random(4711)   # deterministisch: jeder Tag klingt gleich
    n = int(dauer * SR)
    huelle = _envelope(n, dauer * 0.55, 14.0)
    aus: list[float] = []
    tief = 0.0
    for i in range(n):
        alpha = 0.04 + 0.42 * (i / n) ** 2   # zu, dann hell oeffnend
        tief += alpha * (rnd.uniform(-1, 1) - tief)
        aus.append(tief * huelle[i] * 3.0)
    return aus


def klick(dauer: float = 0.06) -> list[float]:
    """Kurzer Rast-Klick: hoher Sinus mit sehr schnellem Abfall."""
    n = int(dauer * SR)
    return [math.sin(2 * math.pi * 1860 * i / SR)
            * math.exp(-90 * i / SR) for i in range(n)]


def _impact(dauer: float, f0: float, f1: float, abfall: float,
            transient: float) -> list[float]:
    """Tiefer Schlag: Sinus mit fallender Tonhoehe, exponentieller Abfall,
    kurzer Rausch-Transient am Anschlag."""
    rnd = random.Random(1337)
    n = int(dauer * SR)
    aus = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = f1 + (f0 - f1) * math.exp(-9.0 * t)
        phase += 2 * math.pi * f / SR
        s = math.sin(phase) * math.exp(-abfall * t)
        if t < 0.02:
            s += rnd.uniform(-1, 1) * transient * (1 - t / 0.02)
        aus.append(s)
    return aus


def impact_zahl() -> list[float]:
    return _impact(0.5, 105.0, 52.0, 6.5, 0.35)


def impact_kapitel() -> list[float]:
    return _impact(0.65, 82.0, 38.0, 4.5, 0.5)


_BAUER: dict[str, "Callable[[], list[float]]"] = {
    "whoosh": whoosh,
    "klick": klick,
    "zahl": impact_zahl,
    "kapitel": impact_kapitel,
}


def effekt_spur(ereignisse: list[tuple[float, str]], ende: float,
                ziel: Path) -> Path | None:
    """Alle Klang-Ereignisse in eine WAV-Spur mischen.

    ereignisse: (Zeit in Sekunden, Art aus PEGEL). Ereignisse ausserhalb
    von [0, ende) fallen still weg (Vorschau-Laeufe kuerzen das Video).
    None, wenn nichts zu mischen ist - der Ton laeuft dann wie bisher."""
    im_fenster = [(t, art) for t, art in ereignisse
                  if 0.0 <= t < ende and art in _BAUER]
    if not im_fenster:
        return None
    # int16-Array statt Float-Liste: bei einem 10-Minuten-Video sind das
    # rund 30 Mio. Samples - die Spur ist fast ueberall still, gemischt
    # wird nur an den Ereignisstellen.
    import array
    n = int(ende * SR) + SR
    puffer = array.array("h", bytes(2 * n))
    klaenge = {art: _BAUER[art]() for art in {a for _, a in im_fenster}}
    for t, art in im_fenster:
        start = int(t * SR)
        pegel = PEGEL[art]
        for i, s in enumerate(klaenge[art]):
            j = start + i
            if j >= n:
                break
            wert = puffer[j] + int(s * pegel * 32767)
            puffer[j] = max(-32768, min(32767, wert))
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ziel), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(puffer.tobytes())
    return ziel
