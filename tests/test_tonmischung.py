#!/usr/bin/env python3
"""Tests fuer die Intro-Anhebung des Musikbetts.

Der Vorspann ist die einzige Strecke, die praktisch jeder Zuschauer hoert
(YouTube-Analytics 19.08.2026: nach 17 s sind 24 % weg). Dort laeuft das Bett
lauter, ab der ersten Kapitelmarke wieder auf Normalpegel.

Gegen ffmpeg gemessen (19.08.2026, echtes bett.opus, Stille als Sprachspur,
damit der Sidechain nicht duckt): ohne Anhebung liegt das Intro 3.56 dB unter
dem Rumpf, mit Anhebung 3.44 dB darueber - eine Verschiebung von exakt
7.00 dB, also BETT_INTRO_ANHEBUNG.

Lauf:  python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import video_report as V  # noqa: E402


class TestIntroAnhebung(unittest.TestCase):
    def test_ohne_kapitelmarke_kein_eingriff(self):
        # Lieber gar keine Anhebung als eine auf geratenem Zeitpunkt.
        self.assertEqual(V._intro_anhebung(0.0), "")

    def test_zu_kurzer_vorspann_kein_eingriff(self):
        # Kuerzer als die Rampe waere die Anhebung nur ein Knacks.
        self.assertEqual(V._intro_anhebung(V.BETT_INTRO_RAMPE - 0.1), "")

    def test_verstaerkung_entspricht_der_konstanten(self):
        ausdruck = V._intro_anhebung(30.0)
        erwartet = 10 ** (V.BETT_INTRO_ANHEBUNG / 20)
        self.assertIn(f"{erwartet:.4f}", ausdruck)
        self.assertIn("eval=frame", ausdruck)

    def test_rampe_endet_auf_der_kapitelmarke(self):
        ausdruck = V._intro_anhebung(30.0)
        self.assertIn(f"lt(t,{30.0 - V.BETT_INTRO_RAMPE:.2f})", ausdruck)
        self.assertIn("lt(t,30.00)", ausdruck)


class TestKapitelEinsStart(unittest.TestCase):
    @staticmethod
    def _wort(start: float) -> V.Wort:
        return V.Wort("x", start, start + 0.3)

    def test_erste_ueberschrift_gibt_den_startzeitpunkt(self):
        bloecke = [V.Block("absatz", "hook", 0),
                   V.Block("ueberschrift", "CRYPTO", 1),
                   V.Block("absatz", "body", 1),
                   V.Block("ueberschrift", "HOUSING", 2)]
        worte = [[self._wort(0.0)], [self._wort(29.6)],
                 [self._wort(31.0)], [self._wort(120.0)]]
        self.assertAlmostEqual(V.kapitel_eins_start(bloecke, worte), 29.6)

    def test_ohne_ueberschrift_null(self):
        bloecke = [V.Block("absatz", "hook", 0)]
        self.assertEqual(V.kapitel_eins_start(bloecke, [[self._wort(0.0)]]), 0.0)

    def test_ueberschrift_ohne_worte_wird_uebersprungen(self):
        bloecke = [V.Block("ueberschrift", "LEER", 1),
                   V.Block("ueberschrift", "CRYPTO", 2)]
        self.assertAlmostEqual(
            V.kapitel_eins_start(bloecke, [[], [self._wort(25.0)]]), 25.0)


class TestTonKette(unittest.TestCase):
    def setUp(self):
        if not V.BETT.exists():
            self.skipTest("kein bett.opus auf diesem Rechner")

    def test_anhebung_sitzt_hinter_dem_ducking(self):
        # Das Ducking soll weiter formen, nur auf hoeherem Grundpegel.
        _, teile, _ = V._ton_kette(0, 60.0, 30.0)
        kette = ";".join(teile)
        self.assertLess(kette.index("sidechaincompress"),
                        kette.index("eval=frame"))

    def test_ohne_kapitelmarke_bleibt_die_kette_neutral(self):
        _, teile, _ = V._ton_kette(0, 60.0, 0.0)
        self.assertNotIn("eval=frame", ";".join(teile))


if __name__ == "__main__":
    unittest.main()
