#!/usr/bin/env python3
"""Tests fuer die Thread-Auswahl und die Rechenschaft der Synthese.

Anlass sind zwei Messungen vom 19.08.2026:

1. Der COVERAGE-Block sollte laut Prompt-Regel 13 jede Thread-Nummer der
   Eingabe genau einmal nennen. Geprueft wurde das nie - gezaehlt wurden nur
   die "omitted"-Zeilen. Ein still verschwundener Thread sah im Log aus wie
   ein vollstaendig abgedeckter Lauf.

2. sandwich() ordnete nach substanz_summe, einer Summe ueber alle Posts und
   damit praktisch einem Mass fuer Threadlaenge. Gemessen gingen alle vier
   Randplaetze an die vier laengsten Threads (298 bis 410 Posts), waehrend
   die pro Post dichtesten in der Mitte lagen - der Position, die laut
   arXiv 2307.03172 um 20-30 Punkte abfaellt.

Lauf:  python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_report as R  # noqa: E402


class TestAbdeckungPruefen(unittest.TestCase):
    def test_fehlende_nummer_wird_gemeldet(self):
        block = ("62604964: used - XRP schizo general\n"
                 "62605073: omitted - nothing beyond the subject line\n")
        fehlend, unbekannt = R.abdeckung_pruefen(
            block, ["62604964", "62605073", "62602437"])
        self.assertEqual(fehlend, ["62602437"])
        self.assertEqual(unbekannt, [])

    def test_vollstaendiger_block_meldet_nichts(self):
        block = ("62604964: used - XRP schizo general\n"
                 "62605073: partly - day trading, tax angle dropped\n")
        self.assertEqual(R.abdeckung_pruefen(block, ["62604964", "62605073"]),
                         ([], []))

    def test_erfundene_nummer_wird_gemeldet(self):
        block = "99999999: used - a thread that was never in the input\n"
        fehlend, unbekannt = R.abdeckung_pruefen(block, ["62604964"])
        self.assertEqual(fehlend, ["62604964"])
        self.assertEqual(unbekannt, ["99999999"])

    def test_aufzaehlungszeichen_und_leerzeilen_stoeren_nicht(self):
        block = "\n- 62604964: used - topic\n  * 62605073: used - topic\n\n"
        self.assertEqual(R.abdeckung_pruefen(block, ["62604964", "62605073"]),
                         ([], []))

    def test_prosa_wird_nicht_als_nummer_gelesen(self):
        block = "Note: all threads were considered.\n62604964: used - topic\n"
        fehlend, _ = R.abdeckung_pruefen(block, ["62604964"])
        self.assertEqual(fehlend, [])


class TestSandwich(unittest.TestCase):
    @staticmethod
    def _meta(paare: dict[str, tuple[float, int]]) -> dict:
        return {t: {"substanz_summe": s, "posts_gesamt": n}
                for t, (s, n) in paare.items()}

    def test_dichter_kurzer_thread_bekommt_einen_randplatz(self):
        # Der lange Thread gewinnt nach Summe, der kurze nach Dichte je Post.
        # Vor der Aenderung landete der kurze in der Mitte.
        meta = self._meta({
            "lang_a": (192.0, 300), "lang_b": (182.0, 410),
            "mittel": (85.0, 165), "mager": (15.0, 107),
            "dicht": (49.0, 57),
        })
        ordnung = R.sandwich([Path(f"{t}.txt") for t in meta], meta)
        raender = {ordnung[0].stem, ordnung[1].stem,
                   ordnung[-2].stem, ordnung[-1].stem}
        self.assertIn("dicht", raender)
        self.assertIn("lang_a", raender)

    def test_kein_extrakt_geht_verloren(self):
        meta = self._meta({f"t{i}": (float(i), 50 + i) for i in range(15)})
        ex = [Path(f"{t}.txt") for t in meta]
        ordnung = R.sandwich(ex, meta)
        self.assertEqual(len(ordnung), len(ex))
        self.assertEqual({p.stem for p in ordnung}, set(meta))

    def test_winzige_threads_kapern_die_dichte_rangliste_nicht(self):
        # Ein einzelner Post mit Link und drei Zahlen ergibt rechnerisch die
        # hoechste Dichte ueberhaupt - unter MIN_POSTS_DICHTE zaehlt sie nicht.
        meta = self._meta({
            "winzling": (8.0, 1), "lang": (192.0, 300),
            "dicht": (49.0, 57), "mager": (15.0, 107),
        })
        ordnung = R.sandwich([Path(f"{t}.txt") for t in meta], meta)
        raender = {ordnung[0].stem, ordnung[1].stem,
                   ordnung[-2].stem, ordnung[-1].stem}
        self.assertIn("dicht", raender)

    def test_fehlende_metadaten_werfen_nicht(self):
        ex = [Path("ohne_meta.txt"), Path("mit_meta.txt")]
        ordnung = R.sandwich(ex, {"mit_meta": {"substanz_summe": 10.0,
                                               "posts_gesamt": 50}})
        self.assertEqual(len(ordnung), 2)


if __name__ == "__main__":
    unittest.main()
