#!/usr/bin/env python3
"""Tests fuer die Standzeit-Boeden und die Pausenstufen (Pacing 19.08.2026).

Die Pacing-Messung des Laufs vom 19.08.2026 (research/recherche-video-pacing-
2026-08-19.md) fand drei Klassen von Timing-Fehlern, gegen die hier die
Rechenregeln gesichert werden - der Rest der Szenenplanung braucht einen
echten Wortstrom und wird auf hp-ubuntu gemessen, nicht hier getestet:

- Lesezeit haengt an der Textlaenge, nicht an einer Konstante (A2),
- die Agenda bekommt ihre Lesezeit aus einer eigenen Pausenstufe (A3),
- der Trenner kodiert jetzt drei Pausenlaengen statt zwei.

Lauf:  python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import video_report as V  # noqa: E402


class TestLesezeitBoeden(unittest.TestCase):
    def test_kurzer_punkt_behaelt_den_absoluten_boden(self):
        # Unter FOKUS_MIN darf die Formel nie fallen, sonst stuende ein
        # Zweizeichen-Punkt kuerzer als eine Blende.
        self.assertEqual(V.fokus_boden(""), V.FOKUS_MIN)
        self.assertGreaterEqual(V.fokus_boden("BTC UP"), V.FOKUS_MIN)

    def test_langer_punkt_bekommt_mehr_zeit(self):
        # "NVIDIA BACKS OPENAI CREDIT" stand 1.5s (18 cps) - jetzt ueber 2s.
        self.assertGreater(V.fokus_boden("NVIDIA BACKS OPENAI CREDIT"), 2.0)

    def test_boden_waechst_mit_der_zeichenzahl(self):
        self.assertLess(V.fokus_boden("A" * 20), V.fokus_boden("A" * 40))

    def test_detail_boden_summiert_die_fragmente(self):
        # Der gemessene Ausreisser: 56 Zeichen standen 1.5s (38 cps).
        frag = ["$500B private-credit fund planned",
                "for datacenter capex"]
        self.assertGreater(V.detail_boden(frag), 4.0)

    def test_detail_boden_ohne_fragmente_ist_die_konstante(self):
        self.assertEqual(V.detail_boden([]), V.DETAIL_MIN)


class TestPausenstufen(unittest.TestCase):
    def test_drei_stufen_am_trenner(self):
        self.assertEqual(V._pause_fuer_trenner("\n\n"), V.GOOGLE_ABSATZ_PAUSE)
        self.assertEqual(V._pause_fuer_trenner("\n\n\n"), V.GOOGLE_AGENDA_PAUSE)
        self.assertEqual(V._pause_fuer_trenner("\n\n\n\n"),
                         V.GOOGLE_KAPITEL_PAUSE)

    def test_agenda_pause_liegt_zwischen_absatz_und_kapitel(self):
        absatz = V._pause_sekunden(V.GOOGLE_ABSATZ_PAUSE)
        agenda = V._pause_sekunden(V.GOOGLE_AGENDA_PAUSE)
        kapitel = V._pause_sekunden(V.GOOGLE_KAPITEL_PAUSE)
        self.assertLess(absatz, agenda)
        self.assertLess(agenda, kapitel)

    def test_ton_text_setzt_die_agenda_stufe(self):
        bloecke = [
            V.Block("absatz", "Hook line.", 0, rolle="intro"),
            V.Block("absatz", "Coming up:", 0, rolle="agenda_kopf"),
            V.Block("absatz", "First chapter.", 0, rolle="agenda"),
            V.Block("absatz", "Second chapter.", 0, rolle="agenda"),
            V.Block("ueberschrift", "CRYPTO", 1),
            V.Block("absatz", "Body text.", 1),
        ]
        text = V.ton_text(bloecke)
        self.assertIn("Coming up:\n\n\nFirst chapter.", text)
        self.assertIn("First chapter.\n\n\nSecond chapter.", text)
        # Die Kapitelgrenze bleibt die laengste Pause und ist von der
        # Agenda-Stufe unterscheidbar.
        self.assertIn("Second chapter.\n\n\n\nCRYPTO", text)
        self.assertIn("CRYPTO\n\nBody text.", text)

    def test_ssml_gruppen_tragen_die_agenda_pause(self):
        ssml = V._ssml_gruppen("Coming up:\n\n\nFirst chapter.")[0][0]
        self.assertIn(f'<break time="{V.GOOGLE_AGENDA_PAUSE}"/>', ssml)


if __name__ == "__main__":
    unittest.main()
