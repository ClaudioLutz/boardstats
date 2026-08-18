#!/usr/bin/env python3
"""Hintergrund-Sichtpruefung fuer einen Tag nachziehen.

Einmalige Reparatur fuer den 18.08.2026: die Sichtpruefung des Morgenlaufs
war an ihrer eigenen Plausibilitaetspruefung gescheitert (dieselbe
Beschreibung fuer zwei Bilder), es entstand kein motive.json, und das Video
lief mit einem einzigen Bild. Der Lauf hier holt genau diesen Schritt nach -
mit der Stapel-Pruefung aus Commit 016a67d.

Das Manifest des Morgenlaufs existiert nicht mehr (arbeit/ wird aufgeraeumt);
die Thread-Reihenfolge nach Substanzdichte steht aber in der Tagestabelle des
Archivs (extrakte/<datum>/README.md) und wird daraus rekonstruiert.
"""
import logging
import re
import sys

import run_report

# Ohne eigene Konfiguration schluckt Python die info-Zeilen der Sichtpruefung,
# und dann fehlt genau die Liste der abgelehnten Bilder samt Grund.
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s",
                    datefmt="%H:%M:%S")

datum = sys.argv[1]
tabelle = (run_report.EXTRAKTE / datum / "README.md").read_text(encoding="utf-8")
threads = re.findall(r"\]\((\d+)\.md\)", tabelle)
if not threads:
    raise SystemExit(f"keine Threads in der Tagestabelle von {datum}")
print(f"{len(threads)} Threads aus der Tagestabelle: {', '.join(threads[:5])} ...")

manifest = {"buendel": [{"thread": t} for t in threads]}
frei = run_report.hintergruende_waehlen(manifest, datum)
print(f"{frei} Hintergrundbilder freigegeben; Abgelehnte liegen mit Grund im "
      f"Dateinamen unter {run_report.ARBEIT / 'motive' / datum / 'abgelehnt'}")
