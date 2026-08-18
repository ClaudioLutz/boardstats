#!/usr/bin/env python3
"""Vorgerenderte Icons fuer die Video-Overlays (18.08.2026).

Quelle: Tabler Icons (github.com/tabler/tabler-icons, MIT, siehe
assets/icons/LICENSE.md), als 240x240-PNG mit Alphakanal unter
assets/icons/ abgelegt - keine Laufzeitabhaengigkeit zu SVG/cairosvg,
nur ein einmaliger Download. Zur Laufzeit wird jedes Icon farbig
eingefaerbt (die PNGs selbst sind schwarz auf transparent) und auf
Zielgroesse herunterskaliert.

Nur Icons mit echter Verwendung sind hier hinterlegt: eine Uhr (Datum im
Ecken-Bug), ein Lesezeichen (Kapitelmarker am Themen-Titel) und ein
Auf-/Ab-Trend-Pfeil (Zahlen-Tafel, nur wenn der Zahlenwert selbst ein
explizites Vorzeichen traegt - kein erfundenes Trendurteil ueber
unbelegte Board-Behauptungen)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image

ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"


@lru_cache(maxsize=32)
def _roh(name: str) -> Image.Image:
    return Image.open(ICON_DIR / f"{name}.png").convert("RGBA")


@lru_cache(maxsize=128)
def icon(name: str, groesse: int, farbe: tuple[int, int, int]) -> Image.Image:
    """Icon `name` auf `groesse`x`groesse` skaliert, in `farbe` eingefaerbt.

    Die Quell-PNGs sind schwarz auf transparent; ihr Alphakanal dient als
    Maske fuer eine einfarbige Flaeche - dasselbe Muster wie ein Icon-Font,
    nur ohne Font-Rendering."""
    roh = _roh(name).resize((groesse, groesse), Image.Resampling.LANCZOS)
    flaeche = Image.new("RGBA", roh.size, (*farbe, 255))
    flaeche.putalpha(roh.getchannel("A"))
    return flaeche
