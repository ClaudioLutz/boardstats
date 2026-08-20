#!/usr/bin/env python3
"""Laufzeitzustand aus dem Haupt-Checkout in einen Worktree kopieren.

Testlaeufe am Report gehoeren laut CLAUDE.md in einen eigenen Worktree. Der
startet aber leer: cache/, arbeit/, berichte/ und raw/ stehen alle in
.gitignore. Ohne sie liest ein Testlauf jeden Thread voll (15 Sonnet-Aufrufe
statt einer Handvoll Deltas) und bezahlt die Sichtpruefung fuer Bilder und
Clips noch einmal, weil die Freigaben fehlen.

Dieses Skript holt den Ausgangsstand einmalig herueber. Es kopiert nur in
diese Richtung - zurueck fliesst nie etwas, sonst waere der Worktree kein
Schutz mehr, sondern nur ein Umweg zum produktiven Zustand.

    python3 testumgebung.py                 # zeigt, was kopiert wuerde
    python3 testumgebung.py --kopieren      # kopiert
    python3 testumgebung.py --kopieren --quelle /pfad/zum/checkout
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ZIEL = Path(__file__).resolve().parent

# Was ein Testlauf braucht, um sich wie ein produktiver zu verhalten.
# raw/ bleibt draussen: die Snapshots holt bundle_biz.py selbst, und sie sind
# das mit Abstand groesste Verzeichnis.
TEILE = (
    ("cache", "Delta-Gedaechtnis: status.json und die Extrakte je Thread"),
    ("arbeit/motive/verwendet.json", "Bildsperren der letzten Tage"),
    ("arbeit/clips/katalog.json", "Clip-Freigaben (Sichtpruefung schon bezahlt)"),
    ("berichte", "Vorberichte fuer den Themenverlauf der Synthese"),
)


def haupt_checkout() -> Path | None:
    """Den Haupt-Checkout finden, aus dem dieser Worktree stammt."""
    try:
        aus = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=ZIEL, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    # Der erste Eintrag ist immer der Haupt-Checkout.
    for zeile in aus.splitlines():
        if zeile.startswith("worktree "):
            return Path(zeile.split(" ", 1)[1])
    return None


def kopieren(quelle: Path, schreiben: bool) -> int:
    if quelle.resolve() == ZIEL.resolve():
        print(f"Quelle und Ziel sind derselbe Ordner ({ZIEL}) - "
              f"das Skript gehoert in einen Worktree, nicht in den "
              f"Haupt-Checkout.")
        return 1

    gefunden = 0
    for teil, zweck in TEILE:
        von, nach = quelle / teil, ZIEL / teil
        if not von.exists():
            print(f"  fehlt in der Quelle, uebersprungen: {teil}")
            continue
        gefunden += 1
        groesse = (sum(p.stat().st_size for p in von.rglob("*") if p.is_file())
                   if von.is_dir() else von.stat().st_size)
        print(f"  {teil}  ({groesse / 1024:.0f} KB) - {zweck}")
        if not schreiben:
            continue
        nach.parent.mkdir(parents=True, exist_ok=True)
        if von.is_dir():
            shutil.copytree(von, nach, dirs_exist_ok=True)
        else:
            shutil.copy2(von, nach)

    if not gefunden:
        print("nichts gefunden - stimmt --quelle?")
        return 1
    if schreiben:
        print(f"\nkopiert nach {ZIEL}")
        print("Testlaeufe hier veraendern den produktiven Zustand nicht mehr; "
              "zurueck kopiert wird bewusst nichts.")
    else:
        print("\nTrockenlauf - mit --kopieren wirklich kopieren.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Laufzeitzustand in diesen Worktree kopieren")
    ap.add_argument("--quelle", type=Path, default=None,
                    help="Haupt-Checkout (Standard: aus git worktree list)")
    ap.add_argument("--kopieren", action="store_true",
                    help="wirklich kopieren statt nur anzeigen")
    args = ap.parse_args()

    quelle = args.quelle or haupt_checkout()
    if quelle is None:
        print("Haupt-Checkout nicht gefunden - bitte --quelle angeben.")
        return 1
    if not quelle.is_dir():
        print(f"Quelle gibt es nicht: {quelle}")
        return 1

    print(f"Quelle: {quelle}\nZiel:   {ZIEL}\n")
    return kopieren(quelle, args.kopieren)


if __name__ == "__main__":
    sys.exit(main())
