#!/usr/bin/env python3
"""Tests fuer Headline-Struktur und Video-Ende (Stossrichtungen B und C,
21.08.2026).

Die Ueberschriften des Berichts wurden von Themenlisten ("STOCKS: URANIUM,
HOOD, ADOBE") auf Behauptungen mit Einsatz umgestellt ("Silver hits 70 and
gets slapped back"). Das ist strukturell heikel: die Ueberschriften-Erkennung
verwarf bis dahin JEDE Zeile mit Kleinbuchstaben, und an ihr haengen die
##-Abschnitte, die Video-Kapitel, folien_zuordnen() und shorts.py. Hier ist
gesichert, dass beide Schreibweisen erkannt werden und der Marker nirgends
doppelt oder sichtbar durchschlaegt.

Dazu das umgebaute Videoende: der Sammelabschnitt der unveraenderten Themen
ist aus der Tonspur genommen, Schluss-Zitat und Cliffhanger-Frage sind neu.

Lauf:  python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bericht_html  # noqa: E402
import run_report as R  # noqa: E402
import video_report as V  # noqa: E402


class Ueberschriften(unittest.TestCase):
    def test_behauptung_in_kleinschreibung_wird_erkannt(self):
        """Der eigentliche Grund fuer den expliziten Marker: ohne ihn faellt
        eine Behauptung mit Kleinbuchstaben durch die Versalien-Heuristik."""
        self.assertTrue(bericht_html._ist_ueberschrift(
            "## Silver hits 70 and gets slapped back"))
        self.assertFalse(bericht_html._ist_ueberschrift(
            "Silver hits 70 and gets slapped back"))

    def test_versalien_pfad_bleibt(self):
        """Berichte frueherer Tage haben keinen Marker und muessen weiter
        laufen."""
        self.assertTrue(bericht_html._ist_ueberschrift("STOCKS: URANIUM, HOOD"))
        self.assertTrue(bericht_html._ist_ueberschrift("/SMG/ - LAGE"))
        self.assertFalse(bericht_html._ist_ueberschrift("Ein normaler Satz."))

    def test_marker_wird_nicht_verdoppelt(self):
        """bericht_zu_markdown() darf aus "## X" nie "## ## X" machen."""
        md = R.bericht_zu_markdown(
            "Data as of: 21.08.2026\n\n## Silver hits 70\n\nText.\n",
            "2026-08-21")
        self.assertIn("## Silver hits 70", md)
        self.assertNotIn("## ## ", md)

    def test_versalien_bekommen_den_marker_weiterhin(self):
        md = R.bericht_zu_markdown("SILVER HITS 70\n\nText.\n", "2026-08-21")
        self.assertIn("## SILVER HITS 70", md)

    def test_marker_erscheint_nicht_im_html(self):
        """Im HTML ist "## " Struktur, kein Text."""
        html = bericht_html.zu_html("## Silver hits 70\n\nText.\n")
        self.assertIn("Silver hits 70", html)
        self.assertNotIn("## ", html)


class StillTrue(unittest.TestCase):
    def test_beide_schreibweisen(self):
        self.assertTrue(R.ist_still_true("Still true from yesterday"))
        self.assertTrue(R.ist_still_true("## Still true from yesterday"))
        self.assertTrue(R.ist_still_true("UNCHANGED FROM YESTERDAY"))
        self.assertFalse(R.ist_still_true("Silver hits 70"))

    def test_abschnitt_wird_nicht_vertont(self):
        """Der Sammelabschnitt faellt aus der Tonspur, alles davor bleibt -
        und seine Thread-URLs beanspruchen keine Bilder mehr."""
        md = ("# Titel\n\n---\n\n## Silver hits 70\n\nSilber lief hoch.\n\n"
              "https://boards.4chan.org/biz/thread/111\n\n"
              "## Still true from yesterday\n\nAltes Thema.\n\n"
              "https://boards.4chan.org/biz/thread/222\n")
        bloecke, abschnitte = V.abschnitte_erzeugen(md)
        texte = " ".join(b.text for b in bloecke)
        self.assertIn("Silber lief hoch", texte)
        self.assertNotIn("Altes Thema", texte)
        self.assertNotIn("Still true", texte)
        threads = [t for a in abschnitte for t in a.threads]
        self.assertIn("111", threads)
        self.assertNotIn("222", threads)


class Kapitelnamen(unittest.TestCase):
    def test_reliability_tag_faellt_aus_dem_kapitelnamen(self):
        """Der Tag steht im Bericht und wird gesprochen, aber im
        YouTube-Kapitelnamen waere er nur Rauschen."""
        bloecke = [V.Block("ueberschrift", "Silver hits 70 [one loud ID]", 1),
                   V.Block("ueberschrift", "Gold splits the room", 2),
                   V.Block("ueberschrift", "Uranium rips", 3)]
        worte = [[V.Wort("x", 20.0, 21.0)], [V.Wort("x", 60.0, 61.0)],
                 [V.Wort("x", 120.0, 121.0)]]
        aus = V.kapitel_bauen(bloecke, worte, "TL;DR")
        self.assertIn("00:20 Silver hits 70", aus)
        self.assertNotIn("[one loud ID]", aus)
        self.assertTrue(aus.startswith("00:00 TL;DR"))


class Schluss(unittest.TestCase):
    def bauen(self, schluss: dict) -> list:
        fdaten = {"zahlen": [{"wert": "70", "titel": "Silver",
                              "satz": "Silver hit seventy."}],
                  "schluss": schluss}
        return V.praesentations_bloecke([], {}, fdaten, "2026-08-21", "GOLD")

    def test_zitat_und_frage_vor_dem_outro(self):
        bloecke = self.bauen({"zitat": "we are all going to make it",
                              "frage": "Does silver hold 70?"})
        rollen = [b.rolle for b in bloecke]
        self.assertEqual(rollen[-3:],
                         ["schluss_zitat", "schluss_frage", "outro"])
        zitat = bloecke[-3].text
        self.assertIn("we are all going to make it", zitat)
        self.assertEqual(bloecke[-2].text, "Does silver hold 70?")

    def test_ohne_schluss_bleibt_nur_das_outro(self):
        """Fehlt das Feld, faellt nur der Schluss-Beat weg - nie das Outro."""
        bloecke = self.bauen({})
        self.assertEqual(bloecke[-1].rolle, "outro")
        self.assertNotIn("schluss_zitat", [b.rolle for b in bloecke])

    def test_nur_frage_ohne_zitat(self):
        bloecke = self.bauen({"frage": "Does silver hold 70?"})
        self.assertEqual([b.rolle for b in bloecke][-2:],
                         ["schluss_frage", "outro"])

    def test_outro_bleibt_unter_fuenf_sekunden(self):
        """Der Abbinder ist auf einen Satz gekuerzt - der Cliffhanger davor
        soll die Aufmerksamkeit bekommen, nicht die Verabschiedung."""
        dauer = len(V.PRAES_OUTRO.split()) / V.TOKENS_PRO_S
        self.assertLess(dauer, 5.0)


if __name__ == "__main__":
    unittest.main()
