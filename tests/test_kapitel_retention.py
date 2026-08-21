#!/usr/bin/env python3
"""Tests fuer die Kapitel-Retention-Messung (Stossrichtung D, 21.08.2026).

Die Abbruchkurve sagt, WANN Zuschauer gehen. Gegen die Kapitelmarken der
Videobeschreibung gelegt sagt sie, WOBEI. Hier ist beides gesichert: das
Zurueckparsen der Marken aus der Beschreibung und die Verlustrechnung je
Kapitel - samt der Eigenschaft, dass alles still zu "" bzw. [] zerfaellt,
wenn eine Messung keine Kapitel kennt (jede Messung vor dem 21.08.2026).

Lauf:  python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analytics_bericht as A  # noqa: E402
import run_report as R  # noqa: E402

BESCHREIBUNG = """Der /biz/-Lagebericht vom 21.08.2026.

00:00 TL;DR
00:48 Silver hits 70
04:00 Gold splits the room
07:07 Still true from yesterday

Quell-Threads:
https://boards.4chan.org/biz/thread/111
"""


class KapitelParsen(unittest.TestCase):
    def test_marken_aus_der_beschreibung(self):
        marken = A.kapitel_aus_beschreibung(BESCHREIBUNG)
        self.assertEqual([m["zeit_s"] for m in marken], [0, 48, 240, 427])
        self.assertEqual(marken[1]["titel"], "Silver hits 70")

    def test_ohne_nullmarke_kein_block(self):
        """Zeitangaben im Fliesstext sind keine Kapitelliste."""
        self.assertEqual(
            A.kapitel_aus_beschreibung("Der Kurs fiel um 12:30 stark ab.\n"), [])

    def test_zu_wenige_marken(self):
        self.assertEqual(
            A.kapitel_aus_beschreibung("00:00 A\n01:00 B\n"), [])

    def test_nicht_aufsteigend(self):
        self.assertEqual(
            A.kapitel_aus_beschreibung("00:00 A\n02:00 B\n01:00 C\n"), [])

    def test_stunden(self):
        marken = A.kapitel_aus_beschreibung(
            "0:00 A\n0:30 B\n1:00:05 C\n")
        self.assertEqual([m["zeit_s"] for m in marken], [0, 30, 3605])


def kennwert(kapitel: list[dict], laufzeit: int = 600,
             f=lambda x: 1 - x) -> dict:
    """Kennwerte-Satz wie _retention_kennwerte ihn liefert."""
    return {"laufzeit_s": laufzeit, "kapitel": kapitel,
            "punkte": [(i / 100, f(i / 100)) for i in range(100)]}


class Verluste(unittest.TestCase):
    def test_steiles_kapitel_steht_oben(self):
        """Kurve faellt zwischen 300 s und 400 s steil; genau dieses
        Kapitel muss die Rangliste anfuehren."""
        def f(x):
            if x < 0.5:
                return 1.0 - 0.1 * x
            if x < 0.667:
                return 0.95 - 4.0 * (x - 0.5)
            return 0.28
        marken = [{"zeit_s": 0, "titel": "TL;DR"},
                  {"zeit_s": 60, "titel": "Ruhiges Kapitel"},
                  {"zeit_s": 300, "titel": "Der Absturz"},
                  {"zeit_s": 400, "titel": "Danach"}]
        v = R._kapitel_verluste([kennwert(marken, f=f)])
        self.assertEqual(v[0]["titel"], "Der Absturz")
        self.assertGreater(v[0]["je_min"], v[1]["je_min"])

    def test_vorspann_bleibt_draussen(self):
        """Das erste Kapitel faellt bei jedem Video am steilsten - das ist
        der bekannte Einstiegsverlust, keine Aussage ueber ein Thema."""
        marken = [{"zeit_s": 0, "titel": "TL;DR"},
                  {"zeit_s": 60, "titel": "Zweitens"},
                  {"zeit_s": 300, "titel": "Drittens"}]
        v = R._kapitel_verluste([kennwert(marken)])
        self.assertNotIn("TL;DR", [x["titel"] for x in v])

    def test_ohne_kapitel_keine_verluste(self):
        """Messungen vor dem 21.08.2026 tragen kein Kapitel-Feld."""
        self.assertEqual(R._kapitel_verluste([kennwert([])]), [])
        self.assertEqual(R._kapitel_verluste([{"laufzeit_s": 600}]), [])

    def test_kurze_kapitel_zaehlen_nicht(self):
        """Unter 30 s ist die Steigung Rauschen."""
        marken = [{"zeit_s": 0, "titel": "TL;DR"},
                  {"zeit_s": 60, "titel": "Kurz"},
                  {"zeit_s": 75, "titel": "Lang"}]
        v = R._kapitel_verluste([kennwert(marken)])
        self.assertNotIn("Kurz", [x["titel"] for x in v])


class BefundZeilen(unittest.TestCase):
    def test_zeilen_nennen_kapitel_und_verlust(self):
        v = [{"titel": "Der Absturz", "nummer": 2, "von": 4,
              "dauer_s": 100.0, "je_min": 0.24}]
        zeilen = R._kapitel_zeilen(v)
        text = "\n".join(zeilen)
        self.assertIn("Der Absturz", text)
        self.assertIn("chapter 3 of 4", text)
        self.assertIn("24 points of audience per minute", text)
        self.assertIn("warning about KIND", text)

    def test_unter_der_schwelle_keine_zeilen(self):
        v = [{"titel": "Harmlos", "nummer": 1, "von": 3, "dauer_s": 100.0,
              "je_min": 0.001}]
        self.assertEqual(R._kapitel_zeilen(v), [])

    def test_leere_messung_bleibt_stumm(self):
        self.assertEqual(R._kapitel_zeilen([]), [])

    def test_block_ohne_kapitel_unveraendert(self):
        """Der Gesamtbefund darf ohne Kapitelmessung nichts Neues
        enthalten - sonst waere jede aeltere Messung ein Prompt-Bruch."""
        k = R._retention_kennwerte(
            {"laufzeit_s": 600, "veroeffentlicht": "2026-08-18",
             "kurve": [{"elapsedVideoTimeRatio": i / 100,
                        "audienceWatchRatio": 1 - i / 100}
                       for i in range(100)]})
        block = R._retention_block([k])
        self.assertNotIn("CHAPTERS THAT LOST", block)


if __name__ == "__main__":
    unittest.main()
